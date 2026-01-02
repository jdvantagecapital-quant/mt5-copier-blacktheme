import re

def apply_add_child_fix():
    with open('dashboard_new.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Find the add_child new_child dict pattern and add missing fields
    old_pattern = '''            'copy_mode': data.get('copy_mode', 'normal'),
            'copy_close': data.get('copy_close', True),
            'enabled': data.get('enabled', True)
        }'''
    
    new_pattern = '''            'copy_mode': data.get('copy_mode', 'normal'),
            'copy_close': data.get('copy_close', True),
            'copy_sl': data.get('copy_sl', True),
            'copy_tp': data.get('copy_tp', True),
            'copy_pending': data.get('copy_pending', True),
            'active_from': data.get('active_from', ''),
            'active_to': data.get('active_to', ''),
            'period': data.get('period', 'M1'),
            'symbol_override': data.get('symbol_override', False),
            'force_copy': data.get('force_copy', False),
            'enabled': data.get('enabled', True)
        }'''
    
    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        print("FIX: Updated add_child with copy_sl, copy_tp, copy_pending, etc.")
    else:
        print("Pattern not found or already fixed")
    
    # Also add symbol fields to add_child
    add_symbol_fields = '''
        # Add symbol fields from data
        for i in range(1, 21):
            key = f'child_symbol_{i}'
            if key in data:
                new_child[key] = data[key].upper() if isinstance(data[key], str) else data[key]'''
    
    marker = "pair['children'].append(new_child)"
    if marker in content and "Add symbol fields from data" not in content:
        content = content.replace(marker, add_symbol_fields + "\n        \n        " + marker)
        print("FIX: Added symbol fields handling to add_child")
    
    if content != original_content:
        with open('dashboard_new.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Dashboard fixes saved!")
    else:
        print("No changes needed")

if __name__ == "__main__":
    apply_add_child_fix()
