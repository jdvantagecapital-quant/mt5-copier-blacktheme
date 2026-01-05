"""
MT5 Trade Copier Launcher - Multi-Process Architecture
Spawns separate processes for each master watcher and child executor
Does NOT import MetaTrader5 - pure process management

License-protected version for commercial distribution
"""

import os
import sys
import time
import threading
import webbrowser
import signal
import subprocess
import json
from datetime import datetime

# Ensure we can import from current directory
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    EXE_PATH = sys.executable
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_PATH = sys.executable

os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

from storage import storage, get_app_data_dir
from license import verify_license_startup, get_license_info, check_license_limits

CONFIG_FILE = "config.json"

def get_data_dir():
    """Get the data directory for storing config, logs, and data files"""
    local_appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    data_dir = os.path.join(local_appdata, 'JD_MT5_TradeCopier')
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'data'), exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'logs'), exist_ok=True)
    return data_dir

DATA_DIR = get_data_dir()

class ProcessManager:
    """Manages master and child processes for MT5 copier"""
    
    def __init__(self):
        self.processes = {}  # {pair_id: {'master': proc, 'children': {child_id: proc}}}
        self.activated_pairs = {}  # {pair_id: True/False} - tracks which pairs have MT5 terminals open
        self.flask_thread = None
        
    def load_config(self):
        """Load configuration from file"""
        config_path = os.path.join(DATA_DIR, CONFIG_FILE)
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        return {'pairs': [], 'settings': {}}
    
    def save_config(self, config):
        """Save configuration to file"""
        config_path = os.path.join(DATA_DIR, CONFIG_FILE)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def get_exe_command(self, script_name):
        """Get the command to run a script (handles frozen vs script mode)"""
        if getattr(sys, 'frozen', False):
            # Running as EXE - use same EXE with --mode flag
            return [EXE_PATH]
        else:
            # Running as script
            return [sys.executable, os.path.join(APP_DIR, script_name)]
    
    def start_master(self, pair_id, pair_config):
        """Start master watcher process for a pair"""
        try:
            if pair_id in self.processes and 'master' in self.processes[pair_id]:
                proc = self.processes[pair_id]['master']
                if proc and proc.poll() is None:
                    return True, "Master already running"
            
            cmd = self.get_exe_command('master_watcher_new.py')
            cmd.extend(['--master', '--pair-id', pair_id])
            
            proc = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
                cwd=APP_DIR
            )
            
            if pair_id not in self.processes:
                self.processes[pair_id] = {'master': None, 'children': {}}
            self.processes[pair_id]['master'] = proc
            
            print(f"[*] Started Master for pair {pair_id} (PID: {proc.pid})")
            return True, f"Master started (PID: {proc.pid})"
            
        except Exception as e:
            return False, f"Failed to start master: {str(e)}"
    
    def start_child(self, pair_id, child_id, child_config):
        """Start child executor process"""
        try:
            if pair_id in self.processes and child_id in self.processes[pair_id].get('children', {}):
                proc = self.processes[pair_id]['children'][child_id]
                if proc and proc.poll() is None:
                    return True, "Child already running"
            
            cmd = self.get_exe_command('child_executor_new.py')
            cmd.extend(['--child', '--pair-id', pair_id, '--child-id', child_id])
            
            proc = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
                cwd=APP_DIR
            )
            
            if pair_id not in self.processes:
                self.processes[pair_id] = {'master': None, 'children': {}}
            if 'children' not in self.processes[pair_id]:
                self.processes[pair_id]['children'] = {}
            self.processes[pair_id]['children'][child_id] = proc
            
            print(f"[*] Started Child {child_id} for pair {pair_id} (PID: {proc.pid})")
            return True, f"Child started (PID: {proc.pid})"
            
        except Exception as e:
            return False, f"Failed to start child: {str(e)}"
    
    def stop_master(self, pair_id):
        """Stop master watcher process"""
        try:
            if pair_id not in self.processes or not self.processes[pair_id].get('master'):
                return True, "Master not running"
            
            proc = self.processes[pair_id]['master']
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except:
                    proc.kill()
                print(f"[*] Stopped Master for pair {pair_id}")
            
            self.processes[pair_id]['master'] = None
            
            # Clean up shared memory file
            shared_file = os.path.join(DATA_DIR, 'data', f'shared_positions_{pair_id}.bin')
            if os.path.exists(shared_file):
                try:
                    os.remove(shared_file)
                except:
                    pass
            
            return True, "Master stopped"
        except Exception as e:
            return False, f"Failed to stop master: {str(e)}"
    
    def stop_child(self, pair_id, child_id):
        """Stop child executor process"""
        try:
            if pair_id not in self.processes or child_id not in self.processes[pair_id].get('children', {}):
                return True, "Child not running"
            
            proc = self.processes[pair_id]['children'][child_id]
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except:
                    proc.kill()
                print(f"[*] Stopped Child {child_id} for pair {pair_id}")
            
            del self.processes[pair_id]['children'][child_id]
            return True, "Child stopped"
        except Exception as e:
            return False, f"Failed to stop child: {str(e)}"
    
    def start_pair(self, pair_id):
        """Start all processes for a pair (master + all enabled children)"""
        # Check if pair is activated first
        if not self.activated_pairs.get(pair_id, False):
            return False, "Please activate the pair first"
        
        config = self.load_config()
        pair = next((p for p in config.get('pairs', []) if p.get('id') == pair_id), None)
        
        if not pair:
            return False, "Pair not found"
        
        if not pair.get('enabled', True):
            return False, "Pair is disabled"
        
        # Start master
        success, msg = self.start_master(pair_id, pair)
        if not success:
            return False, msg
        
        # Wait for master to initialize
        time.sleep(2)
        
        # Start all enabled children
        started_children = 0
        for child in pair.get('children', []):
            if child.get('enabled', True):
                child_id = child.get('id')
                success, msg = self.start_child(pair_id, child_id, child)
                if success:
                    started_children += 1
                    time.sleep(0.5)  # Stagger child starts
        
        return True, f"Started master and {started_children} children"
    
    def stop_pair(self, pair_id):
        """Stop all processes for a pair"""
        # Stop all children first
        if pair_id in self.processes:
            children_ids = list(self.processes[pair_id].get('children', {}).keys())
            for child_id in children_ids:
                self.stop_child(pair_id, child_id)
        
        # Stop master
        self.stop_master(pair_id)
        
        return True, "Pair stopped"
    
    def activate_pair(self, pair_id):
        """Activate a pair - opens MT5 terminals for all accounts"""
        try:
            config = self.load_config()
            pair = next((p for p in config.get('pairs', []) if p.get('id') == pair_id), None)
            
            if not pair:
                return False, "Pair not found"
            
            # Open master MT5 terminal - strip whitespace, newlines, and quotes
            master_terminal = pair.get('master_terminal', '').strip().strip('"').strip("'")
            if master_terminal and os.path.exists(master_terminal):
                try:
                    subprocess.Popen([master_terminal], creationflags=subprocess.DETACHED_PROCESS if os.name == 'nt' else 0)
                    print(f"[*] Opened MT5 terminal for master: {master_terminal}")
                except Exception as e:
                    print(f"[!] Failed to open master terminal: {e}")
            
            # Open child MT5 terminals
            for child in pair.get('children', []):
                child_terminal = child.get('terminal', '').strip().strip('"').strip("'")
                if child_terminal and os.path.exists(child_terminal):
                    try:
                        # Check if this terminal is already open (same as master)
                        if child_terminal != master_terminal:
                            subprocess.Popen([child_terminal], creationflags=subprocess.DETACHED_PROCESS if os.name == 'nt' else 0)
                            print(f"[*] Opened MT5 terminal for child {child.get('id')}: {child_terminal}")
                        time.sleep(0.5)  # Stagger terminal opens
                    except Exception as e:
                        print(f"[!] Failed to open child terminal: {e}")
            
            # Mark pair as activated
            self.activated_pairs[pair_id] = True
            
            # Wait for terminals to initialize
            time.sleep(2)
            
            return True, "Pair activated - MT5 terminals are now connected"
            
        except Exception as e:
            return False, f"Failed to activate pair: {str(e)}"
    
    def deactivate_pair(self, pair_id):
        """Deactivate a pair - closes MT5 terminals"""
        try:
            # Check if copier is running - must stop first
            if pair_id in self.processes:
                master_running = self.processes[pair_id].get('master') and self.processes[pair_id]['master'].poll() is None
                if master_running:
                    return False, "Please stop the copier first"
            
            config = self.load_config()
            pair = next((p for p in config.get('pairs', []) if p.get('id') == pair_id), None)
            
            if not pair:
                return False, "Pair not found"
            
            # Collect terminal paths AND directories to close
            terminals_to_close = set()
            terminal_dirs = set()
            
            # Strip whitespace, newlines, and quotes from terminal paths
            master_terminal = pair.get('master_terminal', '').strip().strip('"').strip("'")
            if master_terminal:
                norm_path = os.path.normpath(master_terminal).lower()
                terminals_to_close.add(norm_path)
                term_dir = os.path.dirname(norm_path).lower()
                if term_dir:
                    terminal_dirs.add(term_dir)
            
            for child in pair.get('children', []):
                child_terminal = child.get('terminal', '').strip().strip('"').strip("'")
                if child_terminal:
                    norm_path = os.path.normpath(child_terminal).lower()
                    terminals_to_close.add(norm_path)
                    term_dir = os.path.dirname(norm_path).lower()
                    if term_dir:
                        terminal_dirs.add(term_dir)
            
            print(f"[DEBUG] Looking for terminals: {terminals_to_close}")
            print(f"[DEBUG] Terminal directories: {terminal_dirs}")
            
            closed_count = 0
            # Kill each terminal process
            if os.name == 'nt':
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'cwd']):
                    try:
                        proc_name = (proc.info.get('name') or '').lower()
                        proc_exe = (proc.info.get('exe') or '').lower()
                        proc_cwd = (proc.info.get('cwd') or '').lower()
                        proc_cmdline = proc.info.get('cmdline') or []
                        
                        # Check if this is an MT5 terminal
                        if 'terminal64.exe' in proc_name or 'terminal.exe' in proc_name:
                            should_close = False
                            
                            # Method 1: Check exe path
                            if proc_exe:
                                norm_exe = os.path.normpath(proc_exe).lower()
                                exe_dir = os.path.dirname(norm_exe).lower()
                                if norm_exe in terminals_to_close or exe_dir in terminal_dirs:
                                    should_close = True
                                    print(f"[DEBUG] Match by exe path: {norm_exe}")
                            
                            # Method 2: Check cwd (current working directory)
                            if not should_close and proc_cwd:
                                norm_cwd = os.path.normpath(proc_cwd).lower()
                                if norm_cwd in terminal_dirs or any(d in norm_cwd for d in terminal_dirs):
                                    should_close = True
                                    print(f"[DEBUG] Match by cwd: {norm_cwd}")
                            
                            # Method 3: Check cmdline for terminal path
                            if not should_close and proc_cmdline:
                                cmdline_str = ' '.join(proc_cmdline).lower()
                                for term_dir in terminal_dirs:
                                    if term_dir in cmdline_str:
                                        should_close = True
                                        print(f"[DEBUG] Match by cmdline: {cmdline_str}")
                                        break
                            
                            if should_close:
                                print(f"[*] Closing MT5 terminal PID {proc.pid}: {proc_exe}")
                                try:
                                    proc.terminate()
                                    closed_count += 1
                                    try:
                                        proc.wait(timeout=3)
                                    except psutil.TimeoutExpired:
                                        proc.kill()
                                        print(f"[*] Force killed MT5 terminal PID {proc.pid}")
                                except Exception as e:
                                    print(f"[WARN] Failed to close terminal: {e}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                        pass
            
            # Mark pair as deactivated
            self.activated_pairs[pair_id] = False
            
            if closed_count > 0:
                return True, f"Pair deactivated - closed {closed_count} MT5 terminal(s)"
            else:
                return True, "Pair deactivated (no matching terminals found)"
            
        except ImportError:
            # psutil not available, just mark as deactivated
            self.activated_pairs[pair_id] = False
            return True, "Pair deactivated (psutil not available - terminals may still be open)"
        except Exception as e:
            return False, f"Failed to deactivate pair: {str(e)}"
    
    def stop_all(self):
        """Stop all processes"""
        pair_ids = list(self.processes.keys())
        for pair_id in pair_ids:
            self.stop_pair(pair_id)
    
    def get_status(self):
        """Get status of all processes"""
        status = {}
        
        # Include all activated pairs
        for pair_id in self.activated_pairs:
            if pair_id not in status:
                status[pair_id] = {
                    'master': False,
                    'activated': self.activated_pairs.get(pair_id, False),
                    'children': {}
                }
        
        # Update with process status
        for pair_id, procs in self.processes.items():
            master_running = procs.get('master') and procs['master'].poll() is None
            children_status = {}
            for child_id, proc in procs.get('children', {}).items():
                children_status[child_id] = proc and proc.poll() is None
            
            if pair_id not in status:
                status[pair_id] = {
                    'master': master_running,
                    'activated': self.activated_pairs.get(pair_id, False),
                    'children': children_status
                }
            else:
                status[pair_id]['master'] = master_running
                status[pair_id]['children'] = children_status
        
        return status
    
    def is_pair_running(self, pair_id):
        """Check if a pair is running (master + at least one child)"""
        if pair_id not in self.processes:
            return False
        
        master_running = self.processes[pair_id].get('master') and self.processes[pair_id]['master'].poll() is None
        if not master_running:
            return False
        
        # Check if any child is running
        for proc in self.processes[pair_id].get('children', {}).values():
            if proc and proc.poll() is None:
                return True
        
        return False

class TradeCopierLauncher:
    """Main launcher for MT5 Trade Copier"""
    
    def __init__(self):
        self.process_manager = ProcessManager()
        self.license_data = None
        
    def print_banner(self):
        print("=" * 60)
        print("   JD MT5 Trade Copier v2.0")
        print("   Multi-Process Professional Architecture")
        print("=" * 60)
        if self.license_data:
            print(f"   Licensed to: {self.license_data.get('client_name', 'Unknown')}")
            print(f"   Expires: {self.license_data.get('expiry_date', 'Unknown')}")
        print(f"   Data Directory: {get_app_data_dir()}")
        print("=" * 60)
        print()
    
    def run_flask(self):
        """Run Flask dashboard"""
        from dashboard_new import create_app
        app = create_app(self.process_manager)
        
        # Disable Flask's default logging
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        app.run(host='127.0.0.1', port=5000, debug=False, threaded=True, use_reloader=False)
    
    def open_browser(self):
        """Open browser after short delay"""
        time.sleep(1.5)
        webbrowser.open('http://127.0.0.1:5000')
    
    def start(self):
        """Start the application"""
        # Verify license first
        print("[*] Verifying license...")
        success, result = verify_license_startup()
        
        if not success:
            print(f"[!] License verification failed: {result}")
            print("[!] Application cannot start without a valid license.")
            input("\nPress Enter to exit...")
            sys.exit(1)
        
        self.license_data = result
        self.print_banner()
        
        print("[*] Initializing secure storage...")
        # Note: We no longer initialize developer accounts - license handles access
        
        print("[*] Starting web dashboard...")
        print("[*] Opening browser at http://127.0.0.1:5000")
        print()
        print("    Press Ctrl+C to shutdown")
        print("=" * 60)
        
        # Open browser in background
        browser_thread = threading.Thread(target=self.open_browser, daemon=True)
        browser_thread.start()
        
        # Run Flask (blocking)
        try:
            self.run_flask()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown"""
        print("\n[*] Shutting down...")
        self.process_manager.stop_all()
        print("[*] Goodbye!")

# Global launcher instance
launcher = None

def get_process_manager():
    """Get the global process manager"""
    global launcher
    if launcher is None:
        launcher = TradeCopierLauncher()
    return launcher.process_manager

def main():
    global launcher
    launcher = TradeCopierLauncher()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        launcher.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Check command line arguments for subprocess modes
    if len(sys.argv) > 1:
        if '--master' in sys.argv:
            # Run as master watcher subprocess
            import master_watcher_new
            pair_id = sys.argv[sys.argv.index('--pair-id') + 1] if '--pair-id' in sys.argv else None
            try:
                master_watcher_new.main(pair_id)
            except Exception as e:
                print(f"\n[FATAL ERROR] {e}")
            finally:
                print("\n" + "=" * 60)
                input("Press Enter to close this window...")
            return
        elif '--child' in sys.argv:
            # Run as child executor subprocess
            import child_executor_new
            pair_id = sys.argv[sys.argv.index('--pair-id') + 1] if '--pair-id' in sys.argv else None
            child_id = sys.argv[sys.argv.index('--child-id') + 1] if '--child-id' in sys.argv else None
            try:
                child_executor_new.main(pair_id, child_id)
            except Exception as e:
                print(f"\n[FATAL ERROR] {e}")
            finally:
                print("\n" + "=" * 60)
                input("Press Enter to close this window...")
            return
    
    # Default: run main dashboard
    launcher.start()

if __name__ == '__main__':
    main()