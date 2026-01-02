content = open("child_executor_new.py", "r", encoding="utf-8").read()

# Add type_filling to the modify request - some brokers require this
old_request = '''        request = {
            "action": mt5.TRADE_ACTION_MODIFY,
            "order": ticket,
            "symbol": order.symbol,
            "price": new_price,
            "sl": new_sl,
            "tp": new_tp,
            "type_time": order.type_time,
            "expiration": order.time_expiration,
        }'''

new_request = '''        request = {
            "action": mt5.TRADE_ACTION_MODIFY,
            "order": ticket,
            "symbol": order.symbol,
            "price": new_price,
            "sl": new_sl,
            "tp": new_tp,
            "type_time": order.type_time,
            "expiration": order.time_expiration,
            "type_filling": mt5.ORDER_FILLING_IOC,  # Required by some brokers
        }'''

if old_request in content:
    content = content.replace(old_request, new_request)
    open("child_executor_new.py", "w", encoding="utf-8").write(content)
    print("Added type_filling to modify_pending_price")
else:
    print("Pattern not found")