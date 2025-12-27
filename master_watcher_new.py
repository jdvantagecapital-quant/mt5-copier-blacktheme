"""
MASTER WATCHER - Multi-Process Architecture
Each instance handles ONE master account for ONE pair
Accepts --pair-id argument to identify which pair to monitor
Writes to pair-specific shared memory file including balance/equity
"""

import MetaTrader5 as mt5
import mmap
import struct
import time
import json
import os
import sys
from datetime import datetime, timedelta


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

# Shared memory format:
# Header: timestamp(8) + balance(8) + equity(8) + count(4) = 28 bytes
# Positions: MAX_POSITIONS * POSITION_SIZE
HEADER_SIZE = 28

def save_master_activity(pair_id, message, log_type="INFO"):
    """Save master activity to JSON file for dashboard"""
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
    """Save closed trade to JSON file for dashboard"""
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
        closed_trades = closed_trades[:50]  # Keep last 50
        
        with open(closed_file, 'w') as f:
            json.dump(closed_trades, f)
    except:
        pass

def load_config(pair_id):
    """Load configuration for specific pair"""
    if not os.path.exists(CONFIG_FILE):
        print(f"ERROR: {CONFIG_FILE} not found!")
        return None
    
    with open(CONFIG_FILE, 'r', encoding='utf-8-sig') as f:
        config = json.load(f)
    
    pairs = config.get('pairs', [])
    pair = next((p for p in pairs if p.get('id') == pair_id), None)
    
    if not pair:
        print(f"ERROR: Pair {pair_id} not found in config!")
        return None
    
    return pair

