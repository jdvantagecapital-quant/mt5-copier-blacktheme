"""Fix JavaScript activity slice limits in dashboard template"""
import re

file_path = r'C:\Users\MI\MT5-Copier-new\Templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix: activities.slice(0, 100) -> activities.slice(0, 5000)
content = re.sub(r'activities\.slice\(0,\s*100\)', 'activities.slice(0, 5000)', content)

# Fix: closedTrades.slice(0, 50) -> closedTrades.slice(0, 500)
content = re.sub(r'closedTrades\.slice\(0,\s*50\)', 'closedTrades.slice(0, 500)', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Templates/index.html: Updated JavaScript slice limits')
print('- activities.slice(0, 5000)')
print('- closedTrades.slice(0, 500)')
