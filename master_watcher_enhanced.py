"""
MASTER WATCHER - Enhanced with Database Integration
Each instance handles ONE master account for ONE pair
Captures real MT5 data, logs everything, stores to database
"""

import MetaTrader5 as mt5
import mmap
import struct
import time
import json
import os
import sys
from datetime import datetime, timedelta

# Import enhanced database storage
try:
    from storage_db import db
    USE_DATABASE = True
except ImportError:
    USE_DATABASE = False
    print("[WARN] Database module not available, using legacy storage")

# Get correct directory for config files
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(APP_DIR)

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
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
MAX_POSITIONS = 50
POSITION_SIZE = 48
MASTER_ACTIVITY_LOG_TEMPLATE = "master_activity_{pair_id}.json"
MAX_ACTIVITY_LOGS = 100
HEADER_SIZE = 28

def log_to_database(pair_id, level, message, account_id=None):
    """Log message to database with level (DEBUG/INFO/WARN/ERROR)"""
    if USE_DATABASE:
        try:
            db.add_log(pair_id, 'MASTER_WATCHER', level, message, account_id)
        except:
            pass

def save_master_activity(pair_id, message, log_type="INFO"):
    """Save master activity to JSON file for dashboard and database"""
    # Database logging
    log_to_database(pair_id, log_type, message)
    
    # Legacy JSON logging
    try:
        log_file = os.path.join(DATA_DIR, 'logs', f'master_activity_{pair_id}.json')
        activities = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    activities = json.load(f)
            except:
                activities = []
        
        activity = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "message": message,
            "type": log_type
        }
        activities.insert(0, activity)
        activities = activities[:MAX_ACTIVITY_LOGS]
        
        with open(log_file, 'w') as f:
            json.dump(activities, f)
    except:
        pass

def save_closed_trade(pair_id, trade_data):
    """Save closed trade to JSON file and database"""
    # Save to database
    if USE_DATABASE:
        try:
            db.add_trade_history(
                ticket=trade_data.get('ticket', 0),
                pair_id=pair_id,
                account_id=trade_data.get('account_id', 0),
                account_type='MASTER',
                symbol=trade_data.get('symbol', ''),
                trade_type=trade_data.get('type', 0),
                volume=trade_data.get('volume', 0.0),
                price_open=trade_data.get('price_open', 0.0),
                price_close=trade_data.get('close_price', 0.0),
                profit=trade_data.get('profit', 0.0),
                open_time=trade_data.get('open_time', ''),
                close_time=trade_data.get('close_time', ''),
                sl=trade_data.get('sl', 0.0),
                tp=trade_data.get('tp', 0.0)
            )
        except Exception as e:
            log_to_database(pair_id, 'ERROR', f"Failed to save trade to database: {e}")
    
    # Legacy JSON file
    try:
        closed_file = os.path.join(DATA_DIR, "data", f"closed_trades_{pair_id}.json")
        closed_trades = []
        if os.path.exists(closed_file):
            try:
                with open(closed_file, 'r') as f:
                    closed_trades = json.load(f)
            except:
                closed_trades = []
        
        closed_trades.insert(0, trade_data)
        closed_trades = closed_trades[:50]
        
        with open(closed_file, 'w') as f:
            json.dump(closed_trades, f)
    except:
        pass

def load_config(pair_id):
    """Load configuration for specific pair"""
    if not os.path.exists(CONFIG_FILE):
        print(f"ERROR: {CONFIG_FILE} not found!")
        log_to_database(pair_id, 'ERROR', f"Config file not found: {CONFIG_FILE}")
        return None
    
    with open(CONFIG_FILE, 'r', encoding='utf-8-sig') as f:
        config = json.load(f)
    
    pairs = config.get('pairs', [])
    pair = next((p for p in pairs if p.get('id') == pair_id), None)
    
    if not pair:
        print(f"ERROR: Pair {pair_id} not found in config!")
        log_to_database(pair_id, 'ERROR', f"Pair {pair_id} not found in config")
        return None
    
    return pair