def main(pair_id):
    """Main function for master watcher"""
    if not pair_id:
        print("ERROR: --pair-id argument required!")
        return
    
    print("=" * 60)
    print(f"MASTER WATCHER - Pair: {pair_id}")
    print("=" * 60)
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
        print(f"ERROR: Invalid master account number: {master_account}")
        save_master_activity(pair_id, f"ERROR: Invalid account number", "ERROR")
        return
    
    print(f"Terminal: {master_terminal}")
    print(f"Account: {master_account}")
    print()
    save_master_activity(pair_id, f"Configured for account {master_account}", "INFO")
    
    if not os.path.exists(master_terminal):
        print(f"ERROR: Terminal not found: {master_terminal}")
        save_master_activity(pair_id, "ERROR: Terminal not found", "ERROR")
        return
    
    # Create pair-specific shared memory file with new format
    SHARED_FILE = os.path.join(DATA_DIR, "data", f"shared_positions_{pair_id}.bin")
    file_size = HEADER_SIZE + MAX_POSITIONS * POSITION_SIZE
    
    try:
        with open(SHARED_FILE, 'wb') as f:
            f.write(b'\x00' * file_size)
        print(f"Created: {SHARED_FILE} ({file_size} bytes)")
    except Exception as e:
        print(f"ERROR creating shared file: {e}")
        save_master_activity(pair_id, f"ERROR: Cannot create shared file", "ERROR")
        return
    
    print(f"\nConnecting to MT5...")
    master_password = pair.get('master_password', '').strip()
    master_server = pair.get('master_server', '').strip()
    
    # First try to initialize without login to check if already connected
    already_connected = False
    if mt5.initialize(path=master_terminal):
        acc = mt5.account_info()
        if acc and acc.login == master_account:
            print(f"Already logged in as {acc.login} @ {acc.server}")
            save_master_activity(pair_id, f"Already logged in as {acc.login}", "INFO")
            already_connected = True
    
    if not already_connected:
        mt5.shutdown()
        if not master_password or not master_server:
            print("ERROR: Password and server required for login")
            save_master_activity(pair_id, "ERROR: Missing credentials", "ERROR")
            return
        
        print(f"Logging in to account {master_account}...")
        if not mt5.initialize(path=master_terminal, login=master_account,
                             password=master_password, server=master_server):
            error = mt5.last_error()
            print(f"Login failed: {error}")
            save_master_activity(pair_id, f"Login failed: {error}", "ERROR")
            return
    
    acc = mt5.account_info()
    if not acc:
        print("Failed to get account info")
        save_master_activity(pair_id, "Failed to get account info", "ERROR")
        mt5.shutdown()
        return
    
    print(f"Connected: {acc.login} @ {acc.server}")
    print(f"Balance: ${acc.balance:.2f}")
    save_master_activity(pair_id, f"Connected: {acc.login} - Balance: ${acc.balance:.2f}", "INFO")
    print("\nMonitoring positions...")
    
    f = None
    mm = None
    
    try:
        f = open(SHARED_FILE, 'r+b')
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE)
    except Exception as e:
        print(f"ERROR opening mmap: {e}")
        save_master_activity(pair_id, f"ERROR opening mmap: {e}", "ERROR")
        mt5.shutdown()
        return
    
    last_count = 0
    last_log_time = 0
    tracked_positions = {}  # ticket -> position info
    
    try:
        while True:
            # Check if pair is still enabled
            pair = load_config(pair_id)
            if not pair or not pair.get('enabled', True):
                time.sleep(1)
                continue
            
            # Get account info for balance/equity
            acc = mt5.account_info()
            balance = acc.balance if acc else 0.0
            equity = acc.equity if acc else 0.0
            
            positions = mt5.positions_get()
            count = len(positions) if positions else 0
            current_tickets = set()
            
            # Track current positions
            if positions:
                for pos in positions:
                    current_tickets.add(pos.ticket)
                    if pos.ticket not in tracked_positions:
                        tracked_positions[pos.ticket] = {
                            'ticket': pos.ticket,
                            'symbol': pos.symbol,
                            'type': pos.type,
                            'volume': pos.volume,
                            'price_open': pos.price_open,
                            'profit': pos.profit
                        }
            
            # Detect closed positions
            closed_tickets = set(tracked_positions.keys()) - current_tickets
            for ticket in closed_tickets:
                pos_info = tracked_positions.pop(ticket)
                # Get closed profit from history
                from_date = datetime.now() - timedelta(minutes=5)
                deals = mt5.history_deals_get(from_date, datetime.now(), ticket=ticket)
                if deals:
                    for deal in deals:
                        if deal.entry == 1:  # Exit deal
                            pos_info['profit'] = deal.profit
                            pos_info['close_price'] = deal.price
                            pos_info['close_time'] = datetime.now().strftime("%H:%M:%S")
                save_closed_trade(pair_id, pos_info)
                type_str = "BUY" if pos_info['type'] == 0 else "SELL"
                save_master_activity(pair_id, f"Closed {type_str} {pos_info['volume']} {pos_info['symbol']} P/L: {pos_info['profit']:.2f}", "CLOSE")
            
            # Log position changes
            if count != last_count:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Positions: {count}")
                save_master_activity(pair_id, f"Position count: {count}", "INFO")
                last_count = count
            
            # Write to shared memory with new format
            mm.seek(0)
            timestamp = int(time.time() * 1000)
            # Header: timestamp(8) + balance(8) + equity(8) + count(4)
            mm.write(struct.pack('<Q', timestamp))
            mm.write(struct.pack('<d', balance))
            mm.write(struct.pack('<d', equity))
            mm.write(struct.pack('<I', count))
            
            if positions:
                for pos in positions[:MAX_POSITIONS]:
                    symbol_bytes = pos.symbol.encode('utf-8')[:15].ljust(15, b'\x00')
                    
                    pos_data = struct.pack('<Q', pos.ticket)  # ticket
                    pos_data += struct.pack('<B', pos.type)  # type (0=buy, 1=sell)
                    pos_data += struct.pack('<d', pos.volume)  # volume
                    pos_data += struct.pack('<d', pos.sl if pos.sl else 0.0)  # SL
                    pos_data += struct.pack('<d', pos.tp if pos.tp else 0.0)  # TP
                    pos_data += symbol_bytes  # symbol
                    pos_data += struct.pack('<d', pos.price_open)  # price_open
                    pos_data += struct.pack('<d', pos.profit)  # profit
                    
                    mm.write(pos_data)
            
            mm.flush()
            
            # Periodic status log
            current_time = time.time()
            if current_time - last_log_time > 300:  # Every 5 minutes
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Status: {count} positions, Balance: ${balance:.2f}, Equity: ${equity:.2f}")
                save_master_activity(pair_id, f"Status OK - {count} positions, Balance: ${balance:.2f}", "INFO")
                last_log_time = current_time
            
            time.sleep(0.1)  # 100ms update interval
            
    except KeyboardInterrupt:
        print("\n[*] Stopping (Ctrl+C)...")
        save_master_activity(pair_id, "Master watcher stopped by user", "INFO")
    except Exception as e:
        print(f"\n[*] ERROR: {e}")
        save_master_activity(pair_id, f"ERROR: {e}", "ERROR")
    finally:
        if mm:
            mm.close()
        if f:
            f.close()
        mt5.shutdown()
        print("[*] Master watcher stopped.")
        save_master_activity(pair_id, "Master watcher shutdown complete", "INFO")

if __name__ == "__main__":
    # Parse command line arguments
    pair_id = None
    if '--pair-id' in sys.argv:
        idx = sys.argv.index('--pair-id')
        if idx + 1 < len(sys.argv):
            pair_id = sys.argv[idx + 1]
    
    try:
        main(pair_id)
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
    finally:
        print("\n" + "=" * 60)
        input("Press Enter to close this window...")

