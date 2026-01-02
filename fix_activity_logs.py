"""
Fix all activity log limits to show ALL logs
"""
import re

# Fix 1: master_watcher_new.py - Increase MAX_ACTIVITY_LOGS from 100 to 10000
file1 = r'C:\Users\MI\MT5-Copier-new\master_watcher_new.py'
with open(file1, 'r', encoding='utf-8') as f:
    content = f.read()
content = re.sub(r'MAX_ACTIVITY_LOGS\s*=\s*\d+', 'MAX_ACTIVITY_LOGS = 10000', content)
with open(file1, 'w', encoding='utf-8') as f:
    f.write(content)
print('1. master_watcher_new.py: MAX_ACTIVITY_LOGS = 10000')

# Fix 2: dashboard_new.py - Remove all activity limits
file2 = r'C:\Users\MI\MT5-Copier-new\dashboard_new.py'
with open(file2, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix activity limits in mt5-data API
# Change: activities[:20] -> activities (no limit)
content = re.sub(r'for act in activities\[:20\]:', 'for act in activities:', content)

# Change: master_activities[:500] -> master_activities  
content = re.sub(r'for log in master_activities\[:500\]:', 'for log in master_activities:', content)

# Fix child activity reading limit
content = re.sub(r'if len\(result\[.activities.\]\[child_id\]\) >= 20:', 'if False:  # No limit', content)

# Fix: lines[-50:] -> lines[-5000:]
content = re.sub(r'lines = f\.readlines\(\)\[-50:\]', 'lines = f.readlines()[-5000:]', content)
content = re.sub(r'lines = f\.readlines\(\)\[-500:\]', 'lines = f.readlines()[-5000:]', content)

with open(file2, 'w', encoding='utf-8') as f:
    f.write(content)
print('2. dashboard_new.py: Removed all activity limits')

# Fix 3: Check child_executor_new.py for logging
file3 = r'C:\Users\MI\MT5-Copier-new\child_executor_new.py'
with open(file3, 'r', encoding='utf-8') as f:
    content = f.read()

# Check if there's a MAX_LOG limit
if 'MAX_LOG' in content:
    content = re.sub(r'MAX_LOG\w*\s*=\s*\d+', 'MAX_LOG_LINES = 50000', content)
    with open(file3, 'w', encoding='utf-8') as f:
        f.write(content)
    print('3. child_executor_new.py: Updated MAX_LOG limit')
else:
    print('3. child_executor_new.py: No MAX_LOG limit found (text log file)')

print('')
print('=== Activity Log Fixes Applied ===')
print('- Master activity JSON: Keeps 10000 entries')
print('- Dashboard reads ALL master activities')
print('- Dashboard reads last 5000 lines from child logs')
print('- No artificial limits on activity display')
