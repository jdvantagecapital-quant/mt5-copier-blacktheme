"""
MT5 Trade Copier - Child Executor (Enhanced)
With symbol mapping, database integration, and comprehensive logging
"""

import os
import sys
import json
import time
import struct
import mmap
from datetime import datetime

# Determine the base directory
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

# Import database and MT5
try:
    from storage_db import db
    USE_DATABASE = True
except ImportError:
    USE_DATABASE = False
    print("[WARN] Database module not available")

try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERROR: MetaTrader5 module not found")
    sys.exit(1)

# Constants
POSITION_SIZE = 64
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
STATS_FILE = os.path.join(DATA_DIR, "pair_stats.json")

def load_stats():
    """Load stats from file"""
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_stats(stats):
    """Save stats to file"""
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
    except:
        pass

def update_trade_stats(pair_id, success=True):
    """Update trade statistics for a pair"""
    stats = load_stats()
    if pair_id not in stats:
        stats[pair_id] = {'total': 0, 'success': 0, 'failed': 0}
    stats[pair_id]['total'] += 1
    if success:
        stats[pair_id]['success'] += 1
    else:
        stats[pair_id]['failed'] += 1
    save_stats(stats)

class TradeLog:
    """Enhanced logger with database integration"""
    def __init__(self, pair_id, child_id, child_account=None):
        self.pair_id = pair_id
        self.child_id = child_id
        self.child_account = child_account
        self.log_dir = os.path.join(DATA_DIR, "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, f"child_{pair_id}_{child_id}.log")
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] [{level}] {message}"
        print(line)
        
        # Write to file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(line + "\n")
        except:
            pass
        
        # Write to database
        if USE_DATABASE:
            try:
                db.add_log(self.pair_id, 'CHILD_EXECUTOR', level, message, self.child_account)
            except:
                pass

