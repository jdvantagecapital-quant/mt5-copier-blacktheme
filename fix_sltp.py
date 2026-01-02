content = open("child_executor_new.py", "r", encoding="utf-8").read()

# Fix modify_pending_sltp - add type_filling and remove duplicate log
old = '''        request = {
            "action": mt5.TRADE_ACTION_MODIFY,
            "order": ticket,
            "symbol": order.symbol,
            "price": order.price_open,
            "sl": new_sl,
            "tp": new_tp,
            "type_time": order.type_time,
            "expiration": order.time_expiration,
        }
        
        log.log(f'Modify request: ticket={ticket}, sl={new_sl}, tp={new_tp}', 'DEBUG')
        log.log(f'Modify request: ticket={ticket}, sl={new_sl}, tp={new_tp}', 'DEBUG')
        result = mt5.order_send(request)
        if result is None:
            log.log(f"Modify pending SL/TP failed - no response", "ERROR")
            return False'''

new = '''        request = {
            "action": mt5.TRADE_ACTION_MODIFY,
            "order": ticket,
            "symbol": order.symbol,
            "price": order.price_open,
            "sl": new_sl,
            "tp": new_tp,
            "type_time": order.type_time,
            "expiration": order.time_expiration,
            "type_filling": mt5.ORDER_FILLING_IOC,  # Required by some brokers
        }
        
        log.log(f'Modify pending SLTP request: ticket={ticket}, sl={new_sl}, tp={new_tp}', 'DEBUG')
        result = mt5.order_send(request)
        if result is None:
            err = mt5.last_error()
            log.log(f"Modify pending SL/TP failed - no response. Error: {err}", "ERROR")
            return False'''

if old in content:
    content = content.replace(old, new)
    open("child_executor_new.py", "w", encoding="utf-8").write(content)
    print("Fixed modify_pending_sltp")
else:
    print("Pattern not found")