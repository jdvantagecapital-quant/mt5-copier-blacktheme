#!/usr/bin/env python3
import re

def apply_dashboard_fixes():
    with open('dashboard_new.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # FIX 1: Update update_child to include copy_sl, copy_tp, copy_pending
    old_pattern = "for key in ['name', 'terminal', 'account', 'password', 'server', 'lot_multiplier', 'copy_mode', 'copy_close', 'enabled', 'period', 'symbol_override', 'force_copy']:"
    new_pattern = "for key in ['name', 'terminal', 'account', 'password', 'server', 'lot_multiplier', 'copy_mode', 'copy_close', 'enabled', 'period', 'symbol_override', 'force_copy', 'copy_sl', 'copy_tp', 'copy_pending', 'active_from', 'active_to']:"
    
    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        print("FIX 1: Updated update_child to include copy_sl, copy_tp, copy_pending")
    else:
        print("FIX 1: Pattern not found or already fixed")
    
    if content != original_content:
        with open('dashboard_new.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Dashboard fixes saved!")
    else:
        print("No changes needed")

if __name__ == "__main__":
    apply_dashboard_fixes()
