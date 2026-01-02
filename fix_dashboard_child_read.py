"""Update dashboard to read child JSON activities first"""

file_path = r'C:\Users\MI\MT5-Copier-new\dashboard_new.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the child activity reading section
old_child_read = '''            # Read child activities from log file
            try:
                logs_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'JD_MT5_TradeCopier', 'logs')
                log_file = os.path.join(logs_dir, f'child_{pair_id}_{child_id}.log')
                
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()[-5000:]
                        for line in reversed(lines):
                            if any(tag in line for tag in ['[SIGNAL]', '[OPEN]', '[CLOSE]', '[ERROR]', '[WARN]', '[INFO]']):
                                # Parse log level
                                log_type = 'INFO'
                                if '[CLOSE]' in line: log_type = 'CLOSE'
                                elif '[SIGNAL]' in line: log_type = 'SIGNAL'
                                elif '[OPEN]' in line: log_type = 'TRADE'
                                elif '[ERROR]' in line: log_type = 'ERROR'
                                elif '[WARN]' in line: log_type = 'WARN'
                                
                                result['activities'][child_id].append({
                                    'time': line[1:20] if len(line) > 20 else '',
                                    'message': line.strip(),
                                    'type': log_type
                                })
                            if False:  # No limit
                                break
            except:
                pass'''

new_child_read = '''            # Read child activities - try JSON first, then fall back to log file
            try:
                logs_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'JD_MT5_TradeCopier', 'logs')
                json_file = os.path.join(logs_dir, f'child_activity_{pair_id}_{child_id}.json')
                log_file = os.path.join(logs_dir, f'child_{pair_id}_{child_id}.log')
                
                # Try JSON first (faster and structured)
                if os.path.exists(json_file):
                    with open(json_file, 'r', encoding='utf-8') as f:
                        activities = json.load(f)
                        for act in activities:
                            result['activities'][child_id].append({
                                'time': f"{act.get('date', '')} {act.get('time', '')}",
                                'message': act.get('message', ''),
                                'type': act.get('type', 'INFO')
                            })
                # Fall back to text log file
                elif os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()[-5000:]
                        for line in reversed(lines):
                            if any(tag in line for tag in ['[SIGNAL]', '[OPEN]', '[CLOSE]', '[ERROR]', '[WARN]', '[INFO]', '[DEBUG]']):
                                log_type = 'INFO'
                                if '[CLOSE]' in line: log_type = 'CLOSE'
                                elif '[SIGNAL]' in line: log_type = 'SIGNAL'
                                elif '[OPEN]' in line: log_type = 'TRADE'
                                elif '[ERROR]' in line: log_type = 'ERROR'
                                elif '[WARN]' in line: log_type = 'WARN'
                                elif '[DEBUG]' in line: log_type = 'DEBUG'
                                
                                result['activities'][child_id].append({
                                    'time': line[1:20] if len(line) > 20 else '',
                                    'message': line.strip(),
                                    'type': log_type
                                })
            except Exception as e:
                print(f"[WARN] Error reading child {child_id} activities: {e}")'''

if old_child_read in content:
    content = content.replace(old_child_read, new_child_read)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated dashboard to read child JSON activities first')
else:
    print('Could not find exact child read section - may need manual update')
    # Check what exists
    if 'child_activity_' in content:
        print('Already has child_activity_ JSON reading')
    else:
        print('Needs child_activity_ JSON reading added')
