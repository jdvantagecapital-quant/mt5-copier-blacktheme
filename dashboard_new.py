"""
MT5 Trade Copier Dashboard - Multi-Process Architecture
Supports multiple pairs with multiple children per pair

License-protected version - no user login required
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
import json
import os
import sys
import time
from datetime import datetime, timedelta
import secrets
import mmap
import struct
from auth_license import (
    generate_secret_key, login_required, developer_required,
    authenticate_user, verify_access_code, get_current_user, get_user_by_id,
    create_user, update_user, delete_user, reset_password, get_all_users,
    generate_user_access_code, can_access_pair, get_user_pairs, verify_password
)
from license import get_license_info, check_license_limits


# Get correct directory for config files (works in both dev and EXE)
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Data directory in AppData
def get_data_dir():
    if os.name == 'nt':
        base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~/.local/share')
    data_dir = os.path.join(base, 'JD_MT5_TradeCopier')
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'data'), exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'logs'), exist_ok=True)
    return data_dir

DATA_DIR = get_data_dir()
CONFIG_FILE = 'config.json'
STATUS_FILE = 'copier_status.json'
STATS_FILE = 'pair_stats.json'

def create_app(process_manager):
    """Create Flask application with process manager"""
    app = Flask(__name__, template_folder='Templates', static_folder='static')
    app.secret_key = generate_secret_key()
    
    # Store process manager reference
    app.config['PROCESS_MANAGER'] = process_manager
    
    def load_config():
        config_path = os.path.join(DATA_DIR, CONFIG_FILE)
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        return {'pairs': [], 'settings': {}}
    
    def save_config(config):
        config_path = os.path.join(DATA_DIR, CONFIG_FILE)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def load_stats():
        stats_path = os.path.join(DATA_DIR, STATS_FILE)
        if os.path.exists(stats_path):
            with open(stats_path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        return {}
    
    def save_stats(stats):
        stats_path = os.path.join(DATA_DIR, STATS_FILE)
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
    
    @app.context_processor
    def inject_user():
        user = get_current_user()
        license_info = get_license_info()
        return dict(current_user=user, license_info=license_info)
    
    # License Error Route
    @app.route('/license-error')
    def license_error():
        return render_template('license_error.html'), 403
    
    # Authentication Routes - Simplified for License System
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        # With license system, auto-login if license is valid
        license_info = get_license_info()
        if license_info:
            session['licensed'] = True
            session['client_name'] = license_info.get('client_name', 'Unknown')
            return redirect(url_for('index'))
        return redirect(url_for('license_error'))
    
    @app.route('/logout')
    def logout():
        session.clear()
        flash('Application closed.', 'info')
        return redirect(url_for('login'))
    
    @app.route('/change-password', methods=['GET', 'POST'])
    @login_required
    def change_password():
        # Password change not applicable with license system
        flash('Password management is not available with license authentication.', 'info')
        return redirect(url_for('index'))
    
    # Main Routes
    @app.route('/')
    @login_required
    def index():
        return render_template('index.html')
    
    @app.route('/accounts')
    @login_required
    def accounts():
        return render_template('accounts.html')
    
    @app.route('/logs')
    @login_required
    def logs():
        return render_template('logs.html')
    
    @app.route('/history')
    @login_required
    def history():
        return render_template('history.html')
    
    @app.route('/settings')
    @developer_required
    def settings():
        return render_template('settings.html')
    
    @app.route('/license')
    @login_required
    def license_page():
        """Show license information"""
        license_info = get_license_info()
        return render_template('license_info.html', license=license_info)
    
    # API Routes - Config
    @app.route('/api/config', methods=['GET', 'POST'])
    @login_required
    def handle_config():
        user = get_current_user()
        if request.method == 'GET':
            config = load_config()
            if user and user.get('role') == 'client':
                accessible_pairs = get_user_pairs(user, config.get('pairs', []))
                config['pairs'] = [p for _, p in accessible_pairs]
                config['is_client'] = True
            return jsonify(config)
        else:
            if user and user.get('role') != 'developer':
                return jsonify({'success': False, 'error': 'Access denied'})
            config = request.json
            for pair in config.get('pairs', []):
                if 'master_terminal' in pair:
                    pair['master_terminal'] = pair['master_terminal'].strip('"' + chr(39) + '  ')
                for child in pair.get('children', []):
                    if 'terminal' in child:
                        child['terminal'] = child['terminal'].strip('"' + chr(39) + '  ')
            save_config(config)
            return jsonify({'success': True})
    
    # API Routes - Pair Management
    @app.route('/api/pairs', methods=['GET'])
    @login_required
    def get_pairs():
        config = load_config()
        user = get_current_user()
        pairs = config.get('pairs', [])
        
        if user and user.get('role') == 'client':
            accessible_pairs = get_user_pairs(user, pairs)
            pairs = [p for _, p in accessible_pairs]
        
        # Add status information
        pm = app.config['PROCESS_MANAGER']
        status = pm.get_status()
        
        for pair in pairs:
            pair_id = pair.get('id')
            if pair_id in status:
                pair['status'] = {
                    'master_running': status[pair_id].get('master', False),
                    'children_running': status[pair_id].get('children', {})
                }
            else:
                pair['status'] = {
                    'master_running': False,
                    'children_running': {}
                }
        
        return jsonify(pairs)
    
    @app.route('/api/pairs', methods=['POST'])
    @developer_required
    def create_pair():
        data = request.json
        config = load_config()
        
        # Check license limits for pairs
        license_info = get_license_info()
        max_pairs = license_info.get('max_pairs', 5) if license_info else 5
        current_pairs = len(config.get('pairs', []))
        
        if current_pairs >= max_pairs:
            return jsonify({
                'success': False, 
                'error': f'License limit reached. Maximum {max_pairs} pairs allowed. You have {current_pairs}.'
            }), 403
        
        # Check license limits for children in this new pair
        max_children = license_info.get('max_children', 10) if license_info else 10
        children_data = data.get('children', [])
        if len(children_data) > max_children:
            return jsonify({
                'success': False,
                'error': f'License limit reached. Maximum {max_children} children per pair allowed.'
            }), 403
        
        # Generate unique pair ID
        pair_id = f"pair_{secrets.token_hex(4)}"
        # Convert account to integer
        try:
            master_account = int(data.get('master_account', 0))
        except (ValueError, TypeError):
            master_account = 0
        new_pair = {
            'id': pair_id,
            'name': data.get('name') or f'Pair {master_account}',
            'master_terminal': (data.get('master_terminal') or '').strip(),
            'master_account': master_account,
            'master_password': data.get('master_password', ''),
            'master_server': (data.get('master_server') or '').strip(),
            'enabled': data.get('enabled', True),
            'children': []
        }
        # Process children if provided
        for idx, child_data in enumerate(children_data):
            try:
                child_account = int(child_data.get('account', 0))
            except (ValueError, TypeError):
                child_account = 0
            child = {
                'id': f"child_{secrets.token_hex(4)}",
                'name': child_data.get('name') or f'Child {idx + 1}',
                'terminal': (child_data.get('terminal') or '').strip(),
                'account': child_account,
                'password': child_data.get('password', ''),
                'server': (child_data.get('server') or '').strip(),
                'copy_mode': child_data.get('copy_mode', 'full'),
                'lot_multiplier': float(child_data.get('lot_multiplier') or 1.0),
                'active_from': child_data.get('active_from') or None,
                'active_to': child_data.get('active_to') or None,
                'enabled': child_data.get('enabled', True)
            }
            new_pair['children'].append(child)
        config['pairs'].append(new_pair)
        save_config(config)
        return jsonify({'success': True, 'pair': new_pair})
    
    @app.route('/api/pairs/<pair_id>', methods=['PUT'])
    @developer_required
    def update_pair(pair_id):
        data = request.json
        config = load_config()
        pair = next((p for p in config['pairs'] if p.get('id') == pair_id), None)
        if not pair:
            return jsonify({'success': False, 'error': 'Pair not found'})
        
        # Check license limits for children when updating
        if 'children' in data:
            license_info = get_license_info()
            max_children = license_info.get('max_children', 10) if license_info else 10
            if len(data['children']) > max_children:
                return jsonify({
                    'success': False,
                    'error': f'License limit reached. Maximum {max_children} children per pair allowed.'
                }), 403
        
        # Update master fields with type conversion
        if 'master_account' in data:
            try:
                pair['master_account'] = int(data['master_account'])
            except (ValueError, TypeError):
                pair['master_account'] = 0
        for key in ['name', 'master_terminal', 'master_password', 'master_server']:
            if key in data:
                pair[key] = (data[key] or '').strip() if isinstance(data[key], str) else data[key]
        if 'enabled' in data:
            pair['enabled'] = data['enabled']
        # Update children if provided
        if 'children' in data:
            new_children = []
            for idx, child_data in enumerate(data['children']):
                try:
                    child_account = int(child_data.get('account', 0))
                except (ValueError, TypeError):
                    child_account = 0
                # Check if child has existing ID
                child_id = child_data.get('id') or f"child_{secrets.token_hex(4)}"
                child = {
                    'id': child_id,
                    'name': child_data.get('name') or f'Child {idx + 1}',
                    'terminal': (child_data.get('terminal') or '').strip(),
                    'account': child_account,
                    'password': child_data.get('password', ''),
                    'server': (child_data.get('server') or '').strip(),
                    'copy_mode': child_data.get('copy_mode', 'full'),
                    'lot_multiplier': float(child_data.get('lot_multiplier') or 1.0),
                    'active_from': child_data.get('active_from') or None,
                    'active_to': child_data.get('active_to') or None,
                    'enabled': child_data.get('enabled', True)
                }
                new_children.append(child)
            pair['children'] = new_children
        save_config(config)
        return jsonify({'success': True, 'pair': pair})
    
    @app.route('/api/pairs/<pair_id>', methods=['DELETE'])
    @developer_required
    def delete_pair(pair_id):
        pm = app.config['PROCESS_MANAGER']
        
        # Stop pair if running
        pm.stop_pair(pair_id)
        
        config = load_config()
        config['pairs'] = [p for p in config['pairs'] if p.get('id') != pair_id]
        save_config(config)
        
        return jsonify({'success': True})
    
    # API Routes - Child Management
    @app.route('/api/pairs/<pair_id>/children', methods=['POST'])
    @developer_required
    def add_child(pair_id):
        data = request.json
        config = load_config()
        
        pair = next((p for p in config['pairs'] if p.get('id') == pair_id), None)
        if not pair:
            return jsonify({'success': False, 'error': 'Pair not found'})
        
        # Check license limits for children
        license_info = get_license_info()
        max_children = license_info.get('max_children', 10) if license_info else 10
        current_children = len(pair.get('children', []))
        
        if current_children >= max_children:
            return jsonify({
                'success': False, 
                'error': f'License limit reached. Maximum {max_children} children per pair allowed. This pair has {current_children}.'
            }), 403
        
        # Generate unique child ID
        child_id = f"child_{secrets.token_hex(4)}"
        
        new_child = {
            'id': child_id,
            'name': data.get('name', 'New Child'),
            "terminal": data.get("terminal", "").strip("'\"  "),
            'account': data.get('account', 0),
            'password': data.get('password', ''),
            "server": data.get("server", "").strip("'\"  "),
            'lot_multiplier': data.get('lot_multiplier', 1.0),
            'copy_mode': data.get('copy_mode', 'normal'),
            'copy_close': data.get('copy_close', True),
            'enabled': data.get('enabled', True)
        }
        
        if 'children' not in pair:
            pair['children'] = []
        pair['children'].append(new_child)
        
        save_config(config)
        return jsonify({'success': True, 'child': new_child})
    
    @app.route('/api/pairs/<pair_id>/children/<child_id>', methods=['PUT'])
    @developer_required
    def update_child(pair_id, child_id):
        data = request.json
        config = load_config()
        
        pair = next((p for p in config['pairs'] if p.get('id') == pair_id), None)
        if not pair:
            return jsonify({'success': False, 'error': 'Pair not found'})
        
        child = next((c for c in pair.get('children', []) if c.get('id') == child_id), None)
        if not child:
            return jsonify({'success': False, 'error': 'Child not found'})
        
        # Update child fields
        for key in ['name', 'terminal', 'account', 'password', 'server', 'lot_multiplier', 'copy_mode', 'copy_close', 'enabled', 'period']:
            if key in data:
                value = data[key]
                if key in ['terminal', 'server'] and isinstance(value, str):
                    value = value.strip('"' + chr(39) + '  ')
                child[key] = value
        
        save_config(config)
        return jsonify({'success': True, 'child': child})
    
    @app.route('/api/pairs/<pair_id>/children/<child_id>', methods=['DELETE'])
    @developer_required
    def delete_child(pair_id, child_id):
        pm = app.config['PROCESS_MANAGER']
        
        # Stop child if running
        pm.stop_child(pair_id, child_id)
        
        config = load_config()
        pair = next((p for p in config['pairs'] if p.get('id') == pair_id), None)
        
        if pair:
            pair['children'] = [c for c in pair.get('children', []) if c.get('id') != child_id]
            save_config(config)
        
        return jsonify({'success': True})
    
    # API Routes - Process Control
    @app.route('/api/pairs/<pair_id>/start', methods=['POST'])
    @developer_required
    def start_pair(pair_id):
        pm = app.config['PROCESS_MANAGER']
        success, message = pm.start_pair(pair_id)
        return jsonify({'success': success, 'message': message})
    
    @app.route('/api/pairs/<pair_id>/stop', methods=['POST'])
    @developer_required
    def stop_pair(pair_id):
        pm = app.config['PROCESS_MANAGER']
        success, message = pm.stop_pair(pair_id)
        return jsonify({'success': success, 'message': message})
    
    @app.route('/api/pairs/<pair_id>/children/<child_id>/start', methods=['POST'])
    @developer_required
    def start_child(pair_id, child_id):
        pm = app.config['PROCESS_MANAGER']
        config = load_config()
        pair = next((p for p in config['pairs'] if p.get('id') == pair_id), None)
        if not pair:
            return jsonify({'success': False, 'error': 'Pair not found'})
        child = next((c for c in pair.get('children', []) if c.get('id') == child_id), None)
        if not child:
            return jsonify({'success': False, 'error': 'Child not found'})
        success, message = pm.start_child(pair_id, child_id, child)
        return jsonify({'success': success, 'message': message})
    
    @app.route('/api/pairs/<pair_id>/children/<child_id>/stop', methods=['POST'])
    @developer_required
    def stop_child(pair_id, child_id):
        pm = app.config['PROCESS_MANAGER']
        success, message = pm.stop_child(pair_id, child_id)
        return jsonify({'success': success, 'message': message})
    
    @app.route('/api/status')
    @login_required
    def get_status():
        pm = app.config['PROCESS_MANAGER']
        config = load_config()
        
        # Get first enabled pair
        pairs = [p for p in config.get('pairs', []) if p.get('enabled', True)]
        if not pairs:
            return jsonify({
                'running': False,
                'master': None,
                'children': [],
                'stats': {'total': 0, 'success': 0, 'failed': 0}
            })
        
        pair = pairs[0]
        pair_id = pair['id']
        children = pair.get('children', [])
        
        # Check if pair is running
        status = pm.get_status()
        pair_running = pair_id in status and status[pair_id].get('master', False)
        
        # Load stats
        stats = load_stats().get(pair_id, {'total': 0, 'success': 0, 'failed': 0})
        
        # Build response
        result = {
            'running': pair_running,
            'master': {
                'account': pair.get('master_account', 0),
                'balance': 0,
                'equity': 0,
                'connected': False,
                'positions': [],
                'closed_today': [],
                'live_pl': 0
            },
            'children': [],
            'stats': stats
        }
        
        # Add all children
        for child in children:
            result['children'].append({
                'id': child.get('id'),
                'name': child.get('name', 'Child'),
                'account': child.get('account', 0),
                'balance': 0,
                'equity': 0,
                'connected': False,
                'positions': [],
                'closed_today': [],
                'live_pl': 0,
                'running': pair_running and child.get('enabled', True)
            })
        
        return jsonify(result)

    

    @app.route('/api/process-status')
    @login_required
    def get_process_status():
        pm = app.config['PROCESS_MANAGER']
        raw_status = pm.get_status()
        # Convert to format expected by UI: {pair_id: {master_running: bool, children: {}}}
        status = {}
        for pair_id, pair_status in raw_status.items():
            status[pair_id] = {
                'master_running': pair_status.get('master', False),
                'children': pair_status.get('children', {})
            }
        return jsonify({'status': status})
    # API Routes - Activity Logs
    @app.route('/api/activity/<pair_id>')
    @login_required
    def get_activity(pair_id):
        master_activity = []
        child_activities = {}
        
        # Load master activity
        master_log = f'master_activity_{pair_id}.json'
        if os.path.exists(master_log):
            try:
                with open(master_log, 'r') as f:
                    master_activity = json.load(f)
            except:
                pass
        
        # Load children activities
        config = load_config()
        pair = next((p for p in config['pairs'] if p.get('id') == pair_id), None)
        if pair:
            for child in pair.get('children', []):
                child_id = child.get('id')
                child_log = f'activity_log_{pair_id}_{child_id}.json'
                if os.path.exists(child_log):
                    try:
                        with open(child_log, 'r') as f:
                            child_activities[child_id] = json.load(f)
                    except:
                        child_activities[child_id] = []
        
        return jsonify({
            'master': master_activity[:50],
            'children': child_activities
        })
    

    # Backward-compatible global routes for single-pair mode
    @app.route('/api/start', methods=['POST'])
    @developer_required
    def global_start():
        """Start the first enabled pair"""
        config = load_config()
        pairs = [p for p in config.get('pairs', []) if p.get('enabled', True)]
        if not pairs:
            return jsonify({'success': False, 'error': 'No enabled pairs found'})
        
        pair_id = pairs[0]['id']
        pm = app.config['PROCESS_MANAGER']
        success, message = pm.start_pair(pair_id)
        return jsonify({'success': success, 'message': message})
    
    @app.route('/api/stop', methods=['POST'])
    @developer_required
    def global_stop():
        """Stop the first enabled pair"""
        config = load_config()
        pairs = [p for p in config.get('pairs', []) if p.get('enabled', True)]
        if not pairs:
            return jsonify({'success': False, 'error': 'No enabled pairs found'})
        
        pair_id = pairs[0]['id']
        pm = app.config['PROCESS_MANAGER']
        success, message = pm.stop_pair(pair_id)
        return jsonify({'success': success, 'message': message})
    
    @app.route('/api/activity')
    @login_required
    def global_activity():
        """Get activity for the first enabled pair"""
        config = load_config()
        pairs = [p for p in config.get('pairs', []) if p.get('enabled', True)]
        if not pairs:
            return jsonify({'master': [], 'children': {}})
        
        pair_id = pairs[0]['id']
        return get_activity(pair_id)

    # Settings API
    @app.route('/api/settings', methods=['GET'])
    @login_required
    def api_get_settings():
        config = load_config()
        return jsonify({'success': True, 'settings': config.get('settings', {
            'copy_interval': 100,
            'retry_attempts': 3,
            'slippage': 5,
            'log_level': 'INFO'
        })})
    
    @app.route('/api/settings', methods=['POST'])
    @developer_required
    def api_save_settings():
        data = request.json
        config = load_config()
        config['settings'] = data
        save_config(config)
        return jsonify({'success': True})
    
    # Logs API
    @app.route('/api/logs', methods=['GET'])
    @login_required
    def api_get_logs():
        logs = []
        log_file = os.path.join(DATA_DIR, 'logs', 'trade_log.txt')
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()[-100:]
                    for line in reversed(lines):
                        line = line.strip()
                        if line:
                            log_type = 'info'
                            if 'ERROR' in line.upper():
                                log_type = 'error'
                            elif 'SUCCESS' in line.upper() or 'COPIED' in line.upper():
                                log_type = 'success'
                            logs.append({'type': log_type, 'message': line, 'time': ''})
            except:
                pass
        return jsonify({'logs': logs})
    
    @app.route('/api/logs/clear', methods=['POST'])
    @developer_required
    def api_clear_all_logs():
        """Clear all activity logs"""
        import glob
        log_patterns = [
            os.path.join(DATA_DIR, 'logs', 'master_activity_*.json'),
            os.path.join(DATA_DIR, 'logs', 'activity_log_*.json'),
            os.path.join(DATA_DIR, 'logs', 'child_activity_*.json'),
            os.path.join(DATA_DIR, 'logs', 'trade_log.txt')
        ]
        for pattern in log_patterns:
            for f in glob.glob(pattern):
                try:
                    os.remove(f)
                except:
                    pass
        return jsonify({'success': True})

    @app.route('/api/logs', methods=['DELETE'])
    @developer_required
    def api_clear_logs():
        log_file = os.path.join(DATA_DIR, 'logs', 'trade_log.txt')
        if os.path.exists(log_file):
            open(log_file, 'w').close()
        return jsonify({'success': True})


    @app.route('/api/all-logs', methods=['GET'])
    @login_required
    def api_get_all_logs():
        """Get all activity logs from all pairs"""
        all_logs = []
        config = load_config()
        
        for pair in config.get('pairs', []):
            pair_id = pair.get('id')
            pair_name = pair.get('name', pair_id)
            
            # Load master activity
            master_log = os.path.join(DATA_DIR, 'logs', f'master_activity_{pair_id}.json')
            if os.path.exists(master_log):
                try:
                    with open(master_log, 'r') as f:
                        master_activities = json.load(f)
                    for log in master_activities[:50]:
                        all_logs.append({
                            'time': f"{log.get('date', '')} {log.get('time', '')}".strip(),
                            'type': log.get('type', 'info'),
                            'message': f"[{pair_name}] [MASTER] {log.get('message', '')}",
                            'source': 'master',
                            'pair': pair_id
                        })
                except:
                    pass
            
            # Load children activities
            for child in pair.get('children', []):
                child_id = child.get('id')
                child_log = os.path.join(DATA_DIR, 'logs', f'activity_log_{pair_id}_{child_id}.json')
                if os.path.exists(child_log):
                    try:
                        with open(child_log, 'r') as f:
                            child_activities = json.load(f)
                        for log in child_activities[:50]:
                            all_logs.append({
                                'time': f"{log.get('date', '')} {log.get('time', '')}".strip(),
                                'type': log.get('type', 'info'),
                                'message': f"[{pair_name}] [CHILD {child_id}] {log.get('message', '')}",
                                'source': 'child',
                                'pair': pair_id
                            })
                    except:
                        pass
        
        # Sort by time descending
        all_logs.sort(key=lambda x: x.get('time', ''), reverse=True)
        return jsonify({'logs': all_logs[:200]})


    


    

    # User Management Routes
    @app.route('/api/users', methods=['GET'])
    @developer_required
    def api_get_users():
        users = get_all_users()
        return jsonify(users)
    
    @app.route('/api/users', methods=['POST'])
    @developer_required
    def api_create_user():
        data = request.json
        username = data.get('username', '').strip()
        role = data.get('role', 'client')
        assigned_pairs = data.get('assigned_pairs', [])
        if not username:
            return jsonify({'success': False, 'error': 'Username is required'})
        if role not in ['developer', 'client']:
            return jsonify({'success': False, 'error': 'Invalid role'})
        password, error = create_user(username, role, assigned_pairs)
        if error:
            return jsonify({'success': False, 'error': error})
        return jsonify({'success': True, 'password': password})
    
    @app.route('/api/users/<user_id>', methods=['PUT'])
    @developer_required
    def api_update_user(user_id):
        data = request.json
        success = update_user(user_id, data)
        return jsonify({'success': success})
    
    @app.route('/api/users/<user_id>', methods=['DELETE'])
    @developer_required
    def api_delete_user(user_id):
        success = delete_user(user_id)
        return jsonify({'success': success})
    
    @app.route('/api/users/<user_id>/generate-code', methods=['POST'])
    @developer_required
    def api_generate_code(user_id):
        code = generate_user_access_code(user_id)
        if code:
            return jsonify({'success': True, 'code': code})
        return jsonify({'success': False, 'error': 'Failed to generate code'})
    
    @app.route('/api/users/<user_id>/reset', methods=['POST'])
    @developer_required
    def api_reset_pwd(user_id):
        return api_reset_password(user_id)

    @app.route('/api/users/<user_id>/reset-password', methods=['POST'])
    @developer_required
    def api_reset_password(user_id):
        password = reset_password(user_id)
        if password:
            return jsonify({'success': True, 'password': password})
        return jsonify({'success': False, 'error': 'Failed to reset password'})
    # API Route - Get Live Trades for a pair
    @app.route('/api/pairs/<pair_id>/trades')
    @login_required
    def get_pair_trades(pair_id):
        """Read live trades, account info and activities from shared memory file"""
        result = {'master': [], 'children': {}, 'balance': 0, 'equity': 0, 'child_data': {}, 'activities': {'master': []}, 'closed_master': [], 'closed_children': {}}
        
        # Read master positions from shared memory
        shared_file = os.path.join(DATA_DIR, 'data', f'shared_positions_{pair_id}.bin')
        if os.path.exists(shared_file):
            try:
                with open(shared_file, 'rb') as f:
                    data = f.read()
                    # New format: timestamp(8) + balance(8) + equity(8) + count(4) = 28 bytes header
                    if len(data) >= 28:
                        timestamp = struct.unpack('<Q', data[:8])[0]
                        balance = struct.unpack('<d', data[8:16])[0]
                        equity = struct.unpack('<d', data[16:24])[0]
                        count = struct.unpack('<I', data[24:28])[0]
                        
                        result['balance'] = round(balance, 2)
                        result['equity'] = round(equity, 2)
                        
                        positions = []
                        offset = 28
                        # Position format: ticket(8) + type(1) + volume(8) + sl(8) + tp(8) + symbol(15) + price_open(8) + profit(8) = 64 bytes
                        POSITION_SIZE = 64
                        for i in range(min(count, 50)):
                            if offset + POSITION_SIZE <= len(data):
                                ticket = struct.unpack('<Q', data[offset:offset+8])[0]
                                trade_type = struct.unpack('<B', data[offset+8:offset+9])[0]
                                volume = struct.unpack('<d', data[offset+9:offset+17])[0]
                                sl = struct.unpack('<d', data[offset+17:offset+25])[0]
                                tp = struct.unpack('<d', data[offset+25:offset+33])[0]
                                symbol = data[offset+33:offset+48].decode('utf-8').rstrip('\x00')
                                price_open = struct.unpack('<d', data[offset+48:offset+56])[0]
                                profit = struct.unpack('<d', data[offset+56:offset+64])[0]
                                
                                if ticket > 0:
                                    positions.append({
                                        'ticket': ticket,
                                        'symbol': symbol,
                                        'type': trade_type,
                                        'volume': round(volume, 2),
                                        'price_open': round(price_open, 5),
                                        'profit': round(profit, 2)
                                    })
                                offset += POSITION_SIZE
                        result['master'] = positions
            except Exception as e:
                print(f"Error reading shared file: {e}")
        
        # Load closed trades from history files
        closed_master_file = os.path.join(DATA_DIR, 'data', f'closed_trades_{pair_id}.json')
        if os.path.exists(closed_master_file):
            try:
                with open(closed_master_file, 'r') as cmf:
                    result['closed_master'] = json.load(cmf)[:20]
            except:
                pass
        
        # Load master activity logs
        master_log_file = os.path.join(DATA_DIR, 'logs', f'master_activity_{pair_id}.json')
        if os.path.exists(master_log_file):
            try:
                with open(master_log_file, 'r') as mf:
                    result['activities']['master'] = json.load(mf)[:20]
            except:
                pass
        
        # Read child data from shared memory files
        config = load_config()
        pair = next((p for p in config.get('pairs', []) if p.get('id') == pair_id), None)
        if pair:
            for child in pair.get('children', []):
                child_id = child.get('id')
                result['activities'][child_id] = []
                
                # Read child shared memory file
                child_shared_file = os.path.join(DATA_DIR, 'data', f'child_data_{pair_id}_{child_id}.bin')
                if os.path.exists(child_shared_file):
                    try:
                        with open(child_shared_file, 'rb') as cf:
                            cdata = cf.read()
                            if len(cdata) >= 28:
                                c_balance = struct.unpack('<d', cdata[8:16])[0]
                                c_equity = struct.unpack('<d', cdata[16:24])[0]
                                c_count = struct.unpack('<I', cdata[24:28])[0]
                                
                                result['child_data'][child_id] = {
                                    'balance': round(c_balance, 2),
                                    'equity': round(c_equity, 2)
                                }
                                
                                # Read child positions
                                child_positions = []
                                c_offset = 28
                                POSITION_SIZE = 64
                                for i in range(min(c_count, 50)):
                                    if c_offset + POSITION_SIZE <= len(cdata):
                                        c_ticket = struct.unpack('<Q', cdata[c_offset:c_offset+8])[0]
                                        c_type = struct.unpack('<B', cdata[c_offset+8:c_offset+9])[0]
                                        c_volume = struct.unpack('<d', cdata[c_offset+9:c_offset+17])[0]
                                        c_sl = struct.unpack('<d', cdata[c_offset+17:c_offset+25])[0]
                                        c_tp = struct.unpack('<d', cdata[c_offset+25:c_offset+33])[0]
                                        c_symbol = cdata[c_offset+33:c_offset+48].decode('utf-8').rstrip('\x00')
                                        c_price = struct.unpack('<d', cdata[c_offset+48:c_offset+56])[0]
                                        c_profit = struct.unpack('<d', cdata[c_offset+56:c_offset+64])[0]
                                        
                                        if c_ticket > 0:
                                            child_positions.append({
                                                'ticket': c_ticket,
                                                'symbol': c_symbol,
                                                'type': c_type,
                                                'volume': round(c_volume, 2),
                                                'price_open': round(c_price, 5),
                                                'profit': round(c_profit, 2)
                                            })
                                        c_offset += POSITION_SIZE
                                result['children'][child_id] = child_positions
                    except Exception as ce:
                        print(f"Error reading child data: {ce}")
                        result['children'][child_id] = []
                        result['child_data'][child_id] = {'balance': 0, 'equity': 0}
                else:
                    result['children'][child_id] = []
                    result['child_data'][child_id] = {'balance': 0, 'equity': 0}
                
                # Load child activity logs
                child_log_file = os.path.join(DATA_DIR, 'logs', f'activity_log_{pair_id}_{child_id}.json')
                if os.path.exists(child_log_file):
                    try:
                        with open(child_log_file, 'r') as clf:
                            result['activities'][child_id] = json.load(clf)[:20]
                    except:
                        pass
                
                # Load child closed trades
                child_closed_file = os.path.join(DATA_DIR, 'data', f'closed_trades_{pair_id}_{child_id}.json')
                if os.path.exists(child_closed_file):
                    try:
                        with open(child_closed_file, 'r') as ccf:
                            result['closed_children'][child_id] = json.load(ccf)[:20]
                    except:
                        result['closed_children'][child_id] = []
                else:
                    result['closed_children'][child_id] = []
        
        return jsonify(result)

    
    return app

def main():
    """Standalone dashboard for testing"""
    from launcher_new import ProcessManager
    
    # License check is done in launcher, but check here for standalone testing
    from license import verify_license_startup
    success, result = verify_license_startup()
    if not success:
        print(f"License error: {result}")
        return
    
    pm = ProcessManager()
    app = create_app(pm)
    
    print("=" * 50)
    print("MT5 Trade Copier Dashboard")
    print(f"Licensed to: {result.get('client_name', 'Unknown')}")
    print("Open: http://127.0.0.1:5000")
    print("=" * 50)
    
    app.run(debug=False, port=5000, threaded=True)

if __name__ == '__main__':
    main()












