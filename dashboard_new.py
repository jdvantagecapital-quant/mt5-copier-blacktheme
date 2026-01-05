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
        
        # Clean up terminal paths (strip quotes, newlines, extra spaces)
        for pair in pairs:
            if 'master_terminal' in pair and pair['master_terminal']:
                pair['master_terminal'] = pair['master_terminal'].strip().strip('"\'')
            for child in pair.get('children', []):
                if 'terminal' in child and child['terminal']:
                    child['terminal'] = child['terminal'].strip().strip('"\'')
        
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
            'master_terminal': (data.get('master_terminal') or '').strip().strip('"\''),
            'master_account': master_account,
            'master_password': data.get('master_password', ''),
            'master_server': (data.get('master_server') or '').strip(),
            'enabled': data.get('enabled', True),
            **{f'master_symbol_{i}': data.get(f'master_symbol_{i}', '').upper() for i in range(1, 21)},
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
                'terminal': (child_data.get('terminal') or '').strip().strip('"\''),
                'account': child_account,
                'password': child_data.get('password', ''),
                'server': (child_data.get('server') or '').strip(),
                'copy_mode': child_data.get('copy_mode', 'full'),
                'lot_multiplier': float(child_data.get('lot_multiplier') or 1.0),
                'symbol_override': child_data.get('symbol_override', ''),
                'force_copy': child_data.get('force_copy', False),
                **{f'child_symbol_{i}': child_data.get(f'child_symbol_{i}', '').upper() for i in range(1, 21)},
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
        # Update master symbol fields - CLEAR old ones first, then set new ones
        for i in range(1, 21):
            key = f'master_symbol_{i}'
            # Always clear old value first
            if key in pair:
                del pair[key]
            # Then set new value if provided and not empty
            if key in data and data[key]:
                pair[key] = data[key].upper() if isinstance(data[key], str) else data[key]
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
                    'terminal': (child_data.get('terminal') or '').strip().strip('"').strip("'"),
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
            'terminal': (data.get('terminal') or '').strip().strip('"').strip("'"),
            'account': data.get('account', 0),
            'password': data.get('password', ''),
            'server': (data.get('server') or '').strip().strip('"').strip("'"),
            'lot_multiplier': data.get('lot_multiplier', 1.0),
            'copy_mode': data.get('copy_mode', 'normal'),
            'copy_close': data.get('copy_close', True),
            'copy_sl': data.get('copy_sl', True),
            'copy_tp': data.get('copy_tp', True),
            'copy_pending': data.get('copy_pending', True),
            'active_from': data.get('active_from', ''),
            'active_to': data.get('active_to', ''),
            'period': data.get('period', 'M1'),
            'symbol_override': data.get('symbol_override', False),
            'force_copy': data.get('force_copy', False),
            'enabled': data.get('enabled', True)
        }
        
        if 'children' not in pair:
            pair['children'] = []
        
        # Add symbol fields from data
        for i in range(1, 21):
            key = f'child_symbol_{i}'
            if key in data:
                new_child[key] = data[key].upper() if isinstance(data[key], str) else data[key]
        
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
        for key in ['name', 'terminal', 'account', 'password', 'server', 'lot_multiplier', 'copy_mode', 'copy_close', 'enabled', 'period', 'symbol_override', 'force_copy', 'copy_sl', 'copy_tp', 'copy_pending', 'active_from', 'active_to']:
            if key in data:
                value = data[key]
                if key in ['terminal', 'server'] and isinstance(value, str):
                    value = value.strip().strip('"').strip("'")
                child[key] = value
        
        # Update child symbol fields - CLEAR old ones first, then set new ones
        for i in range(1, 21):
            key = f'child_symbol_{i}'
            # Always clear old value first
            if key in child:
                del child[key]
            # Then set new value if provided and not empty
            if key in data and data[key]:
                child[key] = data[key].upper() if isinstance(data[key], str) else data[key]
        
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
        # Convert to format expected by UI: {pair_id: {running: bool, activated: bool}}
        status = {}
        for pair_id, pair_status in raw_status.items():
            status[pair_id] = {
                'running': pair_status.get('master', False),
                'activated': pair_status.get('activated', False),
                'children': pair_status.get('children', {})
            }
        return jsonify(status)
    
    @app.route('/api/pairs/<pair_id>/activate', methods=['POST'])
    @developer_required
    def activate_pair(pair_id):
        """Activate a pair - opens MT5 terminals and starts data fetching"""
        pm = app.config['PROCESS_MANAGER']
        success, message = pm.activate_pair(pair_id)
        return jsonify({'success': success, 'message': message})
    
    @app.route('/api/pairs/<pair_id>/deactivate', methods=['POST'])
    @developer_required
    def deactivate_pair(pair_id):
        """Deactivate a pair - closes MT5 terminals and stops data fetching"""
        pm = app.config['PROCESS_MANAGER']
        # First check if copier is running
        status = pm.get_status()
        if pair_id in status and status[pair_id].get('master', False):
            return jsonify({'success': False, 'error': 'Please stop the copier first'})
        success, message = pm.deactivate_pair(pair_id)
        return jsonify({'success': success, 'message': message})
    
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
            'master': master_activity[:100],  # Show last 100 entries
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
        """Get all activity logs from all pairs, masters and children with full identification"""
        all_logs = []
        config = load_config()
        limit = request.args.get('limit', 0, type=int)  # 0 = unlimited
        include_archives = request.args.get('archives', 'false').lower() == 'true'
        
        for pair in config.get('pairs', []):
            pair_id = pair.get('id')
            pair_name = pair.get('name', f'Pair {pair_id}')
            master_account = pair.get('master_account', 'Unknown')
            
            # Load master activity
            master_log = os.path.join(DATA_DIR, 'logs', f'master_activity_{pair_id}.json')
            if os.path.exists(master_log):
                try:
                    with open(master_log, 'r') as f:
                        master_activities = json.load(f)
                    for log in master_activities:
                        all_logs.append({
                            'timestamp': f"{log.get('date', '')} {log.get('time', '')}".strip(),
                            'type': log.get('type', 'info'),
                            'action': log.get('action', log.get('type', 'info')),
                            'message': log.get('message', ''),
                            'account': str(master_account),
                            'account_type': 'MASTER',
                            'pair_id': pair_id,
                            'pair_name': pair_name,
                            'symbol': log.get('symbol', ''),
                            'ticket': log.get('ticket', ''),
                            'volume': log.get('volume', ''),
                            'price': log.get('price', ''),
                            'sl': log.get('sl', ''),
                            'tp': log.get('tp', ''),
                            'source': 'master'
                        })
                except:
                    pass
            
            # Load master activity archives if requested
            if include_archives:
                archive_dir = os.path.join(DATA_DIR, 'logs', 'archive')
                for i in range(1, 6):  # Check up to 5 archives
                    archive_file = os.path.join(archive_dir, f'master_activity_{pair_id}.{i}.json')
                    if os.path.exists(archive_file):
                        try:
                            with open(archive_file, 'r') as f:
                                archived_activities = json.load(f)
                            for log in archived_activities:
                                all_logs.append({
                                    'timestamp': f"{log.get('date', '')} {log.get('time', '')}".strip(),
                                    'type': log.get('type', 'info'),
                                    'action': log.get('action', log.get('type', 'info')),
                                    'message': log.get('message', ''),
                                    'account': str(master_account),
                                    'account_type': 'MASTER',
                                    'pair_id': pair_id,
                                    'pair_name': pair_name,
                                    'symbol': log.get('symbol', ''),
                                    'ticket': log.get('ticket', ''),
                                    'volume': log.get('volume', ''),
                                    'price': log.get('price', ''),
                                    'sl': log.get('sl', ''),
                                    'tp': log.get('tp', ''),
                                    'source': 'master_archive'
                                })
                        except:
                            pass
            
            # Load children activities from .log files (text format)
            import re as regex
            for child in pair.get('children', []):
                child_id = child.get('id')
                child_account = child.get('account', 'Unknown')
                
                # Load all child log files including rotated ones
                log_files = []
                child_log = os.path.join(DATA_DIR, 'logs', f'child_{pair_id}_{child_id}.log')
                if os.path.exists(child_log):
                    log_files.append(child_log)
                
                # Include rotated logs if archives requested
                if include_archives:
                    for i in range(1, 6):  # Check up to 5 rotated files
                        rotated = f"{child_log}.{i}"
                        if os.path.exists(rotated):
                            log_files.append(rotated)
                
                for log_file in log_files:
                    try:
                        with open(log_file, 'r') as f:
                            lines = f.readlines()
                        # No limit when reading - read all lines
                        for line in reversed(lines):
                            line = line.strip()
                            if not line:
                                continue
                            # Parse format: [2025-12-26 17:18:25.265] [INFO] message
                            match = regex.match(r'\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})\.\d+\] \[(\w+)\] (.+)', line)
                            if match:
                                date_str, time_str, log_type, message = match.groups()
                                all_logs.append({
                                    'timestamp': f"{date_str} {time_str}",
                                    'type': log_type.lower(),
                                    'action': log_type.lower(),
                                    'message': message,
                                    'account': str(child_account),
                                    'account_type': 'CHILD',
                                    'pair_id': pair_id,
                                    'pair_name': pair_name,
                                    'symbol': '',
                                    'ticket': '',
                                    'volume': '',
                                    'price': '',
                                    'sl': '',
                                    'tp': '',
                                    'source': 'child',
                                    'child_id': child_id
                                })
                    except Exception as e:
                        print(f"Error reading child log: {e}")
        
        # Also load trade_log.txt for general system logs
        trade_log = os.path.join(DATA_DIR, 'logs', 'trade_log.txt')
        if os.path.exists(trade_log):
            try:
                with open(trade_log, 'r') as f:
                    lines = f.readlines()  # Read all lines
                for line in lines:
                    line = line.strip()
                    if line:
                        log_type = 'info'
                        if 'ERROR' in line.upper(): log_type = 'error'
                        elif 'WARNING' in line.upper(): log_type = 'warning'
                        elif 'SUCCESS' in line.upper() or 'COPIED' in line.upper(): log_type = 'trade'
                        all_logs.append({
                            'timestamp': '',
                            'type': log_type,
                            'action': log_type,
                            'message': line,
                            'account': 'System',
                            'account_type': 'SYSTEM',
                            'pair_id': '',
                            'pair_name': 'System',
                            'source': 'system'
                        })
            except:
                pass
        
        # Sort by timestamp descending
        all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Apply limit if specified (0 = unlimited)
        if limit > 0:
            return jsonify({'logs': all_logs[:limit], 'total': len(all_logs)})
        return jsonify({'logs': all_logs, 'total': len(all_logs)})


    


    

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
    
    @app.route('/api/pairs/<pair_id>/trades')
    @login_required
    def get_pair_trades(pair_id):
        """Get live trades from shared memory (binary struct format)"""
        import mmap
        import struct
        import os
        from datetime import datetime
        
        # Get date filter parameters
        date_from = request.args.get('date_from', None)
        date_to = request.args.get('date_to', None)
        
        # Helper function to check if trade is within date range
        def is_in_date_range(trade_time_str):
            if not date_from and not date_to:
                return True
            try:
                if ' ' in str(trade_time_str):
                    trade_date = str(trade_time_str).split(' ')[0]
                else:
                    trade_date = str(trade_time_str)[:10]
                if date_from and trade_date < date_from:
                    return False
                if date_to and trade_date > date_to:
                    return False
                return True
            except:
                return True
        
        result = {'master': [], 'children': {}, 'balance': 0, 'equity': 0, 'child_data': {}, 'activities': {'master': []}, 'closed_master': [], 'closed_children': {}}
        
        config = load_config()
        pair = next((p for p in config.get('pairs', []) if p.get('id') == pair_id), None)
        
        if not pair:
            return jsonify(result)
        
        data_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'JD_MT5_TradeCopier', 'data')
        
        # Read master positions from shared memory
        try:
            shared_file = os.path.join(data_dir, f'shared_positions_{pair_id}.bin')
            
            if os.path.exists(shared_file) and os.path.getsize(shared_file) >= 28:
                with open(shared_file, 'r+b') as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        mm.seek(0)
                        timestamp = struct.unpack('<Q', mm.read(8))[0]
                        balance = struct.unpack('<d', mm.read(8))[0]
                        equity = struct.unpack('<d', mm.read(8))[0]
                        count = struct.unpack('<I', mm.read(4))[0]
                        
                        result['balance'] = round(balance, 2)
                        result['equity'] = round(equity, 2)
                        
                        for i in range(min(count, 50)):
                            try:
                                ticket = struct.unpack('<Q', mm.read(8))[0]
                                pos_type = struct.unpack('<B', mm.read(1))[0]
                                volume = struct.unpack('<d', mm.read(8))[0]
                                sl = struct.unpack('<d', mm.read(8))[0]
                                tp = struct.unpack('<d', mm.read(8))[0]
                                symbol = mm.read(15).decode('utf-8', errors='ignore').rstrip('\x00')
                                price_open = struct.unpack('<d', mm.read(8))[0]
                                profit = struct.unpack('<d', mm.read(8))[0]
                                
                                result['master'].append({
                                    'ticket': ticket, 'symbol': symbol, 'type': pos_type,
                                    'volume': volume, 'sl': sl, 'tp': tp,
                                    'price_open': price_open, 'profit': round(profit, 2)
                                })
                            except:
                                break
        except Exception as e:
            print(f"[WARN] Error reading master shared memory: {e}")
        
        # Read closed master trades with date filtering
        try:
            closed_file = os.path.join(data_dir, f'closed_trades_{pair_id}.json')
            if os.path.exists(closed_file):
                with open(closed_file, 'r') as f:
                    all_closed = json.load(f)
                    complete_trades = []
                    for t in all_closed:
                        if t.get('close_price') and t.get('close_time'):
                            if is_in_date_range(t.get('close_time', '')):
                                t['close_price'] = round(t.get('close_price', 0), 5)
                                t['price_open'] = round(t.get('price_open', 0), 5)
                                t['profit'] = round(t.get('profit', 0), 2)
                                complete_trades.append(t)
                    result['closed_master'] = complete_trades
        except:
            pass
        
        # Read master activities - try text log first (more history), then JSON
        try:
            logs_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'JD_MT5_TradeCopier', 'logs')
            master_text_log = os.path.join(logs_dir, f'master_{pair_id}.log')
            master_json_file = os.path.join(logs_dir, f'master_activity_{pair_id}.json')
            
            # Prefer text log (has full history like child logs)
            if os.path.exists(master_text_log):
                with open(master_text_log, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()[-5000:]  # Last 5000 lines
                    for line in reversed(lines):
                        if any(tag in line for tag in ['[SIGNAL]', '[OPEN]', '[CLOSE]', '[ERROR]', '[WARN]', '[INFO]', '[DEBUG]']):
                            log_type = 'INFO'
                            if '[CLOSE]' in line: log_type = 'CLOSE'
                            elif '[SIGNAL]' in line: log_type = 'SIGNAL'
                            elif '[OPEN]' in line: log_type = 'TRADE'
                            elif '[ERROR]' in line: log_type = 'ERROR'
                            elif '[WARN]' in line: log_type = 'WARN'
                            elif '[DEBUG]' in line: log_type = 'DEBUG'
                            
                            result['activities']['master'].append({
                                'time': line[1:24] if len(line) > 24 else '',
                                'message': line.strip(),
                                'type': log_type
                            })
            # Fall back to JSON if text log doesn't exist
            elif os.path.exists(master_json_file):
                with open(master_json_file, 'r', encoding='utf-8') as f:
                    activities = json.load(f)
                    for act in activities:
                        result['activities']['master'].append({
                            'time': f"{act.get('date', '')} {act.get('time', '')}",
                            'message': act.get('message', ''),
                            'type': act.get('type', 'INFO')
                        })
        except Exception as e:
            print(f"[WARN] Error reading master activity: {e}")
        
        # Read child data
        for child in pair.get('children', []):
            child_id = child.get('id')
            result['children'][child_id] = []
            result['activities'][child_id] = []
            result['closed_children'][child_id] = []
            result['child_data'][child_id] = {'balance': 0, 'equity': 0}
            
            # Read child data from binary struct format
            try:
                child_file = os.path.join(data_dir, f'child_data_{pair_id}_{child_id}.bin')
                
                if os.path.exists(child_file) and os.path.getsize(child_file) >= 28:
                    with open(child_file, 'rb') as f:
                        data = f.read()
                        timestamp = struct.unpack('<Q', data[0:8])[0]
                        balance = struct.unpack('<d', data[8:16])[0]
                        equity = struct.unpack('<d', data[16:24])[0]
                        count = struct.unpack('<I', data[24:28])[0]
                        
                        result['child_data'][child_id] = {'balance': round(balance, 2), 'equity': round(equity, 2)}
                        
                        offset = 28
                        positions = []
                        for i in range(min(count, 50)):
                            if offset + 64 > len(data):
                                break
                            ticket = struct.unpack('<Q', data[offset:offset+8])[0]
                            pos_type = struct.unpack('<B', data[offset+8:offset+9])[0]
                            volume = struct.unpack('<d', data[offset+9:offset+17])[0]
                            sl = struct.unpack('<d', data[offset+17:offset+25])[0]
                            tp = struct.unpack('<d', data[offset+25:offset+33])[0]
                            symbol = data[offset+33:offset+48].decode('utf-8', errors='ignore').rstrip(chr(0))
                            price_open = struct.unpack('<d', data[offset+48:offset+56])[0]
                            profit = struct.unpack('<d', data[offset+56:offset+64])[0]
                            
                            positions.append({
                                'ticket': ticket, 'symbol': symbol, 'type': pos_type,
                                'volume': volume, 'sl': sl, 'tp': tp,
                                'price_open': price_open, 'profit': round(profit, 2)
                            })
                            offset += 64
                        result['children'][child_id] = positions
            except Exception as e:
                print(f"[WARN] Error reading child {child_id}: {e}")
            
            # Read child activities - try JSON first, then fall back to log file
            try:
                logs_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'JD_MT5_TradeCopier', 'logs')
                json_file = os.path.join(logs_dir, f'child_activity_{pair_id}_{child_id}.json')
                log_file = os.path.join(logs_dir, f'child_{pair_id}_{child_id}.log')
                
                # Try JSON first (faster and structured)
                if os.path.exists(json_file):
                    with open(json_file, 'r', encoding='utf-8') as f:
                        activities = json.load(f)
                        for act in activities:
                            result['activities'][child_id].append({
                                'time': f"{act.get('date', '')} {act.get('time', '')}",
                                'message': act.get('message', ''),
                                'type': act.get('type', 'INFO')
                            })
                # Fall back to text log file
                elif os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()[-5000:]
                        for line in reversed(lines):
                            if any(tag in line for tag in ['[SIGNAL]', '[OPEN]', '[CLOSE]', '[ERROR]', '[WARN]', '[INFO]', '[DEBUG]']):
                                log_type = 'INFO'
                                if '[CLOSE]' in line: log_type = 'CLOSE'
                                elif '[SIGNAL]' in line: log_type = 'SIGNAL'
                                elif '[OPEN]' in line: log_type = 'TRADE'
                                elif '[ERROR]' in line: log_type = 'ERROR'
                                elif '[WARN]' in line: log_type = 'WARN'
                                elif '[DEBUG]' in line: log_type = 'DEBUG'
                                
                                result['activities'][child_id].append({
                                    'time': line[1:20] if len(line) > 20 else '',
                                    'message': line.strip(),
                                    'type': log_type
                                })
            except Exception as e:
                print(f"[WARN] Error reading child {child_id} activities: {e}")
            
            # Read child closed trades with date filtering
            try:
                child_closed_file = os.path.join(data_dir, f'closed_trades_{pair_id}_{child_id}.json')
                if os.path.exists(child_closed_file):
                    with open(child_closed_file, 'r') as f:
                        child_closed = json.load(f)
                        filtered_closed = []
                        for t in child_closed:
                            if is_in_date_range(t.get('close_time', '')):
                                t['close_price'] = round(t.get('close_price', 0), 5)
                                t['price_open'] = round(t.get('price_open', 0), 5)
                                t['profit'] = round(t.get('profit', 0), 2)
                                filtered_closed.append(t)
                        result['closed_children'][child_id] = filtered_closed
            except:
                pass
        
        return jsonify(result)

    @app.route('/api/accounts/<account_type>/<account_id>/positions')
    @login_required
    def get_account_positions(account_type, account_id):
        """Get live positions directly from MT5 terminal"""
        from mt5_data_fetcher import get_mt5_positions
        
        config = load_config()
        account_info = None
        
        # Find account in config
        if account_type == 'master':
            for pair in config.get('pairs', []):
                if pair.get('id') == account_id:
                    account_info = {
                        'login': pair.get('master_login'),
                        'server': pair.get('master_server'),
                        'password': pair.get('master_password'),
                        'terminal': pair.get('master_terminal')
                    }
                    break
        elif account_type == 'child':
            pair_id, child_id = account_id.split('_')
            for pair in config.get('pairs', []):
                if pair.get('id') == pair_id:
                    for child in pair.get('children', []):
                        if child.get('id') == child_id:
                            account_info = {
                                'login': child.get('login'),
                                'server': child.get('server'),
                                'password': child.get('password'),
                                'terminal': child.get('terminal')
                            }
                            break
                    break
        
        if not account_info:
            return jsonify({'success': False, 'error': 'Account not found'})
        
        result = get_mt5_positions(
            login=account_info['login'],
            server=account_info['server'],
            password=account_info.get('password'),
            terminal_path=account_info.get('terminal')
        )
        
        return jsonify(result)
    
    @app.route('/api/accounts/<account_type>/<account_id>/history')
    @login_required
    def get_account_history(account_type, account_id):
        """Get trade history directly from MT5 terminal"""
        from mt5_data_fetcher import get_mt5_history, get_mt5_closed_orders
        
        days = int(request.args.get('days', 5))
        
        config = load_config()
        account_info = None
        
        # Find account in config
        if account_type == 'master':
            for pair in config.get('pairs', []):
                if pair.get('id') == account_id:
                    account_info = {
                        'login': pair.get('master_login'),
                        'server': pair.get('master_server'),
                        'password': pair.get('master_password'),
                        'terminal': pair.get('master_terminal')
                    }
                    break
        elif account_type == 'child':
            pair_id, child_id = account_id.split('_')
            for pair in config.get('pairs', []):
                if pair.get('id') == pair_id:
                    for child in pair.get('children', []):
                        if child.get('id') == child_id:
                            account_info = {
                                'login': child.get('login'),
                                'server': child.get('server'),
                                'password': child.get('password'),
                                'terminal': child.get('terminal')
                            }
                            break
                    break
        
        if not account_info:
            return jsonify({'success': False, 'error': 'Account not found'})
        
        # Get both deals and orders
        deals_result = get_mt5_history(
            login=account_info['login'],
            server=account_info['server'],
            password=account_info.get('password'),
            terminal_path=account_info.get('terminal'),
            days=days
        )
        
        orders_result = get_mt5_closed_orders(
            login=account_info['login'],
            server=account_info['server'],
            password=account_info.get('password'),
            terminal_path=account_info.get('terminal'),
            days=days
        )
        
        return jsonify({
            'success': True,
            'deals': deals_result.get('deals', []),
            'orders': orders_result.get('orders', []),
            'from_date': deals_result.get('from_date'),
            'to_date': deals_result.get('to_date')
        })
    
    @app.route('/api/pairs/<pair_id>/live-data')
    @login_required
    def get_pair_live_data(pair_id):
        """Get live data for all accounts in a pair"""
        from mt5_data_fetcher import get_mt5_positions
        
        config = load_config()
        pair = next((p for p in config.get('pairs', []) if p.get('id') == pair_id), None)
        
        if not pair:
            return jsonify({'success': False, 'error': 'Pair not found'})
        
        result = {
            'success': True,
            'master': {},
            'children': {}
        }
        
        # Get master data
        master_data = get_mt5_positions(
            login=pair.get('master_login'),
            server=pair.get('master_server'),
            password=pair.get('master_password'),
            terminal_path=pair.get('master_terminal')
        )
        result['master'] = master_data
        
        # Get child data
        for child in pair.get('children', []):
            child_id = child.get('id')
            child_data = get_mt5_positions(
                login=child.get('login'),
                server=child.get('server'),
                password=child.get('password'),
                terminal_path=child.get('terminal')
            )
            result['children'][child_id] = child_data
        
        return jsonify(result)
    
    @app.route('/api/shutdown', methods=['POST'])
    @login_required
    def shutdown_system():
        """Shutdown all running processes, close all MT5 terminals, and exit"""
        try:
            pm = app.config['PROCESS_MANAGER']
            config = load_config()
            
            # 1. Stop all pairs (copier processes)
            for pair in config.get('pairs', []):
                pair_id = pair.get('id')
                if pair_id:
                    try:
                        pm.stop_pair(pair_id)
                    except:
                        pass
            
            # Give processes time to stop
            time.sleep(1)
            
            # 2. Deactivate all pairs (close MT5 terminals)
            for pair in config.get('pairs', []):
                pair_id = pair.get('id')
                if pair_id:
                    try:
                        pm.deactivate_pair(pair_id)
                    except:
                        pass
            
            time.sleep(1)
            
            # 3. Force kill ALL remaining MT5 terminals
            if os.name == 'nt':
                try:
                    import psutil
                    for proc in psutil.process_iter(['pid', 'name']):
                        try:
                            proc_name = (proc.info.get('name') or '').lower()
                            if 'terminal64.exe' in proc_name or 'terminal.exe' in proc_name:
                                proc.terminate()
                                try:
                                    proc.wait(timeout=2)
                                except psutil.TimeoutExpired:
                                    proc.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            pass
                except ImportError:
                    # Fallback: use taskkill
                    import subprocess
                    subprocess.run(['taskkill', '/F', '/IM', 'terminal64.exe'], capture_output=True)
                    subprocess.run(['taskkill', '/F', '/IM', 'terminal.exe'], capture_output=True)
            
            # 4. Shutdown Flask server
            func = request.environ.get('werkzeug.server.shutdown')
            if func is not None:
                func()
            else:
                # For newer Flask, use os._exit
                import threading
                def delayed_exit():
                    time.sleep(0.5)
                    os._exit(0)
                threading.Thread(target=delayed_exit, daemon=True).start()
            
            return jsonify({'success': True, 'message': 'System shutdown initiated - all processes and terminals closed'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})


    

    @app.route('/api/pairs/<pair_id>/mt5-data')
    @login_required
    def get_pair_mt5_data(pair_id):
        """Get data directly from MT5 terminals for all accounts in a pair"""
        from mt5_data_fetcher import get_account_live_data
        
        # Check if pair is activated before fetching MT5 data
        pm = app.config['PROCESS_MANAGER']
        if not pm.activated_pairs.get(pair_id, False):
            return jsonify({
                'success': True,
                'master': {
                    'balance': 0,
                    'equity': 0,
                    'positions': [],
                    'closed_trades': [],
                    'error': 'Pair not activated - click Activate to connect MT5 terminals'
                },
                'children': {},
                'child_data': {},
                'activities': {'master': []},
                'closed_master': [],
                'closed_children': {},
                'balance': 0,
                'equity': 0
            })
        
        # Get date filter parameters
        date_from = request.args.get('date_from', None)
        date_to = request.args.get('date_to', None)
        days = int(request.args.get('days', 30))
        
        config = load_config()
        pair = next((p for p in config.get('pairs', []) if p.get('id') == pair_id), None)
        
        if not pair:
            return jsonify({'success': False, 'error': 'Pair not found'})
        
        result = {
            'success': True,
            'master': {
                'balance': 0,
                'equity': 0,
                'positions': [],
                'closed_trades': [],
                'error': None
            },
            'children': {},
            'child_data': {},
            'activities': {'master': []},
            'closed_master': [],
            'closed_children': {}
        }
        
        # Get master data directly from MT5
        try:
            master_result = get_account_live_data(
                login=pair.get('master_account'),
                server=pair.get('master_server', ''),
                password=pair.get('master_password', ''),
                terminal_path=pair.get('master_terminal', ''),
                date_from=date_from,
                date_to=date_to,
                days=days
            )
            
            if master_result.get('success'):
                result['master']['balance'] = master_result.get('balance', 0)
                result['master']['equity'] = master_result.get('equity', 0)
                result['master']['positions'] = master_result.get('positions', [])
                result['closed_master'] = master_result.get('closed_trades', [])
            else:
                result['master']['error'] = master_result.get('error', 'Unknown error')
        except Exception as e:
            result['master']['error'] = str(e)
        
        # Compatibility fields
        result['balance'] = result['master']['balance']
        result['equity'] = result['master']['equity']
        
        # Get master activities from log - prefer text log for full history
        try:
            logs_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'JD_MT5_TradeCopier', 'logs')
            master_text_log = os.path.join(logs_dir, f'master_{pair_id}.log')
            master_json_file = os.path.join(logs_dir, f'master_activity_{pair_id}.json')
            
            # Prefer text log (has full history like child logs)
            if os.path.exists(master_text_log):
                with open(master_text_log, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()[-5000:]  # Last 5000 lines
                    for line in reversed(lines):
                        if any(tag in line for tag in ['[SIGNAL]', '[OPEN]', '[CLOSE]', '[ERROR]', '[WARN]', '[INFO]', '[DEBUG]']):
                            log_type = 'INFO'
                            if '[CLOSE]' in line: log_type = 'CLOSE'
                            elif '[SIGNAL]' in line: log_type = 'SIGNAL'
                            elif '[OPEN]' in line: log_type = 'TRADE'
                            elif '[ERROR]' in line: log_type = 'ERROR'
                            elif '[WARN]' in line: log_type = 'WARN'
                            elif '[DEBUG]' in line: log_type = 'DEBUG'
                            
                            result['activities']['master'].append({
                                'time': line[1:24] if len(line) > 24 else '',
                                'message': line.strip(),
                                'type': log_type
                            })
            # Fall back to JSON if text log doesn't exist
            elif os.path.exists(master_json_file):
                with open(master_json_file, 'r', encoding='utf-8') as f:
                    activities = json.load(f)
                    for act in activities:
                        result['activities']['master'].append({
                            'time': f"{act.get('date', '')} {act.get('time', '')}",
                            'message': act.get('message', ''),
                            'type': act.get('type', 'INFO')
                        })
        except:
            pass
        
        # Get child data
        for child in pair.get('children', []):
            child_id = child.get('id')
            result['children'][child_id] = []
            result['activities'][child_id] = []
            result['closed_children'][child_id] = []
            result['child_data'][child_id] = {'balance': 0, 'equity': 0}
            
            try:
                child_result = get_account_live_data(
                    login=child.get('account'),
                    server=child.get('server', ''),
                    password=child.get('password', ''),
                    terminal_path=child.get('terminal', ''),
                    date_from=date_from,
                    date_to=date_to,
                    days=days
                )
                
                if child_result.get('success'):
                    result['child_data'][child_id] = {
                        'balance': child_result.get('balance', 0),
                        'equity': child_result.get('equity', 0)
                    }
                    result['children'][child_id] = child_result.get('positions', [])
                    result['closed_children'][child_id] = child_result.get('closed_trades', [])
            except Exception as e:
                result['child_data'][child_id]['error'] = str(e)
            
            # Read child activities from log file
            try:
                logs_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'JD_MT5_TradeCopier', 'logs')
                log_file = os.path.join(logs_dir, f'child_{pair_id}_{child_id}.log')
                
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()[-5000:]
                        for line in reversed(lines):
                            if any(tag in line for tag in ['[SIGNAL]', '[OPEN]', '[CLOSE]', '[ERROR]', '[WARN]', '[INFO]']):
                                log_type = 'INFO'
                                if '[CLOSE]' in line: log_type = 'CLOSE'
                                elif '[SIGNAL]' in line: log_type = 'SIGNAL'
                                elif '[OPEN]' in line: log_type = 'TRADE'
                                elif '[ERROR]' in line: log_type = 'ERROR'
                                elif '[WARN]' in line: log_type = 'WARN'
                                
                                result['activities'][child_id].append({
                                    'time': line[1:20] if len(line) > 20 else '',
                                    'message': line.strip(),
                                    'type': log_type
                                })
                            if False:  # No limit
                                break
            except:
                pass
        
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
















