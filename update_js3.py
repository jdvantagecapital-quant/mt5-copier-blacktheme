file_path = r'C:\Users\MI\MT5-Copier-new\Templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

script_start = content.find('{% block extra_js %}')
if script_start == -1:
    print('Could not find script block')
    exit(1)

new_script = r"""{% block extra_js %}
<script>
// DASHBOARD v4.0 - Full Features: Individual filters, custom dates, all accounts, activity logs
let allPairs = [], selectedPairId = null, selectedPair = null, processStatus = {};
let globalStats = { total: 0, success: 0, failed: 0 }, isRunning = false;
let tradeData = { master: {}, children: {}, child_data: {}, activities: {}, closed_master: [], closed_children: {} };
let activeTab = {};
let cardFilters = {};  // { master: {type:'30days'}, child_0: {type:'custom', from:'2025-01-01', to:'2025-12-31'} }
let isLoading = false;

function formatDate(d) { 
    return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0'); 
}

function getCardDateParams(cardId) {
    const filter = cardFilters[cardId] || {type: '30days'};
    const today = new Date(); today.setHours(0,0,0,0);
    let from, to;
    switch(filter.type) {
        case 'today': from = to = formatDate(today); break;
        case 'yesterday': const y = new Date(today); y.setDate(y.getDate()-1); from = to = formatDate(y); break;
        case '7days': const s7 = new Date(today); s7.setDate(s7.getDate()-7); from = formatDate(s7); to = formatDate(today); break;
        case '30days': const s30 = new Date(today); s30.setDate(s30.getDate()-30); from = formatDate(s30); to = formatDate(today); break;
        case 'custom': from = filter.from || formatDate(today); to = filter.to || formatDate(today); break;
        default: const def = new Date(today); def.setDate(def.getDate()-30); from = formatDate(def); to = formatDate(today);
    }
    return { date_from: from, date_to: to };
}

function setCardFilter(cardId, type, btn) {
    cardFilters[cardId] = { type: type };
    const card = document.getElementById('card_' + cardId);
    if (card) {
        card.querySelectorAll('.card-filter-btn').forEach(b => b.classList.remove('active'));
        if (btn) btn.classList.add('active');
    }
    renderAccounts();
    renderPnlSection();
}

function applyCardCustomDate(cardId) {
    const fromEl = document.getElementById('date_from_' + cardId);
    const toEl = document.getElementById('date_to_' + cardId);
    if (fromEl && toEl && fromEl.value && toEl.value) {
        cardFilters[cardId] = { type: 'custom', from: fromEl.value, to: toEl.value };
        const card = document.getElementById('card_' + cardId);
        if (card) card.querySelectorAll('.card-filter-btn').forEach(b => b.classList.remove('active'));
        renderAccounts();
        renderPnlSection();
    }
}

function setPnlFilter(type, btn) {
    // Apply to all cards
    Object.keys(cardFilters).forEach(k => cardFilters[k] = { type: type });
    if (!cardFilters['master']) cardFilters['master'] = { type: type };
    document.querySelectorAll('.pnl-filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    loadData();
}

function applyPnlCustomDate() {
    const from = document.getElementById('pnl_from')?.value;
    const to = document.getElementById('pnl_to')?.value;
    if (from && to) {
        Object.keys(cardFilters).forEach(k => cardFilters[k] = { type: 'custom', from: from, to: to });
        cardFilters['master'] = { type: 'custom', from: from, to: to };
        document.querySelectorAll('.pnl-filter-btn').forEach(b => b.classList.remove('active'));
        loadData();
    }
}

async function loadPairs() {
    try { const res = await fetch('/api/pairs'); allPairs = await res.json(); } catch(e) { allPairs = []; }
    const select = document.getElementById('pairSelect');
    updateOverviewStats();
    if (!allPairs.length) {
        select.innerHTML = '<option value="">No pairs configured</option>';
        document.getElementById('accountsContainer').innerHTML = '<div class="no-pairs"><i class="fas fa-plug"></i><h3>No Copy Pairs</h3></div>';
        return;
    }
    select.innerHTML = allPairs.map(p => '<option value="'+p.id+'">'+(p.name||'Pair')+' ('+p.master_account+')</option>').join('');
    const saved = localStorage.getItem('selectedPairId');
    if (saved && allPairs.find(p => p.id === saved)) select.value = saved;
    selectPair();
}

function updateOverviewStats() {
    document.getElementById('totalPairs').textContent = allPairs.length;
    let tc = 0; allPairs.forEach(p => tc += (p.children||[]).length);
    document.getElementById('totalChildren').textContent = tc;
    document.getElementById('pairsStatus').textContent = allPairs.length > 0 ? 'Active' : 'None';
    document.getElementById('pairsStatus').className = 'overview-badge ' + (allPairs.length > 0 ? 'active' : 'inactive');
    document.getElementById('childrenStatus').textContent = tc > 0 ? 'Ready' : 'None';
    document.getElementById('childrenStatus').className = 'overview-badge ' + (tc > 0 ? 'active' : 'inactive');
}

function selectPair() {
    const select = document.getElementById('pairSelect');
    selectedPairId = select.value;
    localStorage.setItem('selectedPairId', selectedPairId);
    selectedPair = allPairs.find(p => p.id === selectedPairId);
    activeTab = {};
    // Initialize filters for all accounts
    cardFilters = { master: { type: '30days' } };
    if (selectedPair && selectedPair.children) {
        selectedPair.children.forEach((c, i) => {
            cardFilters['child_' + i] = { type: '30days' };
        });
    }
    loadData();
}

async function loadData() {
    if (!selectedPairId || !selectedPair) return;
    if (isLoading) return;
    isLoading = true;
    try {
        // 1. Process status
        try { const res = await fetch('/api/process-status'); processStatus = (await res.json()).status || {}; } catch(e) { processStatus = {}; }
        const pairStatus = processStatus[selectedPairId];
        isRunning = pairStatus && pairStatus.master_running;
        updateStatusUI();

        // 2. Get all data - fetch 90 days to allow flexible filtering
        const today = new Date(); today.setHours(0,0,0,0);
        const s90 = new Date(today); s90.setDate(s90.getDate() - 90);
        const url = '/api/pairs/' + selectedPairId + '/mt5-data?date_from=' + formatDate(s90) + '&date_to=' + formatDate(today);
        const res = await fetch(url);
        const data = await res.json();
        if (data.success) {
            tradeData = {
                master: data.master || { balance: 0, equity: 0, positions: [] },
                children: data.children || {},
                child_data: data.child_data || {},
                activities: data.activities || {},
                closed_master: data.closed_master || [],
                closed_children: data.closed_children || {}
            };
            tradeData.balance = data.master?.balance || data.balance || 0;
            tradeData.equity = data.master?.equity || data.equity || 0;
        }

        // 3. Global stats
        try { const res3 = await fetch('/api/status'); globalStats = (await res3.json()).stats || { total: 0, success: 0, failed: 0 }; } catch(e) { globalStats = { total: 0, success: 0, failed: 0 }; }
        
        renderAccounts();
        renderPnlSection();
        updateStats();
    } catch(e) { console.error('Load error:', e); }
    finally { isLoading = false; }
}

function filterByDate(trades, cardId) {
    if (!trades || !trades.length) return [];
    const params = getCardDateParams(cardId);
    const fromDate = new Date(params.date_from + 'T00:00:00');
    const toDate = new Date(params.date_to + 'T23:59:59');
    return trades.filter(t => {
        const closeTime = t.close_time || t.time_close || t.time;
        if (!closeTime) return true;
        const tradeDate = new Date(closeTime);
        return tradeDate >= fromDate && tradeDate <= toDate;
    });
}

function updateStatusUI() {
    const indicator = document.getElementById('statusIndicator');
    const dot = document.getElementById('statusDot');
    const txt = document.getElementById('statusText');
    if (isRunning) {
        indicator.className = 'status-indicator'; dot.className = 'status-dot'; txt.className = 'status-text'; txt.textContent = 'RUNNING';
        document.getElementById('btnStart').disabled = true; document.getElementById('btnStop').disabled = false;
    } else {
        indicator.className = 'status-indicator stopped'; dot.className = 'status-dot stopped'; txt.className = 'status-text stopped'; txt.textContent = 'STOPPED';
        document.getElementById('btnStart').disabled = false; document.getElementById('btnStop').disabled = true;
    }
}

function renderPnlSection() {
    if (!selectedPair) { document.getElementById('pnlGrid').innerHTML = ''; return; }
    
    // Master
    const masterPositions = tradeData.master?.positions || [];
    const masterFloating = masterPositions.reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
    const filteredClosedMaster = filterByDate(tradeData.closed_master || [], 'master');
    const masterClosed = filteredClosedMaster.reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
    const masterTotal = masterFloating + masterClosed;
    
    let html = '<div class="pnl-card master">';
    html += '<div class="pnl-card-header"><span class="pnl-account">' + selectedPair.master_account + '</span><span class="pnl-badge master">MASTER</span></div>';
    html += '<div class="pnl-value ' + (masterTotal >= 0 ? 'pos' : 'neg') + '">' + (masterTotal >= 0 ? '+' : '') + masterTotal.toFixed(2) + '</div>';
    html += '<div class="pnl-label">Total P/L</div>';
    html += '<div class="pnl-diff-row"><span class="pnl-diff-label">Floating (' + masterPositions.length + ')</span><span class="pnl-diff-val ' + (masterFloating >= 0 ? 'pos' : 'neg') + '">' + (masterFloating >= 0 ? '+' : '') + masterFloating.toFixed(2) + '</span></div>';
    html += '<div class="pnl-diff-row"><span class="pnl-diff-label">Closed (' + filteredClosedMaster.length + ')</span><span class="pnl-diff-val ' + (masterClosed >= 0 ? 'pos' : 'neg') + '">' + (masterClosed >= 0 ? '+' : '') + masterClosed.toFixed(2) + '</span></div>';
    html += '</div>';
    
    // All Children - use actual child IDs
    const children = selectedPair.children || [];
    children.forEach((child, i) => {
        const cid = child.id;
        const cardId = 'child_' + i;
        
        const childData = tradeData.children?.[cid] || {};
        const childPositions = Array.isArray(childData?.positions) ? childData.positions : (Array.isArray(childData) ? childData : []);
        const childFloating = childPositions.reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
        const filteredClosedChild = filterByDate(tradeData.closed_children?.[cid] || [], cardId);
        const childClosed = filteredClosedChild.reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
        const childTotal = childFloating + childClosed;
        const diff = childTotal - masterTotal;
        
        html += '<div class="pnl-card child">';
        html += '<div class="pnl-card-header"><span class="pnl-account">' + child.account + '</span><span class="pnl-badge child">CHILD ' + (i+1) + '</span></div>';
        html += '<div class="pnl-value ' + (childTotal >= 0 ? 'pos' : 'neg') + '">' + (childTotal >= 0 ? '+' : '') + childTotal.toFixed(2) + '</div>';
        html += '<div class="pnl-label">Total P/L</div>';
        html += '<div class="pnl-diff-row"><span class="pnl-diff-label">Floating (' + childPositions.length + ')</span><span class="pnl-diff-val ' + (childFloating >= 0 ? 'pos' : 'neg') + '">' + (childFloating >= 0 ? '+' : '') + childFloating.toFixed(2) + '</span></div>';
        html += '<div class="pnl-diff-row"><span class="pnl-diff-label">Closed (' + filteredClosedChild.length + ')</span><span class="pnl-diff-val ' + (childClosed >= 0 ? 'pos' : 'neg') + '">' + (childClosed >= 0 ? '+' : '') + childClosed.toFixed(2) + '</span></div>';
        html += '<div class="pnl-diff-row" style="background:rgba(255,68,102,0.08);margin:8px -14px -14px;padding:10px 14px;border-radius:0 0 5px 5px">';
        html += '<span class="pnl-diff-label" style="color:#ff4466;font-weight:600">vs Master</span>';
        html += '<span class="pnl-diff-val ' + (diff >= 0 ? 'pos' : 'neg') + '" style="font-weight:700">' + (diff >= 0 ? '+' : '') + diff.toFixed(2) + '</span></div>';
        html += '</div>';
    });
    
    document.getElementById('pnlGrid').innerHTML = html;
}

function parseActivity(activity) {
    if (!activity) return { time: '', type: 'INFO', message: '' };
    if (typeof activity === 'string') {
        // Format: "2026-01-02 13:08:44 | INFO | message"
        const parts = activity.split('|').map(p => p.trim());
        if (parts.length >= 3) {
            return { time: parts[0], type: parts[1], message: parts.slice(2).join(' | ') };
        }
        return { time: '', type: 'INFO', message: activity };
    }
    // Object format: {time, date, message, type}
    let timeStr = activity.time || '';
    if (activity.date && activity.time && !activity.time.includes('-')) {
        timeStr = activity.date + ' ' + activity.time;
    }
    return { 
        time: timeStr, 
        type: activity.type || 'INFO', 
        message: activity.message || activity.msg || JSON.stringify(activity)
    };
}

function renderAccounts() {
    const container = document.getElementById('accountsContainer');
    if (!selectedPair) { container.innerHTML = ''; return; }
    
    const children = selectedPair.children || [];
    
    // MASTER CARD
    const masterPositions = tradeData.master?.positions || [];
    const masterPnl = masterPositions.reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
    const masterActivities = tradeData.activities?.master || [];
    const filteredClosedMaster = filterByDate(tradeData.closed_master || [], 'master');
    
    let html = buildCard('master', 'master', selectedPair.master_account, 
        tradeData.master?.balance || tradeData.balance || 0, 
        tradeData.master?.equity || tradeData.equity || 0, 
        masterPositions, masterPnl, isRunning, masterActivities, filteredClosedMaster, tradeData.master?.error);
    
    // ALL CHILD CARDS
    children.forEach((child, i) => {
        const cid = child.id;
        const cardId = 'child_' + i;
        
        // Get child positions - try multiple sources
        let childPositions = [];
        const childData = tradeData.children?.[cid];
        if (childData) {
            if (Array.isArray(childData.positions)) childPositions = childData.positions;
            else if (Array.isArray(childData)) childPositions = childData;
        }
        
        // Get child account info
        const childInfo = tradeData.child_data?.[cid] || childData || {};
        const childPnl = childPositions.reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
        
        // Get child activities
        const childActivities = tradeData.activities?.[cid] || [];
        
        // Get closed trades
        const filteredClosedChild = filterByDate(tradeData.closed_children?.[cid] || [], cardId);
        
        const childConnected = isRunning && child.enabled;
        
        html += buildCard(cardId, 'child', child.account, 
            childInfo.balance || 0, 
            childInfo.equity || 0, 
            childPositions, childPnl, childConnected, childActivities, filteredClosedChild, childInfo.error);
    });
    
    // Preserve scroll
    const scrollPositions = {};
    container.querySelectorAll('.trades-tbl, .activity-panel').forEach(el => {
        const cardEl = el.closest('.acc-card');
        if (cardEl && el.scrollTop > 0) {
            scrollPositions[cardEl.id + '_' + (el.classList.contains('trades-tbl') ? 'trades' : 'activity')] = el.scrollTop;
        }
    });
    
    container.innerHTML = html;
    
    // Restore tabs
    for (const cid in activeTab) switchTab(cid, activeTab[cid]);
    
    // Restore scroll
    container.querySelectorAll('.trades-tbl, .activity-panel').forEach(el => {
        const cardEl = el.closest('.acc-card');
        if (cardEl) {
            const key = cardEl.id + '_' + (el.classList.contains('trades-tbl') ? 'trades' : 'activity');
            if (scrollPositions[key]) el.scrollTop = scrollPositions[key];
        }
    });
}

function buildCard(cardId, type, account, balance, equity, trades, pnl, connected, activities, closedTrades, error) {
    const pnlClass = pnl >= 0 ? 'pos' : 'neg';
    const currentTab = activeTab[cardId] || 'live';
    const filter = cardFilters[cardId] || { type: '30days' };
    const currentFilter = filter.type;
    
    let html = '<div class="acc-card ' + type + '" id="card_' + cardId + '">';
    
    // Header
    html += '<div class="acc-header"><div class="acc-info">';
    html += '<span class="acc-badge ' + type + '">' + type.toUpperCase() + '</span>';
    html += '<span class="acc-num">' + account + '</span></div>';
    html += '<div class="acc-status ' + (connected ? 'on' : 'off') + '"><i class="fas fa-circle"></i> ' + (connected ? 'Connected' : 'Offline') + '</div></div>';
    
    // Error
    if (error) html += '<div class="error-msg"><i class="fas fa-exclamation-triangle"></i> ' + error + '</div>';
    
    // Balance/Equity
    html += '<div class="bal-row"><div><div class="bal-label">Balance</div><div class="bal-value">$' + formatMoney(balance) + '</div></div>';
    html += '<div><div class="bal-label">Equity</div><div class="bal-value">$' + formatMoney(equity) + '</div></div></div>';
    
    // Date filter with custom date inputs
    html += '<div class="card-filter">';
    html += '<span class="card-filter-label"><i class="fas fa-calendar-alt"></i></span>';
    ['today','yesterday','7days','30days'].forEach(f => {
        const label = f === 'today' ? 'Today' : f === 'yesterday' ? 'Yest' : f === '7days' ? '7D' : '30D';
        html += '<button class="card-filter-btn ' + (currentFilter === f ? 'active' : '') + '" onclick="setCardFilter(\'' + cardId + '\',\'' + f + '\', this)">' + label + '</button>';
    });
    html += '<input type="date" class="card-date-input" id="date_from_' + cardId + '" title="From date">';
    html += '<input type="date" class="card-date-input" id="date_to_' + cardId + '" title="To date">';
    html += '<button class="card-filter-btn" onclick="applyCardCustomDate(\'' + cardId + '\')" title="Apply custom dates"><i class="fas fa-check"></i></button>';
    html += '</div>';
    
    // Tabs with counts
    const actCount = activities ? activities.length : 0;
    html += '<div class="acc-tabs">';
    html += '<button class="tab-btn ' + (currentTab === 'live' ? 'active' : '') + '" onclick="switchTab(\'' + cardId + '\',\'live\')">Live (' + trades.length + ')</button>';
    html += '<button class="tab-btn ' + (currentTab === 'closed' ? 'active' : '') + '" onclick="switchTab(\'' + cardId + '\',\'closed\')">Closed (' + (closedTrades?.length || 0) + ')</button>';
    html += '<button class="tab-btn ' + (currentTab === 'activity' ? 'active' : '') + '" onclick="switchTab(\'' + cardId + '\',\'activity\')">Activity (' + actCount + ')</button>';
    html += '</div>';
    
    // Live tab
    html += '<div class="tab-panel ' + (currentTab === 'live' ? 'show' : '') + '" id="' + cardId + '_live"><div class="trades-tbl">';
    html += '<div class="tbl-head"><span>Symbol</span><span>Type</span><span>Lots</span><span>Price</span><span style="text-align:right">P/L</span></div>';
    if (trades && trades.length > 0) {
        trades.forEach(t => {
            const dir = (t.type === 0 || t.type === 'buy' || t.type === 'BUY') ? 'buy' : 'sell';
            const profit = parseFloat(t.profit) || 0;
            html += '<div class="tbl-row">';
            html += '<span class="t-sym">' + (t.symbol || 'N/A') + '</span>';
            html += '<span class="t-type ' + dir + '">' + dir.toUpperCase() + '</span>';
            html += '<span class="t-lots">' + (parseFloat(t.volume) || 0).toFixed(2) + '</span>';
            html += '<span class="t-price">' + (t.price_open || t.price || 0) + '</span>';
            html += '<span class="t-pnl ' + (profit >= 0 ? 'pos' : 'neg') + '">' + (profit >= 0 ? '+' : '') + profit.toFixed(2) + '</span>';
            html += '</div>';
        });
    } else {
        html += '<div class="empty-msg">No open positions</div>';
    }
    html += '</div></div>';
    
    // Closed tab
    html += '<div class="tab-panel ' + (currentTab === 'closed' ? 'show' : '') + '" id="' + cardId + '_closed"><div class="trades-tbl">';
    html += '<div class="tbl-head"><span>Symbol</span><span>Type</span><span>Lots</span><span>Close Time</span><span style="text-align:right">P/L</span></div>';
    if (closedTrades && closedTrades.length > 0) {
        closedTrades.slice(0, 50).forEach(t => {
            const dir = (t.type === 0 || t.type === 'buy' || t.type === 'BUY') ? 'buy' : 'sell';
            const profit = parseFloat(t.profit) || 0;
            const closeTime = t.close_time || t.time_close || t.time || '';
            const timeStr = closeTime ? new Date(closeTime).toLocaleString() : '';
            html += '<div class="tbl-row">';
            html += '<span class="t-sym">' + (t.symbol || 'N/A') + '</span>';
            html += '<span class="t-type ' + dir + '">' + dir.toUpperCase() + '</span>';
            html += '<span class="t-lots">' + (parseFloat(t.volume) || 0).toFixed(2) + '</span>';
            html += '<span class="t-price" style="font-size:9px">' + timeStr + '</span>';
            html += '<span class="t-pnl ' + (profit >= 0 ? 'pos' : 'neg') + '">' + (profit >= 0 ? '+' : '') + profit.toFixed(2) + '</span>';
            html += '</div>';
        });
    } else {
        html += '<div class="empty-msg">No closed trades for selected period</div>';
    }
    html += '</div></div>';
    
    // Activity tab - FULL ACTIVITY LOG
    html += '<div class="tab-panel ' + (currentTab === 'activity' ? 'show' : '') + '" id="' + cardId + '_activity"><div class="activity-panel">';
    if (activities && activities.length > 0) {
        activities.slice(0, 100).forEach(act => {
            const a = parseActivity(act);
            const icons = { 
                TRADE: 'arrow-up', CLOSE: 'arrow-down', SIGNAL: 'bolt', 
                INFO: 'info-circle', ERROR: 'exclamation-triangle', 
                OPEN: 'arrow-up', COPY: 'copy', SYNC: 'sync', 
                DEBUG: 'bug', WARN: 'exclamation-circle' 
            };
            const icon = icons[a.type] || 'info-circle';
            const typeClass = a.type.toLowerCase();
            html += '<div class="activity-item">';
            html += '<span class="activity-time">' + a.time + '</span>';
            html += '<span class="activity-icon ' + typeClass + '"><i class="fas fa-' + icon + '"></i></span>';
            html += '<span class="activity-msg">' + a.message + '</span>';
            html += '</div>';
        });
    } else {
        html += '<div class="empty-msg">No activity logs available</div>';
    }
    html += '</div></div>';
    
    // Floating P/L footer
    html += '<div class="total-row"><span class="total-lbl">Floating P/L</span>';
    html += '<span class="total-val ' + pnlClass + '">' + (pnl >= 0 ? '+' : '') + pnl.toFixed(2) + '</span></div>';
    
    html += '</div>';
    return html;
}

function switchTab(cardId, tabName) {
    activeTab[cardId] = tabName;
    const card = document.getElementById('card_' + cardId);
    if (!card) return;
    card.querySelectorAll('.tab-btn').forEach((btn, i) => {
        const tabs = ['live', 'closed', 'activity'];
        btn.className = 'tab-btn' + (i === tabs.indexOf(tabName) ? ' active' : '');
    });
    card.querySelectorAll('.tab-panel').forEach(p => p.className = 'tab-panel');
    const panel = document.getElementById(cardId + '_' + tabName);
    if (panel) panel.className = 'tab-panel show';
}

function formatMoney(val) { 
    return (parseFloat(val) || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); 
}

function updateStats() {
    const masterPositions = tradeData.master?.positions || [];
    const totalPnl = masterPositions.reduce((s, t) => s + (parseFloat(t.profit) || 0), 0);
    const copiedEl = document.getElementById('totalCopied');
    if (copiedEl) copiedEl.textContent = globalStats.total || 0;
    const profitEl = document.getElementById('totalProfit');
    if (profitEl) {
        profitEl.textContent = (totalPnl >= 0 ? '+' : '') + totalPnl.toFixed(2);
        profitEl.className = 'overview-value ' + (totalPnl >= 0 ? 'green' : 'red');
    }
    const ps = document.getElementById('profitStatus');
    if (ps) {
        ps.textContent = totalPnl > 0 ? 'Profit' : totalPnl < 0 ? 'Loss' : 'Neutral';
        ps.className = 'overview-badge ' + (totalPnl > 0 ? 'active' : totalPnl < 0 ? 'inactive' : 'neutral');
    }
}

async function startCopier() {
    document.getElementById('btnStart').disabled = true;
    try { 
        await fetch('/api/pairs/' + selectedPairId + '/start', { method: 'POST' }); 
        setTimeout(loadData, 500); 
    } catch(e) { 
        document.getElementById('btnStart').disabled = false; 
    }
}

async function stopCopier() {
    document.getElementById('btnStop').disabled = true;
    try { 
        await fetch('/api/pairs/' + selectedPairId + '/stop', { method: 'POST' }); 
        setTimeout(loadData, 500); 
    } catch(e) { 
        document.getElementById('btnStop').disabled = false; 
    }
}

// Initialize
loadPairs();

// Auto-refresh every 5 seconds
setInterval(() => {
    if (document.activeElement && document.activeElement.type === 'date') return;
    loadData();
}, 5000);
</script>
{% endblock %}"""

new_content = content[:script_start] + new_script
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Dashboard v4.0 - COMPLETE FIX!')
print('- Individual date filters per card with custom date inputs')
print('- All children accounts shown')
print('- Full activity log display')
print('- Proper P/L comparison')
