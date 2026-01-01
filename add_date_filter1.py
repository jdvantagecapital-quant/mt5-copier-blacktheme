import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add CSS for date filter (before the closing </style>)
date_filter_css = '''
    /* Date Filter */
    .date-filter-btn { 
        background: rgba(102,126,234,0.1); 
        border: 1px solid rgba(102,126,234,0.2); 
        color: #667eea; 
        padding: 4px 8px; 
        border-radius: 4px; 
        font-size: 9px; 
        cursor: pointer; 
        display: flex; 
        align-items: center; 
        gap: 4px;
        transition: all 0.2s;
    }
    .date-filter-btn:hover { background: rgba(102,126,234,0.2); }
    .date-filter-btn.active { background: rgba(102,126,234,0.3); border-color: #667eea; }
    .date-filter-popup {
        position: absolute;
        top: 100%;
        right: 0;
        background: #111;
        border: 1px solid #333;
        border-radius: 6px;
        padding: 10px;
        z-index: 100;
        min-width: 200px;
        display: none;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    .date-filter-popup.show { display: block; }
    .filter-presets { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
    .filter-preset { 
        padding: 4px 10px; 
        background: #1a1a1a; 
        border: 1px solid #333; 
        border-radius: 4px; 
        color: #888; 
        font-size: 9px; 
        cursor: pointer;
        transition: all 0.2s;
    }
    .filter-preset:hover { background: #222; color: #aaa; }
    .filter-preset.active { background: rgba(102,126,234,0.2); border-color: #667eea; color: #667eea; }
    .date-range-inputs { display: flex; gap: 6px; margin-bottom: 8px; }
    .date-input { 
        flex: 1; 
        padding: 6px 8px; 
        background: #0a0a0a; 
        border: 1px solid #333; 
        border-radius: 4px; 
        color: #aaa; 
        font-size: 10px;
        font-family: 'JetBrains Mono', monospace;
    }
    .date-input:focus { border-color: #667eea; outline: none; }
    .filter-apply-btn {
        width: 100%;
        padding: 6px;
        background: rgba(102,126,234,0.2);
        border: 1px solid #667eea;
        border-radius: 4px;
        color: #667eea;
        font-size: 10px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }
    .filter-apply-btn:hover { background: rgba(102,126,234,0.3); }
    .acc-header { position: relative; }
'''

# Insert before </style>
content = content.replace('</style>\n{% endblock %}', date_filter_css + '</style>\n{% endblock %}')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Step 1: Added CSS')