def load_config(pair_id, child_id):
    """Load configuration for the specified pair, child, and global settings"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8-sig') as f:
            config = json.load(f)
        
        pairs = config.get('pairs', [])
        pair = next((p for p in pairs if p.get('id') == pair_id), None)
        
        if not pair:
            return None, None, {}
        
        children = pair.get('children', [])
        child = next((c for c in children if c.get('id') == child_id), None)
        
        # Get global settings
        settings = config.get('settings', {})
        
        return pair, child, settings
    except:
        return None, None, {}

def write_child_data(pair_id, child_id, balance, equity, positions):
    """Write child account data to binary file"""
    try:
        data_file = os.path.join(DATA_DIR, "data", f"child_data_{pair_id}_{child_id}.bin")
        with open(data_file, 'wb') as f:
            f.write(struct.pack('<d', balance))
            f.write(struct.pack('<d', equity))
            f.write(struct.pack('<I', len(positions)))
    except:
        pass

def translate_symbol(pair_id, child_account, master_symbol, log):
    """Translate master symbol to child symbol using database mapping"""
    if not USE_DATABASE:
        return master_symbol
    
    try:
        mapped_symbol = db.get_symbol_mapping(pair_id, child_account, master_symbol)
        if mapped_symbol != master_symbol:
            log.log(f"Symbol mapping: {master_symbol} -> {mapped_symbol}", "DEBUG")
        return mapped_symbol
    except Exception as e:
        log.log(f"Symbol mapping error: {e}, using original symbol", "WARN")
        return master_symbol

def open_trade(symbol, trade_type, volume, sl, tp, magic, comment, log, copy_mode='normal', pair_id=None, child_account=None):
    """Open a trade with retry logic and symbol mapping"""
    
    # Translate symbol if mapping exists
    if pair_id and child_account:
        original_symbol = symbol
        symbol = translate_symbol(pair_id, child_account, symbol, log)
        if symbol != original_symbol:
            log.log(f"Using mapped symbol: {original_symbol} -> {symbol}", "INFO")
    
    # Handle copy modes BEFORE the retry loop
    original_type = trade_type
    original_sl = sl
    original_tp = tp
    
    if copy_mode == 'reverse':
        trade_type = 1 if trade_type == 0 else 0
        # CRITICAL: Also swap SL and TP for reverse mode
        if sl > 0 and tp > 0:
            sl, tp = tp, sl  # Swap both
        elif sl > 0 and tp == 0:
            tp = sl
            sl = 0
        elif tp > 0 and sl == 0:
            sl = tp
            tp = 0
        log.log(f"REVERSE: Direction {original_type}->{trade_type}, SL {original_sl}->{sl}, TP {original_tp}->{tp}", "DEBUG")
    elif copy_mode == 'only_buy':
        if trade_type != 0:
            log.log(f"Skipping SELL signal - only_buy mode active", "INFO")
            return True
    elif copy_mode == 'only_sell':
        if trade_type != 1:
            log.log(f"Skipping BUY signal - only_sell mode active", "INFO")
            return True
    
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            log.log(f"Opening trade attempt {attempt+1}/{max_retries}: {symbol}", "DEBUG")
            
            info = mt5.symbol_info(symbol)
            if info is None:
                log.log(f"Symbol {symbol} not found in terminal", "ERROR")
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                    continue
                return False
            
            if not info.visible:
                log.log(f"Symbol {symbol} not visible, enabling...", "DEBUG")
                mt5.symbol_select(symbol, True)
                time.sleep(0.1)
            
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                log.log(f"Cannot get tick data for {symbol}", "ERROR")
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                    continue
                return False
            
            price = tick.ask if trade_type == 0 else tick.bid
            type_str = "BUY" if trade_type == 0 else "SELL"
            
            # Determine filling mode
            filling = mt5.ORDER_FILLING_IOC
            if info.filling_mode & 1:
                filling = mt5.ORDER_FILLING_FOK
            elif info.filling_mode & 2:
                filling = mt5.ORDER_FILLING_IOC
            else:
                filling = mt5.ORDER_FILLING_RETURN
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": trade_type,
                "price": price,
                "deviation": 50,
                "magic": magic,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }
            
            if sl > 0:
                request["sl"] = sl
            if tp > 0:
                request["tp"] = tp
            
            log.log(f"Sending order: {type_str} {volume} {symbol} @ {price:.5f}", "DEBUG")
            result = mt5.order_send(request)
            
            if result is None:
                log.log(f"FAILED {type_str} {volume} {symbol}: No response, attempt {attempt+1}/{max_retries}", "ERROR")
                if attempt < max_retries - 1:
                    time.sleep(0.3)
                    continue
                return False
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                sl_str = f" SL:{sl:.5f}" if sl > 0 else ""
                tp_str = f" TP:{tp:.5f}" if tp > 0 else ""
                mode_str = f" [{copy_mode.upper()}]" if copy_mode != 'normal' else ""
                log.log(f"OPENED {type_str} {volume} {symbol} @ {price:.5f}{sl_str}{tp_str}{mode_str}", "TRADE")
                
                # Save to database
                if USE_DATABASE and pair_id and child_account:
                    try:
                        db.update_position(
                            ticket=result.order,
                            pair_id=pair_id,
                            account_id=child_account,
                            account_type='CHILD',
                            symbol=symbol,
                            pos_type=trade_type,
                            volume=volume,
                            price_open=price,
                            sl=sl,
                            tp=tp,
                            profit=0.0,
                            open_time=datetime.now().isoformat()
                        )
                    except Exception as e:
                        log.log(f"Failed to save position to DB: {e}", "WARN")
                
                return True
            elif result.retcode in [mt5.TRADE_RETCODE_REQUOTE, mt5.TRADE_RETCODE_PRICE_OFF]:
                log.log(f"Requote for {symbol}, retrying... ({attempt+1}/{max_retries})", "WARN")
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                    continue
            else:
                log.log(f"FAILED {type_str} {volume} {symbol}: {result.comment} (code: {result.retcode})", "ERROR")
                return False
                
        except Exception as e:
            log.log(f"Error opening trade (attempt {attempt+1}): {e}", "ERROR")
            if attempt < max_retries - 1:
                time.sleep(0.3)
                continue
            return False
    
    return False

def close_trade(ticket, symbol, trade_type, volume, log, pair_id=None):
    """Close an existing position with retry logic"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                    continue
                return False
            
            if not info.visible:
                mt5.symbol_select(symbol, True)
                time.sleep(0.1)
            
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                    continue
                return False
            
            close_type = mt5.ORDER_TYPE_SELL if trade_type == 0 else mt5.ORDER_TYPE_BUY
            price = tick.bid if trade_type == 0 else tick.ask
            
            filling = mt5.ORDER_FILLING_IOC
            if info.filling_mode & 1:
                filling = mt5.ORDER_FILLING_FOK
            elif info.filling_mode & 2:
                filling = mt5.ORDER_FILLING_IOC
            else:
                filling = mt5.ORDER_FILLING_RETURN
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": 50,
                "magic": 999999,
                "comment": "close_copy",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                type_str = "BUY" if trade_type == 0 else "SELL"
                log.log(f"CLOSED {type_str} {volume} {symbol} @ {price:.5f}", "CLOSE")
                
                # Remove from database
                if USE_DATABASE:
                    try:
                        db.remove_position(ticket)
                    except:
                        pass
                
                return True
            elif result and result.retcode in [mt5.TRADE_RETCODE_REQUOTE, mt5.TRADE_RETCODE_PRICE_OFF]:
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                    continue
            else:
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                    continue
                return False
                
        except Exception as e:
            log.log(f"Error closing trade: {e}", "ERROR")
            if attempt < max_retries - 1:
                time.sleep(0.2)
                continue
            return False
    
    return False

