#!/usr/bin/env python3
"""
MT5 Trade Copier - Child Executor (New Version)
Copies trades from master to child account using shared memory
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

# Try to import MetaTrader5
try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERROR: MetaTrader5 module not found. Please install it with: pip install MetaTrader5")
    sys.exit(1)

# Constants
POSITION_SIZE = 48  # bytes per position: ticket(8)+type(1)+volume(8)+sl(8)+tp(8)+symbol(15)
MAX_ORDERS = 20       # Max pending orders
ORDER_SIZE = 64       # Pending order size
HEADER_SIZE = 32      # timestamp(8) + balance(8) + equity(8) + pos_count(4) + order_count(4)
MAX_POSITIONS = 50    # Max positions from master
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")


def to_bool(value, default=True):
    """Convert config value to boolean, handling string 'true'/'false' from JSON"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 'on')
    return bool(value)

# Log rotation settings
MAX_LOG_SIZE_MB = 50  # Rotate when log exceeds 50MB
MAX_ROTATED_FILES = 5  # Keep 5 archived logs

def rotate_log_if_needed(log_file):
    """Rotate log file if it exceeds MAX_LOG_SIZE_MB"""
    try:
        if not os.path.exists(log_file):
            return
        
        size_mb = os.path.getsize(log_file) / (1024 * 1024)
        if size_mb < MAX_LOG_SIZE_MB:
            return
        
        # Rotate existing archives
        for i in range(MAX_ROTATED_FILES - 1, 0, -1):
            old_file = f"{log_file}.{i}"
            new_file = f"{log_file}.{i+1}"
            if os.path.exists(old_file):
                if i + 1 > MAX_ROTATED_FILES:
                    os.remove(old_file)
                else:
                    os.rename(old_file, new_file)
        
        # Rotate current log to .1
        os.rename(log_file, f"{log_file}.1")
        print(f"[INFO] Rotated log file: {os.path.basename(log_file)} ({size_mb:.1f}MB)")
    except Exception as e:
        print(f"[WARN] Log rotation failed: {e}")

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
    """Logger for trade activities"""
    def __init__(self, pair_id, child_id):
        self.pair_id = pair_id
        self.child_id = child_id
        self.log_dir = os.path.join(DATA_DIR, "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, f"child_{pair_id}_{child_id}.log")
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] [{level}] {message}"
        print(line)
        try:
            rotate_log_if_needed(self.log_file)  # Check if rotation needed
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(line + "\n")
        except:
            pass
        # Also save to JSON for dashboard
        self._save_activity(message, level)
    
    def _save_activity(self, message, level):
        """Save activity to JSON file for dashboard"""
        try:
            json_file = os.path.join(self.log_dir, f"child_activity_{self.pair_id}_{self.child_id}.json")
            activities = []
            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        activities = json.load(f)
                except:
                    activities = []
            
            activity = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "message": message,
                "type": level
            }
            activities.insert(0, activity)
            activities = activities[:10000]  # Keep last 10000 entries
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(activities, f)
        except:
            pass

