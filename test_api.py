import urllib.request
import json

try:
    url = 'http://127.0.0.1:5000/api/pairs/pair_792a705c/mt5-data'
    r = urllib.request.urlopen(url, timeout=10)
    data = json.loads(r.read().decode())
    
    master_acts = data.get('master', {}).get('activities', [])
    print(f'Master Activities: {len(master_acts)}')
    
    children = data.get('children', {})
    for child_id, child_data in children.items():
        acts = child_data.get('activities', [])
        print(f'Child {child_id}: {len(acts)} activities')
        
except Exception as e:
    print(f'Error: {e}')
