"""Add JSON activity logging to child_executor_new.py"""

file_path = r'C:\Users\MI\MT5-Copier-new\child_executor_new.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the TradeLog class and add JSON logging method
old_log_method = '''    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] [{level}] {message}"
        print(line)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(line + "\\n")
        except:
            pass'''

new_log_method = '''    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] [{level}] {message}"
        print(line)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(line + "\\n")
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
            pass'''

if old_log_method in content:
    content = content.replace(old_log_method, new_log_method)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Added JSON activity logging to child_executor_new.py')
else:
    print('Could not find log method to update - trying alternative pattern')
    # Try to find with regex
    import re
    pattern = r'(def log\(self, message, level="INFO"\):.*?pass)\n'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        print('Found log method via regex')
    else:
        print('Log method not found')
