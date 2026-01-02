content = open("child_executor_new.py", "r", encoding="utf-8").read()

# Fix 1: Add last_error() and check if we need to add type_filling to modify_pending_price
old = '''        result = mt5.order_send(request)
        if result is None:
            log.log(f"Modify pending price failed - no response", "ERROR")
            return False'''

new = '''        log.log(f"Modify pending price request: {request}", "DEBUG")
        result = mt5.order_send(request)
        if result is None:
            err = mt5.last_error()
            log.log(f"Modify pending price failed - no response. Error: {err}", "ERROR")
            return False'''

if old in content:
    content = content.replace(old, new, 1)  # Only replace first occurrence
    open("child_executor_new.py", "w", encoding="utf-8").write(content)
    print("Added error logging to modify_pending_price")
else:
    print("Pattern not found - checking if already updated")