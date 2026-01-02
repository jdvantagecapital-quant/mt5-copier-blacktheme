#!/usr/bin/env python3
"""
Apply all fixes to child_executor_new.py for copy modes and pending orders
"""
import re

def apply_fixes():
    # Read the file
    with open('child_executor_new.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # ============================================
    # FIX 1: Replace open_pending_order to handle REVERSE mode type mapping
    # ============================================
    
    old_open_pending = '''def open_pending_order(symbol, order_type, volume, price, sl, tp, master_ticket, comment, log):
    """Open a pending order on child account"""
    try:
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
            return False'''
    
    new_open_pending = '''def open_pending_order(symbol, order_type, volume, price, sl, tp, master_ticket, comment, log, copy_mode='normal'):
    """Open a pending order on child account with copy mode support"""
    try:
        # Apply ONLY_BUY / ONLY_SELL filter
        if copy_mode == 'only_buy' and order_type not in [2, 4]:  # Not BUY_LIMIT or BUY_STOP
            log.log(f"Skipping SELL pending order - only_buy mode active", "INFO")
            return True  # Return True to mark as handled
        elif copy_mode == 'only_sell' and order_type not in [3, 5]:  # Not SELL_LIMIT or SELL_STOP
            log.log(f"Skipping BUY pending order - only_sell mode active", "INFO")
            return True  # Return True to mark as handled
        
        # Apply REVERSE mode type mapping
        original_type = order_type
        if copy_mode == 'reverse':
            # BUY_LIMIT(2) <-> SELL_LIMIT(3), BUY_STOP(4) <-> SELL_STOP(5)
            reverse_map = {2: 3, 3: 2, 4: 5, 5: 4}
            order_type = reverse_map.get(order_type, order_type)
            # Also swap SL and TP for reverse mode
            if sl > 0 and tp > 0:
                sl, tp = tp, sl
            elif sl > 0 and tp == 0:
                tp = sl
                sl = 0
            elif tp > 0 and sl == 0:
                sl = tp
                tp = 0
            log.log(f"REVERSE: Pending type {original_type} -> {order_type}, SL/TP swapped", "DEBUG")
        
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
            return False'''
    
    if old_open_pending in content:
        content = content.replace(old_open_pending, new_open_pending)
        print("FIX 1: Updated open_pending_order with REVERSE/ONLY_BUY/ONLY_SELL support")
    else:
        print("FIX 1: open_pending_order pattern not found - may already be fixed")
    
    # ============================================
    # FIX 2: Update pending order result log to show copy mode
    # ============================================
    
    old_pending_log = '''if result.retcode == mt5.TRADE_RETCODE_DONE:
            order_name = ['','','BUY_LIMIT','SELL_LIMIT','BUY_STOP','SELL_STOP'][order_type] if order_type <= 5 else 'PENDING'
            log.log(f"Pending order placed: {order_name} {volume} {symbol} @ {price}", "TRADE")
            return True'''
    
    new_pending_log = '''if result.retcode == mt5.TRADE_RETCODE_DONE:
            order_name = ['','','BUY_LIMIT','SELL_LIMIT','BUY_STOP','SELL_STOP'][order_type] if order_type <= 5 else 'PENDING'
            mode_str = f" [{copy_mode.upper()}]" if copy_mode != 'normal' else ""
            log.log(f"Pending order placed: {order_name} {volume} {symbol} @ {price}{mode_str}", "TRADE")
            return True'''
    
    if old_pending_log in content:
        content = content.replace(old_pending_log, new_pending_log)
        print("FIX 2: Updated pending order success log with copy mode")
    else:
        print("FIX 2: Pending log pattern not found")
    
    # ============================================
    # FIX 3: Add modify_pending_price function after modify_pending_sltp
    # ============================================
    
    # Check if function already exists
    if 'def modify_pending_price(' not in content:
        # Find the end of modify_pending_sltp function
        pattern = r'(def modify_pending_sltp\(ticket, new_sl, new_tp, log\):.*?return False\s*\n)'
        
        new_function = '''def modify_pending_price(ticket, new_price, new_sl, new_tp, log):
    """Modify price on an existing pending order"""
    try:
        orders = mt5.orders_get(ticket=ticket)
        if not orders:
            return False
        
        order = orders[0]
        
        request = {
            "action": mt5.TRADE_ACTION_MODIFY,
            "order": ticket,
            "symbol": order.symbol,
            "price": new_price,
            "sl": new_sl,
            "tp": new_tp,
            "type_time": order.type_time,
            "expiration": order.time_expiration,
        }
        
        result = mt5.order_send(request)
        if result is None:
            log.log(f"Modify pending price failed - no response", "ERROR")
            return False
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            log.log(f"Modified pending order {ticket}: Price={new_price}, SL={new_sl}, TP={new_tp}", "TRADE")
            return True
        else:
            log.log(f"Modify pending price failed: {result.retcode} - {result.comment}", "ERROR")
            return False
            
    except Exception as e:
        log.log(f"Modify pending price error: {e}", "ERROR")
        return False

'''
        
        # Find and insert after modify_pending_sltp
        match = re.search(r'(def modify_pending_sltp\(ticket, new_sl, new_tp, log\):.*?return False\n)', content, re.DOTALL)
        if match:
            insert_pos = match.end()
            content = content[:insert_pos] + '\n' + new_function + content[insert_pos:]
            print("FIX 3: Added modify_pending_price function")
        else:
            print("FIX 3: Could not find modify_pending_sltp to insert after")
    else:
        print("FIX 3: modify_pending_price already exists")
    
    # ============================================
    # FIX 4: Update the pending order copy call to include copy_mode
    # ============================================
    
    old_pending_call = '''success = open_pending_order(
                                    mapped_symbol,
                                    order['type'],
                                    child_volume,
                                    order['price'],
                                    order['sl'] if copy_sl else 0,
                                    order['tp'] if copy_tp else 0,
                                    master_ticket,
                                    f"pending_{master_ticket}",
                                    log
                                )'''
    
    new_pending_call = '''success = open_pending_order(
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
                                )'''
    
    if old_pending_call in content:
        content = content.replace(old_pending_call, new_pending_call)
        print("FIX 4: Updated open_pending_order call to pass copy_mode")
    else:
        print("FIX 4: Pending order call pattern not found")
    
    # ============================================
    # FIX 5: Add pending track entry with price for price modification detection
    # ============================================
    
    old_pending_track = '''if success:
                                    pending_track[master_ticket] = {'symbol': order['symbol'], 'time': time.time(), 'sl': order['sl'], 'tp': order['tp'], 'attempts': 0, 'is_pending_order': True}'''
    
    new_pending_track = '''if success:
                                    pending_track[master_ticket] = {'symbol': order['symbol'], 'time': time.time(), 'price': order['price'], 'sl': order['sl'], 'tp': order['tp'], 'attempts': 0, 'is_pending_order': True}'''
    
    if old_pending_track in content:
        content = content.replace(old_pending_track, new_pending_track)
        print("FIX 5: Added price tracking to pending_track")
    else:
        print("FIX 5: Pending track pattern not found")
    
    # ============================================
    # FIX 6: Update pending order modification to include PRICE changes and REVERSE mode SL/TP swap
    # ============================================
    
    old_pending_modify = '''# Update SL/TP on existing pending orders if changed on master
                        for master_ticket, order in master_orders.items():
                            if master_ticket in pending_track:
                                tracked = pending_track[master_ticket]
                                if not tracked.get('is_pending_order', False):
                                    continue
                                    
                                new_sl = order['sl'] if copy_sl else 0
                                new_tp = order['tp'] if copy_tp else 0
                                old_sl = tracked.get('sl', 0)
                                old_tp = tracked.get('tp', 0)
                                
                                sl_diff = abs(new_sl - old_sl)
                                tp_diff = abs(new_tp - old_tp)
                                
                                if sl_diff > 0.00001 or tp_diff > 0.00001:
                                    log.log(f"SL/TP CHANGED for #{master_ticket}: old_sl={old_sl} new_sl={new_sl} old_tp={old_tp} new_tp={new_tp}", "INFO")
                                    
                                    child_orders = mt5.orders_get()
                                    log.log(f"Child has {len(child_orders) if child_orders else 0} pending orders", "DEBUG")
                                    
                                    found = False
                                    if child_orders:
                                        for child_order in child_orders:
                                            log.log(f"Checking child order {child_order.ticket} comment='{child_order.comment}'", "DEBUG")
                                            if child_order.comment.startswith(f"pending_{str(master_ticket)[:8]}"):
                                                log.log(f"Found matching order {child_order.ticket}, modifying SL/TP", "INFO")
                                                result = modify_pending_sltp(child_order.ticket, new_sl, new_tp, log)
                                                if result:
                                                    pending_track[master_ticket]['sl'] = order['sl']
                                                    pending_track[master_ticket]['tp'] = order['tp']
                                                found = True
                                                break
                                    
                                    if not found:
                                        log.log(f"Could not find child order for master #{master_ticket}", "WARN")'''
    
    new_pending_modify = '''# Update Price/SL/TP on existing pending orders if changed on master
                        for master_ticket, order in master_orders.items():
                            if master_ticket in pending_track:
                                tracked = pending_track[master_ticket]
                                if not tracked.get('is_pending_order', False):
                                    continue
                                
                                # Get values from master
                                new_price = order['price']
                                new_sl = order['sl'] if copy_sl else 0
                                new_tp = order['tp'] if copy_tp else 0
                                
                                # Apply REVERSE mode SL/TP swap
                                if copy_mode == 'reverse':
                                    if new_sl > 0 and new_tp > 0:
                                        new_sl, new_tp = new_tp, new_sl
                                    elif new_sl > 0 and new_tp == 0:
                                        new_tp = new_sl
                                        new_sl = 0
                                    elif new_tp > 0 and new_sl == 0:
                                        new_sl = new_tp
                                        new_tp = 0
                                
                                old_price = tracked.get('price', 0)
                                old_sl = tracked.get('sl', 0)
                                old_tp = tracked.get('tp', 0)
                                
                                price_diff = abs(new_price - old_price)
                                sl_diff = abs(new_sl - old_sl)
                                tp_diff = abs(new_tp - old_tp)
                                
                                if price_diff > 0.00001 or sl_diff > 0.00001 or tp_diff > 0.00001:
                                    log.log(f"PENDING MODIFIED #{master_ticket}: price={old_price}->{new_price} sl={old_sl}->{new_sl} tp={old_tp}->{new_tp}", "INFO")
                                    
                                    child_orders = mt5.orders_get()
                                    log.log(f"Child has {len(child_orders) if child_orders else 0} pending orders", "DEBUG")
                                    
                                    found = False
                                    if child_orders:
                                        for child_order in child_orders:
                                            if child_order.comment.startswith(f"pending_{str(master_ticket)[:8]}"):
                                                log.log(f"Found matching order {child_order.ticket}, modifying", "INFO")
                                                if price_diff > 0.00001:
                                                    # Price changed - use modify_pending_price
                                                    result = modify_pending_price(child_order.ticket, new_price, new_sl, new_tp, log)
                                                else:
                                                    # Only SL/TP changed
                                                    result = modify_pending_sltp(child_order.ticket, new_sl, new_tp, log)
                                                if result:
                                                    pending_track[master_ticket]['price'] = order['price']
                                                    pending_track[master_ticket]['sl'] = order['sl']
                                                    pending_track[master_ticket]['tp'] = order['tp']
                                                found = True
                                                break
                                    
                                    if not found:
                                        log.log(f"Could not find child order for master #{master_ticket}", "WARN")'''
    
    if old_pending_modify in content:
        content = content.replace(old_pending_modify, new_pending_modify)
        print("FIX 6: Updated pending order modification with PRICE + REVERSE SL/TP swap")
    else:
        print("FIX 6: Pending modify pattern not found - checking for variations...")
        # Try simpler pattern match
        if '# Update SL/TP on existing pending orders if changed on master' in content:
            print("FIX 6: Found the section header, may need manual fix")
    
    # ============================================
    # FIX 7: Update position SL/TP modification for REVERSE mode
    # ============================================
    
    old_sltp_update = '''# Update SL/TP on existing positions if changed on master
                if copy_sl or copy_tp:
                    for master_ticket, child_ticket in tracked_master.items():
                        if child_ticket > 0 and master_ticket in master_now:
                            master_pos = master_now[master_ticket]
                            child_pos = mt5.positions_get(ticket=child_ticket)
                            if child_pos:
                                cp = child_pos[0]
                                new_sl = master_pos['sl'] if copy_sl else cp.sl
                                new_tp = master_pos['tp'] if copy_tp else cp.tp
                                # Check if SL/TP changed
                                if abs(cp.sl - new_sl) > 0.00001 or abs(cp.tp - new_tp) > 0.00001:
                                    modify_sltp(child_ticket, cp.symbol, new_sl, new_tp, log)'''
    
    new_sltp_update = '''# Update SL/TP on existing positions if changed on master
                if copy_sl or copy_tp:
                    for master_ticket, child_ticket in tracked_master.items():
                        if child_ticket > 0 and master_ticket in master_now:
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
                                    modify_sltp(child_ticket, cp.symbol, new_sl, new_tp, log)'''
    
    if old_sltp_update in content:
        content = content.replace(old_sltp_update, new_sltp_update)
        print("FIX 7: Updated position SL/TP modification with REVERSE mode swap")
    else:
        # Check if already has REVERSE mode
        if "# REVERSE mode: Swap SL and TP" in content:
            print("FIX 7: REVERSE mode SL/TP swap already present")
        else:
            print("FIX 7: Position SL/TP pattern not found")
    
    # ============================================
    # Save the file
    # ============================================
    
    if content != original_content:
        with open('child_executor_new.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("\n=== All fixes applied and saved! ===")
    else:
        print("\n=== No changes made ===")

if __name__ == "__main__":
    apply_fixes()