def main(pair_id):
    """Main function for master watcher with enhanced logging"""
    if not pair_id:
        print("ERROR: --pair-id argument required!")
        return
    
    print("=" * 60)
    print(f"MASTER WATCHER - Pair: {pair_id}")
    print("=" * 60)
    
    log_to_database(pair_id, 'INFO', f"Master watcher started for pair {pair_id}")
    save_master_activity(pair_id, f"Master watcher started for pair {pair_id}", "INFO")
    
    pair = load_config(pair_id)
    if not pair:
        return
    
    # Get terminal path and strip any quotes
    master_terminal = pair.get('master_terminal', '').strip('"').strip("'").strip()
    
    # Get account and convert to int
    master_account = pair.get('master_account', 0)
    try:
        master_account = int(master_account)
    except (ValueError, TypeError):
        msg = f"Invalid master account number: {master_account}"
        print(f"ERROR: {msg}")
        log_to_database(pair_id, 'ERROR', msg, master_account)
        save_master_activity(pair_id, f"ERROR: {msg}", "ERROR")
        return
    
    print(f"Terminal: {master_terminal}")
    print(f"Account: {master_account}")
    print()
    
    log_to_database(pair_id, 'INFO', f"Configured for account {master_account}, terminal: {master_terminal}", master_account)
    save_master_activity(pair_id, f"Configured for account {master_account}", "INFO")
    
    if not os.path.exists(master_terminal):
        msg = f"Terminal not found: {master_terminal}"
        print(f"ERROR: {msg}")
        log_to_database(pair_id, 'ERROR', msg, master_account)
        save_master_activity(pair_id, f"ERROR: {msg}", "ERROR")
        return
    
    # Create pair-specific shared memory file
    SHARED_FILE = os.path.join(DATA_DIR, "data", f"shared_positions_{pair_id}.bin")
    file_size = HEADER_SIZE + MAX_POSITIONS * POSITION_SIZE
    
    try:
        with open(SHARED_FILE, 'wb') as f:
            f.write(b'\x00' * file_size)
        print(f"Created: {SHARED_FILE} ({file_size} bytes)")
        log_to_database(pair_id, 'DEBUG', f"Created shared memory file: {SHARED_FILE} ({file_size} bytes)")
    except Exception as e:
        msg = f"Cannot create shared file: {e}"
        print(f"ERROR: {msg}")
        log_to_database(pair_id, 'ERROR', msg, master_account)
        save_master_activity(pair_id, f"ERROR: {msg}", "ERROR")
        return
    
    print(f"\nConnecting to MT5...")
    log_to_database(pair_id, 'DEBUG', "Attempting MT5 connection", master_account)
    
    master_password = pair.get('master_password', '').strip()
    master_server = pair.get('master_server', '').strip()
    
    # First try to initialize without login
    already_connected = False
    if mt5.initialize(path=master_terminal):
        acc = mt5.account_info()
        if acc and acc.login == master_account:
            print(f"Already logged in as {acc.login} @ {acc.server}")
            log_to_database(pair_id, 'INFO', f"Already logged in as {acc.login} @ {acc.server}", acc.login)
            save_master_activity(pair_id, f"Already logged in as {acc.login}", "INFO")
            already_connected = True
    
    if not already_connected:
        mt5.shutdown()
        if not master_password or not master_server:
            msg = "Password and server required for login"
            print(f"ERROR: {msg}")
            log_to_database(pair_id, 'ERROR', msg, master_account)
            save_master_activity(pair_id, f"ERROR: {msg}", "ERROR")
            return
        
        print(f"Logging in to account {master_account}...")
        log_to_database(pair_id, 'DEBUG', f"Attempting login to {master_account} @ {master_server}")
        
        if not mt5.initialize(path=master_terminal, login=master_account,
                             password=master_password, server=master_server):
            error = mt5.last_error()
            msg = f"Login failed: {error}"
            print(msg)
            log_to_database(pair_id, 'ERROR', msg, master_account)
            save_master_activity(pair_id, msg, "ERROR")
            return
    
    acc = mt5.account_info()
    if not acc:
        msg = "Failed to get account info"
        print(msg)
        log_to_database(pair_id, 'ERROR', msg, master_account)
        save_master_activity(pair_id, msg, "ERROR")
        mt5.shutdown()
        return
    
    print(f"Connected: {acc.login} @ {acc.server}")
    print(f"Balance: ${acc.balance:.2f}")
    
    log_to_database(pair_id, 'INFO', f"Connected successfully: {acc.login} @ {acc.server}, Balance: ${acc.balance:.2f}", acc.login)
    save_master_activity(pair_id, f"Connected: {acc.login} - Balance: ${acc.balance:.2f}", "INFO")
    
    # Update account status in database
    if USE_DATABASE:
        try:
            db.update_account_status(
                account_id=acc.login,
                pair_id=pair_id,
                account_type='MASTER',
                balance=acc.balance,
                equity=acc.equity,
                margin=acc.margin,
                free_margin=acc.margin_free,
                profit=acc.profit,
                server=acc.server
            )
            log_to_database(pair_id, 'DEBUG', "Account status updated in database", acc.login)
        except Exception as e:
            log_to_database(pair_id, 'WARN', f"Failed to update account status in database: {e}", acc.login)
    
    print("\nMonitoring positions...")
    log_to_database(pair_id, 'INFO', "Started monitoring positions")
    
    f = None
    mm = None
    
    try:
        f = open(SHARED_FILE, 'r+b')
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE)
        log_to_database(pair_id, 'DEBUG', "Shared memory mapped successfully")
    except Exception as e:
        msg = f"ERROR opening mmap: {e}"
        print(msg)
        log_to_database(pair_id, 'ERROR', msg, master_account)
        save_master_activity(pair_id, msg, "ERROR")
        mt5.shutdown()
        return
    
    last_count = 0
    last_log_time = 0
    last_db_update = 0
    tracked_positions = {}
    
    try:
        while True:
            # Check if pair is still enabled
            pair = load_config(pair_id)
            if not pair or not pair.get('enabled', True):
                time.sleep(1)
                continue
            
            # Get account info
            acc = mt5.account_info()
            balance = acc.balance if acc else 0.0
            equity = acc.equity if acc else 0.0
            
            # Update database every 10 seconds
            current_time = time.time()
            if USE_DATABASE and current_time - last_db_update > 10:
                try:
                    db.update_account_status(
                        account_id=acc.login if acc else master_account,
                        pair_id=pair_id,
                        account_type='MASTER',
                        balance=balance,
                        equity=equity,
                        margin=acc.margin if acc else 0,
                        free_margin=acc.margin_free if acc else 0,
                        profit=acc.profit if acc else 0,
                        server=acc.server if acc else ''
                    )
                    last_db_update = current_time
                except Exception as e:
                    log_to_database(pair_id, 'WARN', f"Database update failed: {e}")
            
            positions = mt5.positions_get()
            count = len(positions) if positions else 0
            current_tickets = set()
            
            # Track current positions
            if positions:
                for pos in positions:
                    current_tickets.add(pos.ticket)
                    
                    # New position opened
                    if pos.ticket not in tracked_positions:
                        tracked_positions[pos.ticket] = {
                            'ticket': pos.ticket,
                            'symbol': pos.symbol,
                            'type': pos.type,
                            'volume': pos.volume,
                            'price_open': pos.price_open,
                            'sl': pos.sl,
                            'tp': pos.tp,
                            'profit': pos.profit,
                            'open_time': datetime.fromtimestamp(pos.time).isoformat(),
                            'account_id': acc.login if acc else master_account
                        }
                        
                        type_str = "BUY" if pos.type == 0 else "SELL"
                        msg = f"NEW {type_str} position detected: {pos.symbol} {pos.volume} lots @ {pos.price_open:.5f}"
                        log_to_database(pair_id, 'INFO', msg, acc.login if acc else master_account)
                        
                        # Save to database
                        if USE_DATABASE:
                            try:
                                db.update_position(
                                    ticket=pos.ticket,
                                    pair_id=pair_id,
                                    account_id=acc.login if acc else master_account,
                                    account_type='MASTER',
                                    symbol=pos.symbol,
                                    pos_type=pos.type,
                                    volume=pos.volume,
                                    price_open=pos.price_open,
                                    sl=pos.sl,
                                    tp=pos.tp,
                                    profit=pos.profit,
                                    open_time=tracked_positions[pos.ticket]['open_time']
                                )
                            except Exception as e:
                                log_to_database(pair_id, 'WARN', f"Failed to save position to DB: {e}")
                    else:
                        # Update position profit
                        tracked_positions[pos.ticket]['profit'] = pos.profit
            
            # Detect closed positions
            closed_tickets = set(tracked_positions.keys()) - current_tickets
            for ticket in closed_tickets:
                pos_info = tracked_positions.pop(ticket)
                
                # Get closed trade info from history
                try:
                    from_date = datetime.now() - timedelta(minutes=5)
                    deals = mt5.history_deals_get(from_date, datetime.now())
                    
                    close_price = 0.0
                    close_profit = pos_info['profit']
                    
                    if deals:
                        for deal in deals:
                            if deal.position_id == ticket and deal.entry == 1:  # Exit deal
                                close_price = deal.price
                                close_profit = deal.profit
                                break
                    
                    pos_info['close_price'] = close_price
                    pos_info['profit'] = close_profit
                    pos_info['close_time'] = datetime.now().isoformat()
                    
                except Exception as e:
                    log_to_database(pair_id, 'WARN', f"Failed to get close price from history: {e}")
                    pos_info['close_price'] = 0.0
                    pos_info['close_time'] = datetime.now().isoformat()
                
                save_closed_trade(pair_id, pos_info)
                
                type_str = "BUY" if pos_info['type'] == 0 else "SELL"
                msg = f"CLOSED {type_str} {pos_info['symbol']} {pos_info['volume']} lots, P/L: ${pos_info['profit']:.2f}"
                log_to_database(pair_id, 'INFO', msg, pos_info.get('account_id'))
                save_master_activity(pair_id, msg, "CLOSE")
                
                # Remove from database
                if USE_DATABASE:
                    try:
                        db.remove_position(ticket)
                    except:
                        pass
            
            # Log position count changes
            if count != last_count:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Positions: {count}")
                log_to_database(pair_id, 'DEBUG', f"Position count changed: {count}")
                save_master_activity(pair_id, f"Position count: {count}", "INFO")
                last_count = count
            
            # Write to shared memory
            mm.seek(0)
            timestamp = int(time.time() * 1000)
            mm.write(struct.pack('<Q', timestamp))
            mm.write(struct.pack('<d', balance))
            mm.write(struct.pack('<d', equity))
            mm.write(struct.pack('<I', count))
            
            if positions:
                for pos in positions[:MAX_POSITIONS]:
                    symbol_bytes = pos.symbol.encode('utf-8')[:15].ljust(15, b'\x00')
                    pos_data = struct.pack('<Q', pos.ticket)
                    pos_data += struct.pack('<B', pos.type)
                    pos_data += struct.pack('<d', pos.volume)
                    pos_data += struct.pack('<d', pos.sl if pos.sl else 0.0)
                    pos_data += struct.pack('<d', pos.tp if pos.tp else 0.0)
                    pos_data += symbol_bytes
                    pos_data += struct.pack('<d', pos.price_open)
                    pos_data += struct.pack('<d', pos.profit)
                    mm.write(pos_data)
            
            mm.flush()
            
            # Periodic status log
            if current_time - last_log_time > 300:  # Every 5 minutes
                msg = f"Status: {count} positions, Balance: ${balance:.2f}, Equity: ${equity:.2f}"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
                log_to_database(pair_id, 'INFO', msg)
                save_master_activity(pair_id, f"Status OK - {msg}", "INFO")
                last_log_time = current_time
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n[*] Stopping (Ctrl+C)...")
        log_to_database(pair_id, 'INFO', "Master watcher stopped by user")
        save_master_activity(pair_id, "Master watcher stopped by user", "INFO")
    except Exception as e:
        print(f"\n[*] ERROR: {e}")
        log_to_database(pair_id, 'ERROR', f"Unexpected error: {e}")
        save_master_activity(pair_id, f"ERROR: {e}", "ERROR")
    finally:
        if mm:
            mm.close()
        if f:
            f.close()
        mt5.shutdown()
        print("[*] Master watcher stopped.")
        log_to_database(pair_id, 'INFO', "Master watcher shutdown complete")
        save_master_activity(pair_id, "Master watcher shutdown complete", "INFO")

if __name__ == "__main__":
    pair_id = None
    if '--pair-id' in sys.argv:
        idx = sys.argv.index('--pair-id')
        if idx + 1 < len(sys.argv):
            pair_id = sys.argv[idx + 1]
    
    try:
        main(pair_id)
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        if pair_id:
            log_to_database(pair_id, 'ERROR', f"FATAL: {e}")
    finally:
        print("\n" + "=" * 60)
        input("Press Enter to close this window...")