def find_child_position(master_ticket, symbol, log):
    """Find the child position that corresponds to a master ticket"""
    try:
        positions = mt5.positions_get(symbol=symbol)
        if positions:
            for pos in positions:
                if pos.magic == master_ticket:
                    return pos.ticket
            for pos in positions:
                if pos.comment and f"copy_{master_ticket}" in pos.comment:
                    return pos.ticket
        return None
    except:
        return None

def main(pair_id, child_id):
    """Main function for child executor with enhanced features"""
    if not pair_id or not child_id:
        print("ERROR: --pair-id and --child-id arguments required!")
        return
    
    pair, child, global_settings = load_config(pair_id, child_id)
    if not pair or not child:
        print("ERROR: Configuration not found!")
        return
    
    child_account = int(child.get('account', 0))
    log = TradeLog(pair_id, child_id, child_account)
    
    log.log("=" * 50, "INFO")
    log.log(f"CHILD EXECUTOR STARTED - Pair: {pair_id}, Child: {child_id}", "INFO")
    log.log("=" * 50, "INFO")
    
    # Get terminal path and strip any quotes
    child_terminal = child.get('terminal', '').strip('"\'')
    child_password = child.get('password', '')
    child_server = child.get('server', '')
    
    log.log(f"Child Account: {child_account}", "INFO")
    log.log(f"Server: {child_server}", "INFO")
    log.log(f"Database integration: {'ENABLED' if USE_DATABASE else 'DISABLED'}", "INFO")
    
    # Initialize MT5
    log.log("Initializing MT5 connection...", "DEBUG")
    init_args = {}
    if child_terminal:
        init_args['path'] = child_terminal
    
    if not mt5.initialize(**init_args):
        error = mt5.last_error()
        log.log(f"MT5 init failed: {error}", "ERROR")
        return
    
    # Login
    log.log(f"Logging in to account {child_account}...", "DEBUG")
    if not mt5.login(child_account, password=child_password, server=child_server):
        error = mt5.last_error()
        log.log(f"Login failed: {error}", "ERROR")
        mt5.shutdown()
        return
    
    acc = mt5.account_info()
    if not acc:
        log.log("Cannot get account info!", "ERROR")
        mt5.shutdown()
        return
    
    log.log(f"Connected: {acc.login} @ {acc.server}", "INFO")
    log.log(f"Balance: ${acc.balance:.2f}", "INFO")
    
    # Update account status in database
    if USE_DATABASE:
        try:
            db.update_account_status(
                account_id=acc.login,
                pair_id=pair_id,
                account_type='CHILD',
                balance=acc.balance,
                equity=acc.equity,
                margin=acc.margin,
                free_margin=acc.margin_free,
                profit=acc.profit,
                server=acc.server
            )
            log.log("Account status saved to database", "DEBUG")
        except Exception as e:
            log.log(f"Failed to save account status: {e}", "WARN")
    
    # Load symbol mappings from database
    symbol_mappings = {}
    if USE_DATABASE:
        try:
            symbol_mappings = db.get_all_mappings(pair_id, child_account)
            if symbol_mappings:
                log.log(f"Loaded {len(symbol_mappings)} symbol mappings from database", "INFO")
                for master_sym, child_sym in symbol_mappings.items():
                    log.log(f"  Mapping: {master_sym} -> {child_sym}", "DEBUG")
        except Exception as e:
            log.log(f"Failed to load symbol mappings: {e}", "WARN")
    
    # Write initial child data
    try:
        child_positions = mt5.positions_get() or []
        write_child_data(pair_id, child_id, acc.balance, acc.equity, child_positions)
    except:
        pass
    
    log.log("Waiting for signals from master...", "INFO")
    
    # Shared memory file
    SHARED_FILE = os.path.join(DATA_DIR, "data", f"shared_positions_{pair_id}.bin")
    
    f = None
    mm = None
    
    try:
        f = open(SHARED_FILE, 'r+b')
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        log.log("Connected to shared memory", "DEBUG")
    except Exception as e:
        log.log(f"ERROR opening shared file: {e}", "ERROR")
        return
    
    tracked_master = {}
    pending_track = {}
    last_log = 0
    last_db_update = 0
    error_count = 0
    
    try:
        while True:
            try:
                # Reload config for live changes
                pair, child, global_settings = load_config(pair_id, child_id)
                if not pair or not child:
                    time.sleep(0.5)
                    continue
                
                # Check if pair and child are enabled
                if not pair.get('enabled', True) or not child.get('enabled', True):
                    time.sleep(0.5)
                    continue
                
                # Update settings from config
                lot_multiplier = child.get('lot_multiplier', 1.0)
                copy_mode = child.get('copy_mode', 'normal')
                copy_close = child.get('copy_close', True)
                
                # Get global copy settings (default to True for SL/TP, False for pending)
                copy_sl = global_settings.get('copy_sl', True)
                copy_tp = global_settings.get('copy_tp', True)
                copy_pending = global_settings.get('copy_pending', False)
                
                # Update database every 10 seconds
                current_time = time.time()
                if USE_DATABASE and current_time - last_db_update > 10:
                    try:
                        child_acc = mt5.account_info()
                        if child_acc:
                            db.update_account_status(
                                account_id=child_acc.login,
                                pair_id=pair_id,
                                account_type='CHILD',
                                balance=child_acc.balance,
                                equity=child_acc.equity,
                                margin=child_acc.margin,
                                free_margin=child_acc.margin_free,
                                profit=child_acc.profit,
                                server=child_acc.server
                            )
                        last_db_update = current_time
                    except Exception as e:
                        log.log(f"Database update failed: {e}", "WARN")
                
                # Read shared memory
                mm.seek(0)
                data = mm.read(28)
                if len(data) < 28:
                    time.sleep(0.01)
                    continue
                
                ts = struct.unpack("<Q", data[0:8])[0]
                count = struct.unpack("<I", data[24:28])[0]
                
                master_now = {}
                for i in range(count):
                    pos_data = mm.read(POSITION_SIZE)
                    if len(pos_data) < POSITION_SIZE:
                        break
                    
                    ticket = struct.unpack('Q', pos_data[0:8])[0]
                    ptype = struct.unpack('B', pos_data[8:9])[0]
                    volume = struct.unpack('d', pos_data[9:17])[0]
                    sl = struct.unpack('d', pos_data[17:25])[0]
                    tp = struct.unpack('d', pos_data[25:33])[0]
                    symbol = pos_data[33:48].decode('utf-8').rstrip('\x00')
                    
                    master_now[ticket] = {
                        'symbol': symbol,
                        'type': ptype,
                        'volume': volume,
                        'sl': sl,
                        'tp': tp
                    }
                
                # Process pending tracking
                for master_ticket in list(pending_track.keys()):
                    info = pending_track[master_ticket]
                    if info['attempts'] >= 10:
                        log.log(f"Could not map master {master_ticket}, giving up", "WARN")
                        tracked_master[master_ticket] = -1
                        del pending_track[master_ticket]
                        continue
                    
                    child_ticket = find_child_position(master_ticket, info['symbol'], log)
                    if child_ticket:
                        tracked_master[master_ticket] = child_ticket
                        log.log(f"Mapped master {master_ticket} -> child {child_ticket}", "INFO")
                        del pending_track[master_ticket]
                    else:
                        pending_track[master_ticket]['attempts'] += 1
                
                # Open new positions
                for master_ticket, pos in master_now.items():
                    if master_ticket not in tracked_master and master_ticket not in pending_track:
                        child_volume = round(pos['volume'] * lot_multiplier, 2)
                        if child_volume < 0.01:
                            child_volume = 0.01
                        
                        type_str = "BUY" if pos['type'] == 0 else "SELL"
                        log.log(f"NEW SIGNAL: {type_str} {pos['symbol']} {pos['volume']} lots from master", "SIGNAL")
                        
                        # Apply SL/TP based on global settings
                        sl_to_copy = pos['sl'] if copy_sl else 0
                        tp_to_copy = pos['tp'] if copy_tp else 0
                        
                        success = open_trade(
                            pos['symbol'], 
                            pos['type'], 
                            child_volume,
                            sl_to_copy,
                            tp_to_copy,
                            master_ticket,
                            f"copy_{master_ticket}",
                            log,
                            copy_mode,
                            pair_id,
                            child_account
                        )
                        
                        update_trade_stats(pair_id, success)
                        
                        if success:
                            pending_track[master_ticket] = {
                                'symbol': pos['symbol'],
                                'attempts': 0,
                                'time': time.time()
                            }
                            time.sleep(0.05)
                            child_ticket = find_child_position(master_ticket, pos['symbol'], log)
                            if child_ticket:
                                tracked_master[master_ticket] = child_ticket
                                log.log(f"Mapped master {master_ticket} -> child {child_ticket}", "INFO")
                                del pending_track[master_ticket]
                        else:
                            tracked_master[master_ticket] = -1
                
                # Close positions
                if copy_close:
                    closed_tickets = []
                    for master_ticket, child_ticket in tracked_master.items():
                        if master_ticket not in master_now:
                            if child_ticket > 0:
                                child_pos = mt5.positions_get(ticket=child_ticket)
                                if child_pos:
                                    cp = child_pos[0]
                                    log.log(f"CLOSE SIGNAL: Master closed {cp.symbol}", "SIGNAL")
                                    close_trade(cp.ticket, cp.symbol, cp.type, cp.volume, log, pair_id)
                            closed_tickets.append(master_ticket)
                    
                    for t in closed_tickets:
                        del tracked_master[t]
                        if t in pending_track:
                            del pending_track[t]
                
                # Periodic status and data write
                now = time.time()
                try:
                    child_acc = mt5.account_info()
                    child_positions = mt5.positions_get() or []
                    if child_acc:
                        write_child_data(pair_id, child_id, child_acc.balance, child_acc.equity, child_positions)
                except:
                    pass
                
                if now - last_log > 60:
                    child_pos_count = len(mt5.positions_get() or [])
                    log.log(f"Status: Tracking {len(tracked_master)} | Pending {len(pending_track)} | Child has {child_pos_count} positions", "INFO")
                    last_log = now
                
                error_count = 0
                time.sleep(0.01)
                
            except struct.error as e:
                error_count += 1
                if error_count < 5:
                    log.log(f"Data read error (retrying): {e}", "WARN")
                time.sleep(0.1)
            except Exception as e:
                error_count += 1
                log.log(f"Loop error: {e}", "ERROR")
                if error_count > 10:
                    log.log("Too many errors, restarting connection...", "ERROR")
                    try:
                        mt5.shutdown()
                        time.sleep(1)
                        mt5.initialize(path=child_terminal, login=child_account, 
                                      password=child_password, server=child_server)
                        error_count = 0
                    except:
                        pass
                time.sleep(0.5)
            
    except KeyboardInterrupt:
        log.log("Stopping (Ctrl+C)...", "INFO")
    finally:
        if mm:
            mm.close()
        if f:
            f.close()
        mt5.shutdown()
        log.log("Child executor stopped.", "INFO")

if __name__ == "__main__":
    pair_id = None
    child_id = None
    
    if '--pair-id' in sys.argv:
        idx = sys.argv.index('--pair-id')
        if idx + 1 < len(sys.argv):
            pair_id = sys.argv[idx + 1]
    
    if '--child-id' in sys.argv:
        idx = sys.argv.index('--child-id')
        if idx + 1 < len(sys.argv):
            child_id = sys.argv[idx + 1]
    
    try:
        main(pair_id, child_id)
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
    finally:
        print("\n" + "=" * 60)
        input("Press Enter to close this window...")
