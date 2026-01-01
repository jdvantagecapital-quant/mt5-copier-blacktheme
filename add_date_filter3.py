with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add date filter JavaScript functions before loadPairs();
date_filter_js = '''
// Date filter state
const dateFilters = {};

function toggleDateFilter(event, cardId) {
    event.stopPropagation();
    const popup = document.getElementById('datefilter_' + cardId);
    document.querySelectorAll('.date-filter-popup').forEach(p => {
        if (p.id !== 'datefilter_' + cardId) p.classList.remove('show');
    });
    popup.classList.toggle('show');
}

function applyDatePreset(cardId, preset) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    let fromDate = null;
    let toDate = new Date();
    toDate.setHours(23, 59, 59, 999);
    
    switch(preset) {
        case 'all':
            fromDate = null;
            toDate = null;
            break;
        case 'today':
            fromDate = today;
            break;
        case 'yesterday':
            fromDate = new Date(today);
            fromDate.setDate(fromDate.getDate() - 1);
            toDate = new Date(today);
            toDate.setMilliseconds(-1);
            break;
        case 'week':
            fromDate = new Date(today);
            fromDate.setDate(fromDate.getDate() - 7);
            break;
    }
    
    dateFilters[cardId] = { from: fromDate, to: toDate, preset: preset };
    
    const label = document.getElementById('filter_label_' + cardId);
    if (label) label.textContent = preset.charAt(0).toUpperCase() + preset.slice(1);
    
    const popup = document.getElementById('datefilter_' + cardId);
    popup.querySelectorAll('.filter-preset').forEach(btn => {
        btn.classList.toggle('active', btn.textContent.toLowerCase() === preset);
    });
    
    popup.classList.remove('show');
    renderAccounts();
}

function applyCustomDateRange(cardId) {
    const fromInput = document.getElementById('from_' + cardId);
    const toInput = document.getElementById('to_' + cardId);
    
    let fromDate = fromInput.value ? new Date(fromInput.value) : null;
    let toDate = toInput.value ? new Date(toInput.value) : null;
    
    if (fromDate) fromDate.setHours(0, 0, 0, 0);
    if (toDate) toDate.setHours(23, 59, 59, 999);
    
    dateFilters[cardId] = { from: fromDate, to: toDate, preset: 'custom' };
    
    const label = document.getElementById('filter_label_' + cardId);
    if (label) {
        if (fromDate && toDate) {
            label.textContent = fromDate.toLocaleDateString('en-US', {month:'short', day:'numeric'}) + '-' + toDate.toLocaleDateString('en-US', {month:'short', day:'numeric'});
        } else if (fromDate) {
            label.textContent = 'From ' + fromDate.toLocaleDateString('en-US', {month:'short', day:'numeric'});
        } else if (toDate) {
            label.textContent = 'To ' + toDate.toLocaleDateString('en-US', {month:'short', day:'numeric'});
        }
    }
    
    const popup = document.getElementById('datefilter_' + cardId);
    popup.querySelectorAll('.filter-preset').forEach(btn => btn.classList.remove('active'));
    
    popup.classList.remove('show');
    renderAccounts();
}

function filterTradesByDate(trades, cardId) {
    const filter = dateFilters[cardId];
    if (!filter || (!filter.from && !filter.to)) return trades;
    
    return trades.filter(t => {
        if (!t.close_time) return true;
        const tradeDate = new Date(t.close_time * 1000);
        if (filter.from && tradeDate < filter.from) return false;
        if (filter.to && tradeDate > filter.to) return false;
        return true;
    });
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('.date-filter-btn') && !e.target.closest('.date-filter-popup')) {
        document.querySelectorAll('.date-filter-popup').forEach(p => p.classList.remove('show'));
    }
});

'''

content = content.replace('loadPairs();', date_filter_js + 'loadPairs();')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Step 3: Added date filter JS functions')
