with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and update the buildCard function - add date filter button to header
old_header = '''html += '<div class="acc-header"><div class="acc-info"><span class="acc-badge ' + type + '">' + type.toUpperCase() + '</span><span class="acc-num">' + account + '</span></div>';
    html += '<div class="acc-status ' + (connected ? 'on' : 'off') + '"><i class="fas fa-circle"></i> ' + (connected ? 'On' : 'Off') + '</div></div>';'''

new_header = '''html += '<div class="acc-header"><div class="acc-info"><span class="acc-badge ' + type + '">' + type.toUpperCase() + '</span><span class="acc-num">' + account + '</span></div>';
    html += '<div style="display:flex;align-items:center;gap:8px;">';
    html += '<button class="date-filter-btn" onclick="toggleDateFilter(event, \\'' + cardId + '\\')" title="Filter by date"><i class="fas fa-calendar-alt"></i><span id="filter_label_' + cardId + '">All</span></button>';
    html += '<div class="acc-status ' + (connected ? 'on' : 'off') + '"><i class="fas fa-circle"></i> ' + (connected ? 'On' : 'Off') + '</div></div></div>';
    html += '<div class="date-filter-popup" id="datefilter_' + cardId + '">';
    html += '<div class="filter-presets">';
    html += '<button class="filter-preset active" onclick="applyDatePreset(\\'' + cardId + '\\', \\'all\\')">All</button>';
    html += '<button class="filter-preset" onclick="applyDatePreset(\\'' + cardId + '\\', \\'today\\')">Today</button>';
    html += '<button class="filter-preset" onclick="applyDatePreset(\\'' + cardId + '\\', \\'yesterday\\')">Yesterday</button>';
    html += '<button class="filter-preset" onclick="applyDatePreset(\\'' + cardId + '\\', \\'week\\')">This Week</button>';
    html += '</div>';
    html += '<div class="date-range-inputs"><input type="date" class="date-input" id="from_' + cardId + '" placeholder="From"><input type="date" class="date-input" id="to_' + cardId + '" placeholder="To"></div>';
    html += '<button class="filter-apply-btn" onclick="applyCustomDateRange(\\'' + cardId + '\\')"><i class="fas fa-filter"></i> Apply Range</button>';
    html += '</div>';'''

content = content.replace(old_header, new_header)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Step 2: Added date filter button')
