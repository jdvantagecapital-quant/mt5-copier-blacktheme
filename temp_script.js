
let allPairs = [], selectedPairId = null, selectedPair = null, processStatus = {};
let globalStats = { total: 0, success: 0, failed: 0 }, isRunning = false;
let tradeData = { master: { balance: 0, equity: 0, positions: [], closed_trades: [] }, children: {}, child_data: {}, activities: {}, closed_master: [], closed_children: {} };
let activeTab = {};
let cardFilters = {};  // Independent filter for each card
let pnlFilter = { type: 'today' };  // Global P/L filter
let pnlData = { master: { positions: [] }, children: {}, closed_master: [], closed_children: {} };

function formatDate(d) { return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0'); }

function getCardDateParams(cardId) {
    const filter = cardFilters[cardId] || { type: '30days' };
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

function getPnlDateParams() {
    const today = new Date(); today.setHours(0,0,0,0);
    let from, to;
    switch(pnlFilter.type) {
        case 'today': from = to = formatDate(today); break;
        case '7days': const s7 = new Date(today); s7.setDate(s7.getDate()-7); from = formatDate(s7); to = formatDate(today); break;
        case '30days': const s30 = new Date(today); s30.setDate(s30.getDate()-30); from = formatDate(s30); to = formatDate(today); break;
        case 'custom': from = pnlFilter.from; to = pnlFilter.to; break;
        default: from = to = formatDate(today);
    }
    return { date_from: from, date_to: to };
}

async function loadPairs() {
    console.log('loadPairs called');
    try { 
        const res = await fetch('/api/pairs'); 
        console.log('API response:', res.status);
        allPairs = await res.json(); 
        console.log('Pairs loaded:', allPairs.length, allPairs);
    } catch(e) { 
        console.error('loadPairs error:', e);
        allPairs = []; 
    }
    const select = document.getElementById('pairSelect');
    updateOverviewStats();
    if (!allPairs.length) {
        console.log('No pairs found, showing empty state');
        select.innerHTML = '<option value="">No pairs configured</option>';
        document.getElementById('accountsContainer').innerHTML = '<div class="no-pairs" style="grid-column:1/-1"><i class="fas fa-plug"></i><h3>No Copy Pairs</h3><p>Configure pairs to start</p><a href="/accounts"><i class="fas fa-plus"></i> Add Pair</a></div>';
        return;
    }
    console.log('Populating dropdown with', allPairs.length, 'pairs');
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
    // Reset card filters - each card gets its own filter
    cardFilters = {};
    if (selectedPair) {
        cardFilters['master'] = { type: '30days' };
        (selectedPair.children||[]).forEach((c,i) => cardFilters['child_'+i] = { type: '30days' });
    }
    loadData();
}

async function loadDataForCard(cardId, isChild, childId) {
    // Get card-specific date params
    const params = getCardDateParams(cardId);
    const url = '/api/pairs/' + selectedPairId + '/mt5-data?date_from=' + params.date_from + '&date_to=' + params.date_to + '&card=' + cardId + (isChild ? '&child_id=' + childId : '');
    
    try {
        const res = await fetch(url);
        return await res.json();
    } catch(e) {
        return null;
    }
}

async function loadData() {
    if (!selectedPairId || !selectedPair) return;
    try { const res = await fetch('/api/process-status'); processStatus = (await res.json()).status || {}; } catch(e) { processStatus = {}; }
    const pairStatus = processStatus[selectedPairId];
    isRunning = pairStatus && pairStatus.master_running;
    updateStatusUI();

    // Load master data with master's own filter
    const masterParams = getCardDateParams('master');
    let masterUrl = '/api/pairs/' + selectedPairId + '/mt5-data?date_from=' + masterParams.date_from + '&date_to=' + masterParams.date_to + '&days=30';
    
    try {
        const res = await fetch(masterUrl);
        const data = await res.json();
        if (data.success) {
            tradeData = {
                master: data.master || { balance: 0, equity: 0, positions: [], closed_trades: [] },
                children: {},
                child_data: {},
                activities: data.activities || {},
                closed_master: data.closed_master || [],
                closed_children: data.closed_children || {}
            };
            tradeData.balance = data.master?.balance || data.balance || 0;
            tradeData.equity = data.master?.equity || data.equity || 0;
            
            // Map children data
            (selectedPair.children||[]).forEach((child, i) => {
                const cid = child.id;
                const childData = data.children?.[cid] || {};
                tradeData.children[cid] = childData.positions || data.children?.[cid] || [];
                tradeData.child_data[cid] = { 
                    balance: childData.balance || data.child_data?.[cid]?.balance || 0, 
                    equity: childData.equity || data.child_data?.[cid]?.equity || 0 
                };
            });
        }
    } catch(e) {
        console.error('Load data error:', e);
        tradeData = { master: { balance: 0, equity: 0, positions: [] }, children: {}, child_data: {}, activities: {}, closed_master: [], closed_children: {}, balance: 0, equity: 0 };
    }
    
    // Load each child with its own filter
    for (let i = 0; i < (selectedPair.children||[]).length; i++) {
        const child = selectedPair.children[i];
        const cardId = 'child_' + i;
        const childParams = getCardDateParams(cardId);
        
        try {
            const childUrl = '/api/pairs/' + selectedPairId + '/mt5-data?date_from=' + childParams.date_from + '&date_to=' + childParams.date_to + '&child_id=' + child.id;
            const res = await fetch(childUrl);
            const childData = await res.json();
            if (childData.success && childData.children?.[child.id]) {
                tradeData.closed_children[child.id] = childData.closed_children?.[child.id] || [];
            }
        } catch(e) {}
    }
    
    try { const res3 = await fetch('/api/status'); globalStats = (await res3.json()).stats || { total: 0, success: 0, failed: 0 }; } catch(e) { globalStats = { total: 0, success: 0, failed: 0 }; }
    
    renderAccounts();
    loadPnlData();  // This will call renderPnlSection after loading P/L data
    updateStats();
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

function setCardFilter(cardId, type) {
    cardFilters[cardId] = { type: type };
    loadData();
}

function applyCardCustomDate(cardId) {
    const from = document.getElementById('date_from_'+cardId)?.value;
    const to = document.getElementById('date_to_'+cardId)?.value;
    if (from && to) {
        cardFilters[cardId] = { type: 'custom', from: from, to: to };
        loadData();
    }
}

function setPnlFilter(type) {
    pnlFilter = { type: type };
    document.querySelectorAll('.pnl-filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    loadPnlData();  // Changed from loadData()
}

function applyPnlCustomDate() {
    const from = document.getElementById('pnl_from')?.value;
    const to = document.getElementById('pnl_to')?.value;
    if (from && to) {
        pnlFilter = { type: 'custom', from: from, to: to };
        document.querySelectorAll('.pnl-filter-btn').forEach(b => b.classList.remove('active'));
        loadPnlData();  // Changed from loadData()
    }
}

async function loadPnlData() {
    if (!selectedPairId || !selectedPair) return;
    
    const params = getPnlDateParams();
    const url = '/api/pairs/' + selectedPairId + '/mt5-data?date_from=' + params.date_from + '&date_to=' + params.date_to;
    
    try {
        const res = await fetch(url);
        const data = await res.json();
        if (data.success) {
            pnlData = {
                master: data.master || { positions: [] },
                children: {},
                closed_master: data.closed_master || [],
                closed_children: data.closed_children || {}
            };
            
            (selectedPair.children||[]).forEach((child) => {
                const cid = child.id;
                pnlData.children[cid] = data.children?.[cid]?.positions || data.children?.[cid] || [];
            });
        }
    } catch(e) {
        console.error('Load P/L data error:', e);
        pnlData = { master: { positions: [] }, children: {}, closed_master: [], closed_children: {} };
    }
    
    renderPnlSection();
}

function renderPnlSection() {
    if (!selectedPair) { document.getElementById('pnlGrid').innerHTML = ''; return; }
    
    const masterPositions = pnlData.master?.positions || [];
    const masterPnl = masterPositions.reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
    const closedMasterPnl = (pnlData.closed_master || []).reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
    const totalMasterPnl = masterPnl + closedMasterPnl;
    
    let html = '';
    
    // Master P/L Card
    html += '<div class="pnl-card master">';
    html += '<div class="pnl-card-header"><span class="pnl-account">' + selectedPair.master_account + '</span><span class="pnl-badge master">MASTER</span></div>';
    html += '<div class="pnl-value ' + (totalMasterPnl >= 0 ? 'pos' : 'neg') + '">' + (totalMasterPnl >= 0 ? '+' : '') + totalMasterPnl.toFixed(2) + '</div>';
    html += '<div class="pnl-label">Total P/L (Floating + Closed)</div>';
    html += '<div class="pnl-diff-row"><span class="pnl-diff-label">Floating</span><span class="pnl-diff-val ' + (masterPnl >= 0 ? 'pos' : 'neg') + '">' + (masterPnl >= 0 ? '+' : '') + masterPnl.toFixed(2) + '</span></div>';
    html += '<div class="pnl-diff-row"><span class="pnl-diff-label">Closed</span><span class="pnl-diff-val ' + (closedMasterPnl >= 0 ? 'pos' : 'neg') + '">' + (closedMasterPnl >= 0 ? '+' : '') + closedMasterPnl.toFixed(2) + '</span></div>';
    html += '</div>';
    
    // Children P/L Cards with difference
    (selectedPair.children||[]).forEach((child, i) => {
        const cid = child.id;
        const childPositions = Array.isArray(pnlData.children?.[cid]) ? pnlData.children[cid] : [];
        const childPnl = childPositions.reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
        const closedChildPnl = (pnlData.closed_children?.[cid] || []).reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
        const totalChildPnl = childPnl + closedChildPnl;
        const diff = totalChildPnl - totalMasterPnl;
        
        html += '<div class="pnl-card child">';
        html += '<div class="pnl-card-header"><span class="pnl-account">' + child.account + '</span><span class="pnl-badge child">CHILD ' + (i+1) + '</span></div>';
        html += '<div class="pnl-value ' + (totalChildPnl >= 0 ? 'pos' : 'neg') + '">' + (totalChildPnl >= 0 ? '+' : '') + totalChildPnl.toFixed(2) + '</div>';
        html += '<div class="pnl-label">Total P/L</div>';
        html += '<div class="pnl-diff-row"><span class="pnl-diff-label">Floating</span><span class="pnl-diff-val ' + (childPnl >= 0 ? 'pos' : 'neg') + '">' + (childPnl >= 0 ? '+' : '') + childPnl.toFixed(2) + '</span></div>';
        html += '<div class="pnl-diff-row"><span class="pnl-diff-label">Closed</span><span class="pnl-diff-val ' + (closedChildPnl >= 0 ? 'pos' : 'neg') + '">' + (closedChildPnl >= 0 ? '+' : '') + closedChildPnl.toFixed(2) + '</span></div>';
        html += '<div class="pnl-diff-row" style="background: rgba(255,68,102,0.05); margin: 6px -14px -14px; padding: 8px 14px; border-radius: 0 0 5px 5px;"><span class="pnl-diff-label" style="color: #ff4466;">vs Master</span><span class="pnl-diff-val ' + (diff >= 0 ? 'pos' : 'neg') + '">' + (diff >= 0 ? '+' : '') + diff.toFixed(2) + '</span></div>';
        html += '</div>';
    });
    
    document.getElementById('pnlGrid').innerHTML = html;
}

function parseActivity(activity) {
    if (typeof activity === 'string') {
        const parts = activity.split('|').map(p => p.trim());
        if (parts.length >= 3) return { time: parts[0].split(' ')[1] || parts[0], type: parts[1] || 'INFO', message: parts.slice(2).join(' | ') };
        return { time: '', type: 'INFO', message: activity };
    }
    return { time: activity.time || '', type: activity.type || 'INFO', message: activity.message || activity.msg || '' };
}

function renderAccounts() {
    const container = document.getElementById('accountsContainer');
    if (!selectedPair) { container.innerHTML = ''; return; }
    
    const children = selectedPair.children || [];
    const masterPositions = tradeData.master?.positions || (Array.isArray(tradeData.master) ? tradeData.master : []);
    const masterPnl = masterPositions.reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
    const masterActivities = Array.isArray(tradeData.activities?.master) ? tradeData.activities.master : [];
    const closedMaster = tradeData.closed_master || tradeData.master?.closed_trades || [];
    const masterError = tradeData.master?.error;
    
    let html = buildCard('master', 'master', selectedPair.master_account, 
        tradeData.balance || tradeData.master?.balance || 0, 
        tradeData.equity || tradeData.master?.equity || 0, 
        masterPositions, masterPnl, isRunning, masterActivities, closedMaster, masterError);
    
    if (children.length > 0) {
        children.forEach((child, i) => {
            const cid = child.id;
            const cardId = 'child_' + i;
            const childPositions = Array.isArray(tradeData.children?.[cid]) ? tradeData.children[cid] : [];
            const childInfo = tradeData.child_data?.[cid] || {};
            const childPnl = childPositions.reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
            const childActivities = Array.isArray(tradeData.activities?.[cid]) ? tradeData.activities[cid] : [];
            const closedChild = Array.isArray(tradeData.closed_children?.[cid]) ? tradeData.closed_children[cid] : [];
            const childConnected = isRunning && child.enabled;
            const childError = childInfo.error;
            html += buildCard(cardId, 'child', child.account, childInfo.balance||0, childInfo.equity||0, childPositions, childPnl, childConnected, childActivities, closedChild, childError);
        });
    } else {
        html += '<div class="acc-card child"><div class="empty-msg">No child accounts configured</div></div>';
    }
    container.innerHTML = html;
    for (const cardId in activeTab) switchTab(cardId, activeTab[cardId]);
}

function buildCard(cardId, type, account, balance, equity, trades, pnl, connected, activities, closedTrades, error) {
    const pnlClass = pnl >= 0 ? 'pos' : 'neg';
    const currentTab = activeTab[cardId] || 'live';
    const currentFilter = cardFilters[cardId]?.type || '30days';
    
    let html = '<div class="acc-card '+type+'" id="card_'+cardId+'">';
    html += '<div class="acc-header"><div class="acc-info"><span class="acc-badge '+type+'">'+type.toUpperCase()+'</span><span class="acc-num">'+account+'</span></div>';
    html += '<div class="acc-status '+(connected?'on':'off')+'"><i class="fas fa-circle"></i> '+(connected?'On':'Off')+'</div></div>';
    
    if (error) html += '<div class="error-msg"><i class="fas fa-exclamation-triangle"></i> '+error+'</div>';
    
    html += '<div class="bal-row"><div><div class="bal-label">Balance</div><div class="bal-value">$'+formatMoney(balance)+'</div></div>';
    html += '<div><div class="bal-label">Equity</div><div class="bal-value">$'+formatMoney(equity)+'</div></div></div>';
    
    html += '<div class="card-filter">';
    html += '<span class="card-filter-label"><i class="fas fa-calendar-alt"></i></span>';
    ['today','yesterday','7days','30days'].forEach(f => {
        const label = f === 'today' ? 'Today' : f === 'yesterday' ? 'Yest' : f === '7days' ? '7D' : '30D';
        html += '<button class="card-filter-btn '+(currentFilter===f?'active':'')+'" onclick="setCardFilter(\''+cardId+'\',\''+f+'\')">'+label+'</button>';
    });
    html += '<input type="date" class="card-date-input" id="date_from_'+cardId+'" style="margin-left:4px">';
    html += '<input type="date" class="card-date-input" id="date_to_'+cardId+'">';
    html += '<button class="card-filter-btn" onclick="applyCardCustomDate(\''+cardId+'\')"><i class="fas fa-check"></i></button>';
    html += '</div>';
    
    html += '<div class="acc-tabs">';
    html += '<button class="tab-btn '+(currentTab==='live'?'active':'')+'" onclick="switchTab(\''+cardId+'\',\'live\')">Live ('+trades.length+')</button>';
    html += '<button class="tab-btn '+(currentTab==='closed'?'active':'')+'" onclick="switchTab(\''+cardId+'\',\'closed\')">Closed ('+(closedTrades?.length||0)+')</button>';
    html += '<button class="tab-btn '+(currentTab==='activity'?'active':'')+'" onclick="switchTab(\''+cardId+'\',\'activity\')">Activity</button></div>';
    
    // Live tab
    html += '<div class="tab-panel '+(currentTab==='live'?'show':'')+'" id="'+cardId+'_live"><div class="trades-tbl">';
    html += '<div class="tbl-head"><span>Symbol</span><span>Type</span><span>Lots</span><span>Price</span><span style="text-align:right">P/L</span></div>';
    if (trades && trades.length > 0) {
        trades.forEach(t => {
            const dir = (t.type===0||t.type==='buy'||t.type==='BUY')?'buy':'sell';
            const profit = parseFloat(t.profit)||0;
            html += '<div class="tbl-row"><span class="t-sym">'+(t.symbol||'N/A')+'</span><span class="t-type '+dir+'">'+dir.toUpperCase()+'</span>';
            html += '<span class="t-lots">'+(parseFloat(t.volume)||0).toFixed(2)+'</span><span class="t-price">'+(t.price_open||t.price||0)+'</span>';
            html += '<span class="t-pnl '+(profit>=0?'pos':'neg')+'">'+(profit>=0?'+':'')+profit.toFixed(2)+'</span></div>';
        });
    } else { html += '<div class="empty-msg">No open positions</div>'; }
    html += '</div></div>';
    
    // Closed tab
    html += '<div class="tab-panel '+(currentTab==='closed'?'show':'')+'" id="'+cardId+'_closed"><div class="trades-tbl">';
    html += '<div class="tbl-head"><span>Symbol</span><span>Type</span><span>Lots</span><span>Close</span><span style="text-align:right">P/L</span></div>';
    if (closedTrades && closedTrades.length > 0) {
        closedTrades.forEach(t => {
            const dir = (t.type===0||t.type==='buy'||t.type==='BUY')?'buy':'sell';
            const profit = parseFloat(t.profit)||0;
            html += '<div class="tbl-row"><span class="t-sym">'+(t.symbol||'N/A')+'</span><span class="t-type '+dir+'">'+dir.toUpperCase()+'</span>';
            html += '<span class="t-lots">'+(parseFloat(t.volume)||0).toFixed(2)+'</span><span class="t-price">'+(t.close_price||t.price||0)+'</span>';
            html += '<span class="t-pnl '+(profit>=0?'pos':'neg')+'">'+(profit>=0?'+':'')+profit.toFixed(2)+'</span></div>';
        });
    } else { html += '<div class="empty-msg">No closed trades for selected period</div>'; }
    html += '</div></div>';
    
    // Activity tab
    html += '<div class="tab-panel '+(currentTab==='activity'?'show':'')+'" id="'+cardId+'_activity"><div class="activity-panel">';
    if (activities && activities.length > 0) {
        activities.slice(0,25).map(parseActivity).forEach(a => {
            const icons = { TRADE:'arrow-up', CLOSE:'arrow-down', SIGNAL:'bolt', INFO:'info-circle', ERROR:'exclamation-triangle', OPEN:'arrow-up' };
            html += '<div class="activity-item"><span class="activity-time">'+a.time+'</span>';
            html += '<span class="activity-icon '+a.type+'"><i class="fas fa-'+(icons[a.type]||'info-circle')+'"></i></span>';
            html += '<span class="activity-msg">'+a.message+'</span></div>';
        });
    } else { html += '<div class="empty-msg">No recent activity</div>'; }
    html += '</div></div>';
    
    html += '<div class="total-row"><span class="total-lbl">Floating P/L</span><span class="total-val '+pnlClass+'">'+(pnl>=0?'+':'')+pnl.toFixed(2)+'</span></div></div>';
    return html;
}

function switchTab(cardId, tabName) {
    activeTab[cardId] = tabName;
    const card = document.getElementById('card_'+cardId);
    if (!card) return;
    const tabs = ['live','closed','activity'];
    card.querySelectorAll('.tab-btn').forEach((btn,i) => btn.className = 'tab-btn'+(i===tabs.indexOf(tabName)?' active':''));
    card.querySelectorAll('.tab-panel').forEach(p => p.className = 'tab-panel');
    const panel = document.getElementById(cardId+'_'+tabName);
    if (panel) panel.className = 'tab-panel show';
}

function formatMoney(val) { return (parseFloat(val)||0).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}); }

function updateStats() {
    const masterPositions = tradeData.master?.positions || (Array.isArray(tradeData.master) ? tradeData.master : []);
    const totalPnl = masterPositions.reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
    document.getElementById('totalCopied').textContent = globalStats.total || 0;
    const profitEl = document.getElementById('totalProfit');
    profitEl.textContent = (totalPnl>=0?'+':'')+totalPnl.toFixed(2);
    profitEl.className = 'overview-value '+(totalPnl>=0?'green':'red');
    const ps = document.getElementById('profitStatus');
    ps.textContent = totalPnl > 0 ? 'Profit' : totalPnl < 0 ? 'Loss' : 'Neutral';
    ps.className = 'overview-badge '+(totalPnl > 0 ? 'active' : totalPnl < 0 ? 'inactive' : 'neutral');
}

async function startCopier() {
    document.getElementById('btnStart').disabled = true;
    try { await fetch('/api/pairs/'+selectedPairId+'/start', {method:'POST'}); setTimeout(loadData, 300); } catch(e) { document.getElementById('btnStart').disabled = false; }
}

async function stopCopier() {
    document.getElementById('btnStop').disabled = true;
    try { await fetch('/api/pairs/'+selectedPairId+'/stop', {method:'POST'}); setTimeout(loadData, 300); } catch(e) { document.getElementById('btnStop').disabled = false; }
}

loadPairs();
setInterval(loadData, 800);