def load_config(pair_id, child_id):
    """Load configuration for the specified pair and child"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8-sig') as f:
            config = json.load(f)
        
        pairs = config.get('pairs', [])
        for pair in pairs:
            if pair.get('id') == pair_id:
                children = pair.get('children', [])
                for child in children:
                    if child.get('id') == child_id:
                        return pair, child
        return None, None
    except Exception as e:
        print(f"Error loading config: {e}")
        return None, None

def write_child_data(pair_id, child_id, balance, equity, positions):
    """Write child account data to binary file for dashboard"""
    try:
        data_dir = os.path.join(DATA_DIR, "data")
        
        filename = os.path.join(data_dir, f"child_data_{pair_id}_{child_id}.bin")
        
        # Header: timestamp(8) + balance(8) + equity(8) + count(4) = 28 bytes
        timestamp = int(time.time() * 1000)
        count = len(positions) if positions else 0
        
        with open(filename, 'wb') as f:
            # Write header
            f.write(struct.pack('<Q', timestamp))
            f.write(struct.pack('<d', balance))
            f.write(struct.pack('<d', equity))
            f.write(struct.pack('<I', count))
            
            # Write positions (64 bytes each)
            for pos in positions:
                # ticket(8) + type(1) + volume(8) + sl(8) + tp(8) + symbol(15) + price_open(8) + profit(8) = 64
                symbol_bytes = pos.symbol.encode('utf-8')[:15].ljust(15, b'\x00')
                f.write(struct.pack('<Q', pos.ticket))
                f.write(struct.pack('<B', pos.type))
                f.write(struct.pack('<d', pos.volume))
                f.write(struct.pack('<d', pos.sl))
                f.write(struct.pack('<d', pos.tp))
                f.write(symbol_bytes)
                f.write(struct.pack('<d', pos.price_open))
                f.write(struct.pack('<d', pos.profit))
    except Exception as e:
        pass


def map_symbol(master_symbol, child_config, pair_config=None):
    """
    Map master symbol to child symbol based on child's symbol mapping configuration.
    
    New format: child['symbols'] = [{master: 'EURUSD', child: 'EURUSD.b'}, ...]
    Old format (backward compat): master_symbol_X in pair, child_symbol_X in child
    """
    try:
        master_sym_upper = master_symbol.upper().strip()
        
        # NEW FORMAT: Check child's own symbols list
        child_symbols = child_config.get('symbols', [])
        if child_symbols and isinstance(child_symbols, list):
            for mapping in child_symbols:
                if isinstance(mapping, dict):
                    m_sym = mapping.get('master', '').upper().strip()
                    c_sym = mapping.get('child', '').strip()
                    if m_sym == master_sym_upper and c_sym:
                        return c_sym
        
        # OLD FORMAT (backward compatibility): Check numbered slots
        # Master symbols from pair, child symbols from child
        for i in range(1, 21):
            # Get master symbol from pair config (if provided) or child config
            master_slot = ''
            if pair_config:
                master_slot = pair_config.get(f'master_symbol_{i}', '').upper().strip()
            if not master_slot:
                master_slot = child_config.get(f'master_symbol_{i}', '').upper().strip()
            
            child_slot_key = f'child_symbol_{i}'
            
            if master_slot and master_slot == master_sym_upper:
                child_sym = child_config.get(child_slot_key, '').strip()
                if child_sym:
                    return child_sym
        
        # Fallback to symbol_override for backward compatibility
        override = child_config.get('symbol_override', '').strip()
        if override:
            return override
        
        # Return original symbol if no mapping found
        return master_symbol
    except Exception as e:
        return master_symbol

def open_trade(symbol, trade_type, volume, sl, tp, magic, comment, log, copy_mode='normal'):
    """Open a new trade on child account with retry logic"""
    max_retries = 3
    
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
        if trade_type != 0:  # Not a BUY
            log.log(f"Skipping SELL signal - only_buy mode active", "INFO")
            return True
    elif copy_mode == 'only_sell':
        if trade_type != 1:  # Not a SELL
            log.log(f"Skipping BUY signal - only_sell mode active", "INFO")
            return True
    
    for attempt in range(max_retries):
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                log.log(f"Symbol {symbol} not found, attempt {attempt+1}/{max_retries}", "WARN")
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                    continue
                return False
            
            if not info.visible:
                if not mt5.symbol_select(symbol, True):
                    log.log(f"Failed to select symbol {symbol}", "ERROR")
                    if attempt < max_retries - 1:
                        time.sleep(0.2)
                        continue
                    return False
                time.sleep(0.1)
            
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                log.log(f"No tick data for {symbol}, attempt {attempt+1}/{max_retries}", "WARN")
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                    continue
                return False
            
            type_str = "BUY" if trade_type == 0 else "SELL"
            price = tick.ask if trade_type == 0 else tick.bid
            
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
                "type": mt5.ORDER_TYPE_BUY if trade_type == 0 else mt5.ORDER_TYPE_SELL,
                "price": price,
                "deviation": 50,  # Increased deviation for better fills
                "magic": magic,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }
            
            if sl > 0:
                request["sl"] = sl
            if tp > 0:
                request["tp"] = tp
            
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

def save_child_closed_trade(pair_id, child_id, trade_data):
    """Save closed trade to JSON file for dashboard"""
    try:
        data_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'JD_MT5_TradeCopier', 'data')
        closed_file = os.path.join(data_dir, f"closed_trades_{pair_id}_{child_id}.json")
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
    except Exception as e:
        print(f"[WARN] Error saving child closed trade: {e}")



def modify_sltp(ticket, symbol, new_sl, new_tp, log):
    """Modify SL/TP on an existing position"""
    try:
        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            return False
        
        p = pos[0]
        # Skip if values are the same
        if abs(p.sl - new_sl) < 0.00001 and abs(p.tp - new_tp) < 0.00001:
            return True  # Already set
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": ticket,
            "sl": new_sl,
            "tp": new_tp,
        }
        
        result = mt5.order_send(request)
        if result is None:
            err = mt5.last_error()
            log.log(f"Modify SL/TP failed - no response. Error: {err}", "ERROR")
            return False
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            log.log(f"Modified SL/TP on {symbol}: SL={new_sl}, TP={new_tp}", "TRADE")
            return True
        else:
            log.log(f"Modify SL/TP failed: {result.retcode}", "ERROR")
            return False
            
    except Exception as e:
        log.log(f"Modify SL/TP error: {e}", "ERROR")
        return False

def modify_pending_sltp(ticket, new_sl, new_tp, log):
    """Modify SL/TP on an existing pending order"""
    try:
        orders = mt5.orders_get(ticket=ticket)
        if not orders:
            log.log(f"Modify pending SL/TP - order {ticket} not found", "ERROR")
            return False
        
        order = orders[0]
        if abs(order.sl - new_sl) < 0.00001 and abs(order.tp - new_tp) < 0.00001:
            return True
        
        # Try different filling modes - some brokers are picky
        filling_modes = [mt5.ORDER_FILLING_RETURN, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]
        
        for filling_mode in filling_modes:
            request = {
                "action": mt5.TRADE_ACTION_MODIFY,
                "order": ticket,
                "symbol": order.symbol,
                "price": order.price_open,
                "type_time": order.type_time,
                "expiration": order.time_expiration,
                "type_filling": filling_mode,
            }
            # Only add SL/TP if they have valid values (not 0)
            if new_sl > 0:
                request["sl"] = new_sl
            if new_tp > 0:
                request["tp"] = new_tp
            
            result = mt5.order_send(request)
            if result is None:
                err = mt5.last_error()
                log.log(f"Modify pending SL/TP failed with filling {filling_mode}: {err}", "DEBUG")
                continue
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                log.log(f"Modified pending order {ticket}: SL={new_sl}, TP={new_tp}", "TRADE")
                return True
            else:
                log.log(f"Modify pending SL/TP retcode {result.retcode}: {result.comment}", "DEBUG")
                continue
        
        # All modes failed
        log.log(f"Modify pending SL/TP failed - all filling modes tried", "ERROR")
        return False
    except Exception as e:
        log.log(f"Modify pending SL/TP error: {e}", "ERROR")
        return False

def modify_pending_price(ticket, new_price, new_sl, new_tp, log):
    """Modify price on an existing pending order"""
    try:
        orders = mt5.orders_get(ticket=ticket)
        if not orders:
            log.log(f"Modify pending price - order {ticket} not found", "ERROR")
            return False
        
        order = orders[0]
        
        # Try different filling modes - some brokers are picky
        filling_modes = [mt5.ORDER_FILLING_RETURN, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]
        
        for filling_mode in filling_modes:
            request = {
                "action": mt5.TRADE_ACTION_MODIFY,
                "order": ticket,
                "symbol": order.symbol,
                "price": new_price,
                "type_time": order.type_time,
                "expiration": order.time_expiration,
                "type_filling": filling_mode,
            }
            # Only add SL/TP if they have valid values (not 0)
            if new_sl > 0:
                request["sl"] = new_sl
            if new_tp > 0:
                request["tp"] = new_tp
            
            result = mt5.order_send(request)
            if result is None:
                err = mt5.last_error()
                log.log(f"Modify pending price failed with filling {filling_mode}: {err}", "DEBUG")
                continue
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                log.log(f"Modified pending order {ticket}: Price={new_price}, SL={new_sl}, TP={new_tp}", "TRADE")
                return True
            else:
                log.log(f"Modify pending price retcode {result.retcode}: {result.comment}", "DEBUG")
                continue
        
        # All modes failed
        log.log(f"Modify pending price failed - all filling modes tried", "ERROR")
        return False
            
    except Exception as e:
        log.log(f"Modify pending price error: {e}", "ERROR")
        return False

def open_pending_order(symbol, order_type, volume, price, sl, tp, master_ticket, comment, log, copy_mode='normal'):
    """Open a pending order on child account with copy mode support"""
    try:
        # Log received parameters
        log.log(f"open_pending_order CALLED: symbol={symbol}, type={order_type}, price={price}, sl={sl}, tp={tp}, mode={copy_mode}", "DEBUG")
        
        # Apply ONLY_BUY / ONLY_SELL filter
        if copy_mode == 'only_buy' and order_type not in [2, 4]:  # Not BUY_LIMIT or BUY_STOP
            log.log(f"Skipping SELL pending order - only_buy mode active", "INFO")
            return True  # Return True to mark as handled
        elif copy_mode == 'only_sell' and order_type not in [3, 5]:  # Not SELL_LIMIT or SELL_STOP
            log.log(f"Skipping BUY pending order - only_sell mode active", "INFO")
            return True  # Return True to mark as handled
        
        # Apply REVERSE mode type mapping
        original_type = order_type
        original_price = price
        original_sl = sl
        original_tp = tp
        
        if copy_mode == 'reverse':
            # Correct reverse mapping for pending orders:
            # The key is to map to order types that TRIGGER at the same price level
            # BUY_LIMIT(2) -> SELL_STOP(5) : both trigger when price DROPS to the level
            # SELL_LIMIT(3) -> BUY_STOP(4) : both trigger when price RISES to the level
            # BUY_STOP(4) -> SELL_LIMIT(3) : both trigger when price RISES to the level
            # SELL_STOP(5) -> BUY_LIMIT(2) : both trigger when price DROPS to the level
            reverse_map = {2: 5, 3: 4, 4: 3, 5: 2}
            order_type = reverse_map.get(order_type, order_type)
            
            # With this mapping, the SAME PRICE works correctly because:
            # - BUY_LIMIT at 1.0900 (below current) -> SELL_STOP at 1.0900 (also needs below current) 
            # - SELL_LIMIT at 1.1100 (above current) -> BUY_STOP at 1.1100 (also needs above current) 
            
            # Swap SL and TP for reverse mode
            if sl > 0 and tp > 0:
                sl, tp = tp, sl
            elif sl > 0 and tp == 0:
                tp = sl
                sl = 0
            elif tp > 0 and sl == 0:
                sl = tp
                tp = 0
            
            order_names = {2: 'BUY_LIMIT', 3: 'SELL_LIMIT', 4: 'BUY_STOP', 5: 'SELL_STOP'}
            log.log(f"REVERSE PENDING: {order_names.get(original_type, original_type)}->{order_names.get(order_type, order_type)}, Price={price:.5f}, SL {original_sl}->{sl}, TP {original_tp}->{tp}", "DEBUG")
        
        log.log(f"open_pending_order: {symbol} type={order_type} vol={volume} price={price} sl={sl} tp={tp}", "DEBUG")
        info = mt5.symbol_info(symbol)
        if info is None:
            log.log(f"Symbol {symbol} not found for pending order", "WARN")
            return False
        
        if not info.visible:
            mt5.symbol_select(symbol, True)
            time.sleep(0.1)
        
        # Order type mapping: 2=BUY_LIMIT, 3=SELL_LIMIT, 4=BUY_STOP, 5=SELL_STOP
        action_map = {
            2: mt5.ORDER_TYPE_BUY_LIMIT,
            3: mt5.ORDER_TYPE_SELL_LIMIT,
            4: mt5.ORDER_TYPE_BUY_STOP,
            5: mt5.ORDER_TYPE_SELL_STOP,
        }
        
        mt5_order_type = action_map.get(order_type)
        if mt5_order_type is None:
            log.log(f"Unsupported pending order type: {order_type}", "WARN")
            return False
        
        # Log the final SL/TP values being used
        log.log(f"PENDING ORDER REQUEST: symbol={symbol}, type={order_type}, price={price:.5f}, SL={sl}, TP={tp}", "DEBUG")
        
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": volume,
            "type": mt5_order_type,
            "price": price,
            "deviation": 20,
            "magic": master_ticket % 1000000000,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        # Only add SL/TP if > 0
        if sl > 0:
            request["sl"] = sl
        if tp > 0:
            request["tp"] = tp
        
        log.log(f"Sending pending order with request: SL={request.get('sl', 0)}, TP={request.get('tp', 0)}", "DEBUG")
        result = mt5.order_send(request)
        if result is None:
            log.log(f"Pending order failed - no response", "ERROR")
            return False
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            order_name = ['','','BUY_LIMIT','SELL_LIMIT','BUY_STOP','SELL_STOP'][order_type] if order_type <= 5 else 'PENDING'
            mode_str = f" [{copy_mode.upper()}]" if copy_mode != 'normal' else ""
            log.log(f"Pending order placed: {order_name} {volume} {symbol} @ {price}{mode_str}", "TRADE")
            return True
        else:
            log.log(f"Pending order failed: {result.retcode} - {result.comment}", "ERROR")
            return False
            
    except Exception as e:
        log.log(f"Pending order error: {e}", "ERROR")
        return False

def close_trade(ticket, symbol, trade_type, volume, log):
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
                return {'success': True, 'price': price, 'profit': result.profit if hasattr(result, 'profit') else 0}
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
            # First, try to find by magic number (exact match)
            for pos in positions:
                if pos.magic == master_ticket:
                    return pos.ticket
            
            # If not found by magic, find positions with our copy comment
            for pos in positions:
                if pos.comment and f"copy_{master_ticket}" in pos.comment:
                    return pos.ticket
        
        return None
    except:
        return None

def main(pair_id, child_id):
    """Main function for child executor"""
    if not pair_id or not child_id:
        print("ERROR: --pair-id and --child-id arguments required!")
        return
    
    log = TradeLog(pair_id, child_id)
    
    log.log("=" * 50, "INFO")
    log.log(f"CHILD EXECUTOR STARTED - Pair: {pair_id}, Child: {child_id}", "INFO")
    log.log("=" * 50, "INFO")
    
    pair, child = load_config(pair_id, child_id)
    if not pair or not child:
        log.log("ERROR: Configuration not found!", "ERROR")
        return
    
    # Get terminal path and strip whitespace, newlines, and quotes
    child_terminal = child.get('terminal', '').strip().strip('"').strip("'")
    child_account = int(child.get('account', 0))
    child_password = child.get('password', '')
    child_server = child.get('server', '')
    
    log.log(f"Child Account: {child_account}", "INFO")
    log.log(f"Server: {child_server}", "INFO")
    
    
    # Validate symbols are configured  
    has_symbols = False
    
    # NEW FORMAT: Check child's own symbols list first
    child_symbols = child.get('symbols', [])
    if child_symbols and isinstance(child_symbols, list):
        for mapping in child_symbols:
            if isinstance(mapping, dict):
                m_sym = mapping.get('master', '').strip()
                c_sym = mapping.get('child', '').strip()
                if m_sym and c_sym:
                    has_symbols = True
                    log.log(f"Symbol mapping: {m_sym} -> {c_sym}", "INFO")
        log.log(f"Total symbol mappings configured: {len([m for m in child_symbols if isinstance(m, dict) and m.get('master') and m.get('child')])}", "INFO")
    
    # OLD FORMAT (backward compat): Check numbered slots
    if not has_symbols:
        for i in range(1, 21):
            master_sym = pair.get(f'master_symbol_{i}', '').strip().upper()
            child_sym = child.get(f'child_symbol_{i}', '').strip().upper()
            if master_sym and child_sym:
                has_symbols = True
                log.log(f"Symbol slot {i}: {master_sym} -> {child_sym}", "INFO")

    if not has_symbols:
        log.log('ERROR: No symbols configured for this child account!', 'ERROR')
        log.log('Please add at least one symbol mapping in the child account settings.', 'ERROR')
        log.log('Go to Accounts -> Edit Child -> Add Symbol (set both Master and Child symbols)', 'ERROR')
        return
    # Initialize MT5
    init_args = {}
    if child_terminal:
        init_args['path'] = child_terminal
    
    if not mt5.initialize(**init_args):
        log.log(f"MT5 init failed: {mt5.last_error()}", "ERROR")
        return
    
    # Login
    if not mt5.login(child_account, password=child_password, server=child_server):
        log.log(f"Login failed: {mt5.last_error()}", "ERROR")
        mt5.shutdown()
        return
    
    acc = mt5.account_info()
    if not acc:
        log.log("Cannot get account info!", "ERROR")
        mt5.shutdown()
        return
    
    log.log(f"Connected: {acc.login} @ {acc.server}", "INFO")
    log.log(f"Balance: ${acc.balance:.2f}", "INFO")
    
    # Write initial child data
    try:
        child_positions = mt5.positions_get() or []
        write_child_data(pair_id, child_id, acc.balance, acc.equity, child_positions)
    except:
        pass
    
    log.log("Waiting for signals...", "INFO")
    
    # Shared memory file
    SHARED_FILE = os.path.join(DATA_DIR, "data", f"shared_positions_{pair_id}.bin")
    
    f = None
    mm = None
    
    try:
        f = open(SHARED_FILE, 'r+b')
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    except Exception as e:
        log.log(f"ERROR opening shared file: {e}", "ERROR")
        return
    
    tracked_master = {}  # master_ticket -> child_ticket
    pending_track = {}   # master_ticket -> {'symbol': ..., 'attempts': 0, 'time': ...}
    copied_pending_orders = {}  # master_ticket -> True (tracks which pending orders have been copied)
    last_log = 0
    error_count = 0
    first_run = True  # Flag to track first iteration
    
    try:
        while True:
            try:
                # Reload config for live changes
                pair, child = load_config(pair_id, child_id)
                if not pair or not child:
                    time.sleep(0.5)
                    continue
                
                # Check if pair and child are enabled
                if not pair.get('enabled', True) or not child.get('enabled', True):
                    time.sleep(0.5)
                    continue
                
                # Check if we're within the active copy period
                copy_period_enabled = child.get('copy_period_enabled', False)
                active_from = child.get('active_from', '') or ''
                active_to = child.get('active_to', '') or ''
                
                # Strip whitespace and validate dates
                active_from = active_from.strip() if isinstance(active_from, str) else ''
                active_to = active_to.strip() if isinstance(active_to, str) else ''
                
                # Check copy period if enabled OR if dates are explicitly set
                if copy_period_enabled or (active_from and len(active_from) >= 10) or (active_to and len(active_to) >= 10):
                    from datetime import date
                    today = date.today().isoformat()  # Format: YYYY-MM-DD
                    
                    # Only check active_from if valid date string
                    if active_from and len(active_from) >= 10:
                        if today < active_from:
                            if time.time() - last_log > 300:
                                log.log(f"Copy period not started. From: {active_from}, Today: {today}", "INFO")
                                last_log = time.time()
                            time.sleep(1)
                            continue
                    
                    # Only check active_to if valid date string
                    if active_to and len(active_to) >= 10:
                        if today > active_to:
                            if time.time() - last_log > 300:
                                log.log(f"Copy period ended. Until: {active_to}, Today: {today}", "INFO")
                                last_log = time.time()
                            time.sleep(1)
                            continue
                
                # Update settings from config
                lot_multiplier = child.get('lot_multiplier', 1.0)
                copy_mode = child.get('copy_mode', 'normal')
                copy_close = to_bool(child.get('copy_close'), True)
                force_copy = to_bool(child.get('force_copy'), False)
                
                # Child copy settings (per-child account) - ensure proper boolean conversion
                copy_sl = to_bool(child.get('copy_sl'), True)
                copy_tp = to_bool(child.get('copy_tp'), True)
                copy_pending = to_bool(child.get('copy_pending'), True)
                
                # Read shared memory - Header: timestamp(8) + balance(8) + equity(8) + count(4) = 28 bytes
                mm.seek(0)
                data = mm.read(HEADER_SIZE)
                if len(data) < HEADER_SIZE:
                    time.sleep(0.01)
                    continue
                
                ts = struct.unpack("<Q", data[0:8])[0]
                pos_count = struct.unpack("<I", data[24:28])[0]
                ord_count = struct.unpack("<I", data[28:32])[0]
                
                master_now = {}
                master_orders = {}  # Initialize here for pending exec detection
                for i in range(pos_count):
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
                
                # Process pending tracking (positions that were opened but not yet mapped)
                for master_ticket in list(pending_track.keys()):
                    info = pending_track[master_ticket]
                    # Skip pending order entries - they don't need position mapping
                    if info.get('is_pending_order', False):
                        continue
                    if info['attempts'] >= 10:
                        # Give up after 10 attempts
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
                
                # Detect executed pending orders: if master_ticket is in copied_pending_orders
                # but now appears as a POSITION (not pending order), it was executed
                for master_ticket in list(copied_pending_orders.keys()):
                    if master_ticket in master_now and master_ticket not in master_orders:
                        # Pending order was executed and is now a position
                        log.log(f"PENDING EXECUTED: Master #{master_ticket} pending order now a position", "INFO")
                        del copied_pending_orders[master_ticket]
                        if master_ticket in pending_track:
                            del pending_track[master_ticket]
                        # Find the child pending order and add to position tracking
                        child_orders = mt5.orders_get()
                        child_positions = mt5.positions_get()
                        # Try to find child position by comment
                        if child_positions:
                            for cp in child_positions:
                                if cp.comment and f"pending_{str(master_ticket)[:8]}" in cp.comment:
                                    tracked_master[master_ticket] = cp.ticket
                                    log.log(f"Mapped executed pending: master {master_ticket} -> child {cp.ticket}", "INFO")
                                    break
                
                # Open new positions
                for master_ticket, pos in master_now.items():
                    # Skip if already tracked or pending
                    if master_ticket in tracked_master or master_ticket in pending_track or master_ticket in copied_pending_orders:
                        continue
                    
                    # CHECK: Is this symbol in our allowed list?
                    incoming_symbol = pos['symbol'].upper().strip()
                    symbol_allowed = False
                    
                    # NEW FORMAT: Check child's own symbols list first
                    child_symbols = child.get('symbols', [])
                    if child_symbols and isinstance(child_symbols, list):
                        for mapping in child_symbols:
                            if isinstance(mapping, dict):
                                m_sym = mapping.get('master', '').upper().strip()
                                c_sym = mapping.get('child', '').strip()
                                if m_sym == incoming_symbol and c_sym:
                                    symbol_allowed = True
                                    log.log(f"Symbol {incoming_symbol} ALLOWED (new format: {m_sym}->{c_sym})", "INFO")
                                    break
                    
                    # OLD FORMAT (backward compatibility): Check numbered slots
                    if not symbol_allowed:
                        for slot_i in range(1, 21):
                            master_sym = pair.get(f'master_symbol_{slot_i}', '').strip().upper()
                            child_sym = child.get(f'child_symbol_{slot_i}', '').strip().upper()
                            if master_sym == incoming_symbol and child_sym:
                                symbol_allowed = True
                                log.log(f"Symbol {incoming_symbol} ALLOWED (slot {slot_i}: {master_sym}->{child_sym})", "INFO")
                                break
                    
                    if not symbol_allowed:
                        log.log(f"Symbol {incoming_symbol} NOT CONFIGURED - SKIPPING trade #{master_ticket}", "WARN")
                        tracked_master[master_ticket] = -1  # Mark as skipped
                        continue
                    
                    # Process new trade (already verified not tracked above)
                    if True:
                        # On first run with force_copy disabled, skip existing positions
                        if first_run and not force_copy:
                            tracked_master[master_ticket] = -1  # Mark as existed before start
                            log.log(f"Skipping existing position {master_ticket} (force_copy disabled)", "INFO")
                            continue
                        
                        child_volume = round(pos['volume'] * lot_multiplier, 2)
                        if child_volume < 0.01:
                            child_volume = 0.01
                        
                        log.log(f"NEW SIGNAL: {pos['symbol']} detected from master", "SIGNAL")
                        
                        mapped_symbol = map_symbol(pos['symbol'], child, pair)
                        success = open_trade(
                            mapped_symbol, 
                            pos['type'], 
                            child_volume,
                            pos['sl'] if copy_sl else 0,
                            pos['tp'] if copy_tp else 0,
                            master_ticket,
                            f"copy_{master_ticket}",
                            log,
                            copy_mode
                        )
                        
                        # Update trade stats
                        update_trade_stats(pair_id, success)
                        
                        if success:
                            # Add to pending tracking
                            pending_track[master_ticket] = {
                                'symbol': pos['symbol'],
                                'attempts': 0,
                                'time': time.time()
                            }
                            # Try immediate lookup
                            time.sleep(0.05)
                            child_ticket = find_child_position(master_ticket, pos['symbol'], log)
                            if child_ticket:
                                tracked_master[master_ticket] = child_ticket
                                log.log(f"Mapped master {master_ticket} -> child {child_ticket}", "INFO")
                                del pending_track[master_ticket]
                        else:
                            # Mark as failed to prevent retry spam
                            tracked_master[master_ticket] = -1
                

                # Update SL/TP on existing positions if changed on master
                if copy_sl or copy_tp:
                    for master_ticket, child_ticket in tracked_master.items():
                        if child_ticket > 0 and master_ticket in master_now:
                            # Skip if we recently failed to modify this position
                            fail_key = f"sltp_fail_{child_ticket}"
                            if fail_key in pending_track:
                                if time.time() - pending_track[fail_key].get('time', 0) < 5:
                                    continue  # Wait 5 seconds before retrying
                            
                            master_pos = master_now[master_ticket]
                            child_pos = mt5.positions_get(ticket=child_ticket)
                            if child_pos:
                                cp = child_pos[0]
                                new_sl = master_pos['sl'] if copy_sl else cp.sl
                                new_tp = master_pos['tp'] if copy_tp else cp.tp
                                
                                # REVERSE mode: Swap SL and TP for opposite positions
                                if copy_mode == 'reverse':
                                    if new_sl > 0 and new_tp > 0:
                                        new_sl, new_tp = new_tp, new_sl  # Swap both
                                    elif new_sl > 0 and new_tp == 0:
                                        new_tp = new_sl
                                        new_sl = 0
                                    elif new_tp > 0 and new_sl == 0:
                                        new_sl = new_tp
                                        new_tp = 0
                                
                                # Check if SL/TP changed
                                if abs(cp.sl - new_sl) > 0.00001 or abs(cp.tp - new_tp) > 0.00001:
                                    result = modify_sltp(child_ticket, cp.symbol, new_sl, new_tp, log)
                                    if not result:
                                        pending_track[fail_key] = {'time': time.time()}
                # Close positions (if copy_close enabled)
                if copy_close:
                    closed_tickets = []
                    
                    # First, iterate over a copy of items to avoid modification during iteration
                    for master_ticket, child_ticket in list(tracked_master.items()):
                        if master_ticket not in master_now:
                            if child_ticket > 0:
                                child_pos = mt5.positions_get(ticket=child_ticket)
                                if child_pos:
                                    cp = child_pos[0]
                                    log.log(f"CLOSE SIGNAL: Master closed {cp.symbol}", "SIGNAL")
                                    close_result = close_trade(cp.ticket, cp.symbol, cp.type, cp.volume, log)
                                    if close_result and close_result.get('success'):
                                        import datetime
                                        save_child_closed_trade(pair_id, child_id, {
                                            'ticket': cp.ticket,
                                            'symbol': cp.symbol,
                                            'type': cp.type,
                                            'volume': cp.volume,
                                            'price_open': cp.price_open,
                                            'close_price': close_result.get('price', 0),
                                            'profit': cp.profit,
                                            'close_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                        })
                                else:
                                    # Position already closed on child side
                                    log.log(f"Child position {child_ticket} already closed", "DEBUG")
                            closed_tickets.append(master_ticket)
                    
                    for t in closed_tickets:
                        if t in tracked_master:
                            del tracked_master[t]
                        if t in pending_track:
                            del pending_track[t]
                    
                    # BULK CLOSE DETECTION: Close all child positions if master has zero
                    tracked_count = len([t for t in tracked_master.values() if t > 0])
                    if len(master_now) == 0 and tracked_count > 0:
                        log.log(f"BULK CLOSE TRIGGERED: master has 0 positions, closing {tracked_count} tracked", "SIGNAL")
                    if len(master_now) == 0:
                        # Get all child positions that belong to our copy trades
                        all_child_positions = mt5.positions_get()
                        if all_child_positions:
                            for cp in all_child_positions:
                                # Check if this is one of our copied positions
                                # Match by: comment contains 'copy_' OR 'pending_' OR magic number matches
                                is_our_position = False
                                if cp.comment and ('copy_' in cp.comment or 'pending_' in cp.comment):
                                    is_our_position = True
                                if cp.ticket in tracked_master.values():
                                    is_our_position = True
                                if cp.magic in tracked_master.keys():
                                    is_our_position = True
                                
                                if is_our_position:
                                    log.log(f"BULK CLOSE: Closing position {cp.symbol} #{cp.ticket}", "SIGNAL")
                                    try:
                                        close_result = close_trade(cp.ticket, cp.symbol, cp.type, cp.volume, log)
                                        if close_result and close_result.get('success'):
                                            import datetime
                                            save_child_closed_trade(pair_id, child_id, {
                                                'ticket': cp.ticket, 'symbol': cp.symbol, 'type': cp.type,
                                                'volume': cp.volume, 'price_open': cp.price_open,
                                                'close_price': close_result.get('price', 0), 'profit': cp.profit,
                                                'close_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                            })
                                    except Exception as e:
                                        log.log(f"BULK CLOSE ERROR: {e}", "ERROR")
                        
                        # Clear tracked_master of any remaining entries with valid child tickets
                        remaining = [(mt, ct) for mt, ct in tracked_master.items() if ct > 0]
                        for master_ticket, child_ticket in remaining:
                            del tracked_master[master_ticket]
                            if master_ticket in pending_track:
                                del pending_track[master_ticket]
                        
                        if remaining:
                            log.log(f"BULK CLOSE: Cleared {len(remaining)} tracked entries", "INFO")

                # Read and copy pending orders if enabled
                if copy_pending:
                    master_orders = {}
                    
                    # Read orders from shared memory if any exist
                    if ord_count > 0:
                        log.log(f"Reading {ord_count} pending orders from master", "DEBUG")
                        mm.seek(HEADER_SIZE + MAX_POSITIONS * POSITION_SIZE)
                        for i in range(ord_count):
                            ord_data = mm.read(ORDER_SIZE)
                            if len(ord_data) < ORDER_SIZE:
                                break
                            
                            ticket = struct.unpack('Q', ord_data[0:8])[0]
                            otype = struct.unpack('B', ord_data[8:9])[0]
                            volume = struct.unpack('d', ord_data[9:17])[0]
                            price = struct.unpack('d', ord_data[17:25])[0]
                            o_sl = struct.unpack('d', ord_data[25:33])[0]
                            o_tp = struct.unpack('d', ord_data[33:41])[0]
                            symbol = ord_data[41:56].decode('utf-8').rstrip('\x00')
                            
                            master_orders[ticket] = {
                                'symbol': symbol, 'type': otype, 'volume': volume,
                                'price': price, 'sl': o_sl, 'tp': o_tp
                            }
                            log.log(f"Read order #{ticket}: {symbol} sl={o_sl} tp={o_tp}", "DEBUG")
                        
                        # Check for new pending orders to copy
                        for master_ticket, order in master_orders.items():
                            if master_ticket not in tracked_master and master_ticket not in pending_track and master_ticket not in copied_pending_orders:
                                incoming_symbol = order['symbol'].strip().upper()
                                
                                symbol_allowed = False
                                
                                # NEW FORMAT: Check child's own symbols list first
                                child_symbols = child.get('symbols', [])
                                if child_symbols and isinstance(child_symbols, list):
                                    for mapping in child_symbols:
                                        if isinstance(mapping, dict):
                                            m_sym = mapping.get('master', '').upper().strip()
                                            c_sym = mapping.get('child', '').strip()
                                            if m_sym == incoming_symbol and c_sym:
                                                symbol_allowed = True
                                                break
                                
                                # OLD FORMAT (backward compatibility): Check numbered slots
                                if not symbol_allowed:
                                    for slot_i in range(1, 21):
                                        master_sym = pair.get(f'master_symbol_{slot_i}', '').strip().upper()
                                        child_sym = child.get(f'child_symbol_{slot_i}', '').strip().upper()
                                        if master_sym == incoming_symbol and child_sym:
                                            symbol_allowed = True
                                            break
                                
                                if not symbol_allowed:
                                    log.log(f"Pending symbol {incoming_symbol} NOT CONFIGURED", "WARN")
                                    continue

                                child_volume = round(order['volume'] * lot_multiplier, 2)
                                if child_volume < 0.01:
                                    child_volume = 0.01
                                
                                log.log(f"NEW PENDING: {order['symbol']} type={order['type']} vol={child_volume} sl={order['sl']} tp={order['tp']}", "SIGNAL")
                                mapped_symbol = map_symbol(order['symbol'], child, pair)
                                
                                success = open_pending_order(
                                    mapped_symbol,
                                    order['type'],
                                    child_volume,
                                    order['price'],
                                    order['sl'] if copy_sl else 0,
                                    order['tp'] if copy_tp else 0,
                                    master_ticket,
                                    f"pending_{master_ticket}",
                                    log,
                                    copy_mode
                                )
                                
                                if success:
                                    # Store ORIGINAL (unswapped) values for comparison with master
                                    # The swap is applied when modifying, not when tracking
                                    track_sl = order['sl'] if copy_sl else 0
                                    track_tp = order['tp'] if copy_tp else 0
                                    pending_track[master_ticket] = {
                                        'symbol': order['symbol'], 
                                        'time': time.time(), 
                                        'price': order['price'], 
                                        'sl': track_sl,  # ORIGINAL master SL
                                        'tp': track_tp,  # ORIGINAL master TP
                                        'attempts': 0, 
                                        'is_pending_order': True
                                    }
                                    copied_pending_orders[master_ticket] = True
                                    log.log(f'Tracking pending #{master_ticket} with master sl={track_sl} tp={track_tp}', 'INFO')

                        # Update Price/SL/TP on existing pending orders if changed on master
                        for master_ticket, order in master_orders.items():
                            if master_ticket in pending_track:
                                tracked = pending_track[master_ticket]
                                if not tracked.get('is_pending_order', False):
                                    continue
                                
                                # Get ORIGINAL values from master (unswapped)
                                new_price = order['price']
                                master_sl = order['sl'] if copy_sl else 0
                                master_tp = order['tp'] if copy_tp else 0
                                
                                # Compare with ORIGINAL tracked values
                                old_price = tracked.get('price', 0)
                                old_sl = tracked.get('sl', 0)
                                old_tp = tracked.get('tp', 0)
                                
                                price_diff = abs(new_price - old_price)
                                sl_diff = abs(master_sl - old_sl)
                                tp_diff = abs(master_tp - old_tp)
                                
                                # NOW apply swap for sending to child
                                child_sl = master_sl
                                child_tp = master_tp
                                if copy_mode == 'reverse':
                                    if master_sl > 0 and master_tp > 0:
                                        child_sl, child_tp = master_tp, master_sl
                                    elif master_sl > 0 and master_tp == 0:
                                        child_tp = master_sl
                                        child_sl = 0
                                    elif master_tp > 0 and master_sl == 0:
                                        child_sl = master_tp
                                        child_tp = 0
                                
                                if price_diff > 0.00001 or sl_diff > 0.00001 or tp_diff > 0.00001:
                                    # Rate limit: skip if last modification failed within 5 seconds
                                    last_fail = tracked.get('last_modify_fail', 0)
                                    if time.time() - last_fail < 5:
                                        continue
                                    
                                    log.log(f"PENDING MODIFIED #{master_ticket}: price={old_price}->{new_price} master_sl={old_sl}->{master_sl} master_tp={old_tp}->{master_tp} child_sl={child_sl} child_tp={child_tp}", "INFO")
                                    
                                    child_orders = mt5.orders_get()
                                    
                                    found = False
                                    if child_orders:
                                        for child_order in child_orders:
                                            # Match by comment containing master ticket
                                            if f"pending_{str(master_ticket)[:8]}" in child_order.comment:
                                                log.log(f"Found matching order {child_order.ticket}, modifying with child_sl={child_sl}, child_tp={child_tp}", "INFO")
                                                if price_diff > 0.00001:
                                                    # Price changed - use modify_pending_price
                                                    result = modify_pending_price(child_order.ticket, new_price, child_sl, child_tp, log)
                                                else:
                                                    # Only SL/TP changed
                                                    result = modify_pending_sltp(child_order.ticket, child_sl, child_tp, log)
                                                if result:
                                                    # Store ORIGINAL master values for next comparison
                                                    pending_track[master_ticket]['price'] = order['price']
                                                    pending_track[master_ticket]['sl'] = master_sl
                                                    pending_track[master_ticket]['tp'] = master_tp
                                                    pending_track[master_ticket].pop('last_modify_fail', None)
                                                else:
                                                    pending_track[master_ticket]['last_modify_fail'] = time.time()
                                                found = True
                                                break
                                    
                                    if not found:
                                        log.log(f"Could not find child order for master #{master_ticket}", "WARN")

                    # Cancel pending orders that were deleted on master
                    pending_to_cancel = []
                    for tracked_ticket in list(pending_track.keys()):
                        if pending_track[tracked_ticket].get('is_pending_order', False):
                            if tracked_ticket not in master_orders:
                                pending_to_cancel.append(tracked_ticket)
                                log.log(f"Master pending #{tracked_ticket} no longer exists, will cancel child", "INFO")
                    
                    for tracked_ticket in pending_to_cancel:
                        child_orders = mt5.orders_get()
                        found = False
                        if child_orders:
                            for order in child_orders:
                                if order.comment.startswith(f"pending_{str(tracked_ticket)[:8]}"):
                                    log.log(f"Cancelling child pending order {order.ticket}", "INFO")
                                    request = {
                                        "action": mt5.TRADE_ACTION_REMOVE,
                                        "order": order.ticket,
                                    }
                                    result = mt5.order_send(request)
                                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                                        log.log(f"Cancelled pending order {order.ticket} successfully", "CLOSE")
                                    else:
                                        log.log(f"Failed to cancel order {order.ticket}: {result.retcode if result else 'no result'}", "ERROR")
                                    found = True
                                    break
                        
                        if not found:
                            log.log(f"Child order for master #{tracked_ticket} not found (may already be gone)", "DEBUG")
                        
                        del pending_track[tracked_ticket]
                        if tracked_ticket in copied_pending_orders:
                            del copied_pending_orders[tracked_ticket]

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
                
                # Mark first run complete
                if first_run:
                    first_run = False
                    if not force_copy:
                        skipped = len([t for t in tracked_master.values() if t == -1])
                        log.log(f"First run complete. Skipped {skipped} existing positions.", "INFO")
                
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
    # Parse command line arguments
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











