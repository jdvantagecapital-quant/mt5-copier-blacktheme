import re

file_path = r'C:\Users\MI\MT5-Copier-new\Templates\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

script_start = content.find('{% block extra_js %}')
if script_start == -1:
    print('Could not find script block')
    exit(1)

new_script = r"""{% block extra_js %}
<script>
// DASHBOARD v3.0 - SUPER FAST
let allPairs = [], selectedPairId = null, selectedPair = null, processStatus = {};
let globalStats = { total: 0, success: 0, failed: 0 }, isRunning = false;
let tradeData = { master: { balance: 0, equity: 0, positions: [] }, children: {}, child_data: {}, activities: {}, closed_master: [], closed_children: {} };
let activeTab = {};
let dateFilter = { type: '30days' };
let isLoading = false;

function formatDate(d) { 
    return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0'); 
}

function getDateParams() {
    const today = new Date(); today.setHours(0,0,0,0);
    let from, to;
    switch(dateFilter.type) {
        case 'today': from = to = formatDate(today); break;
        case 'yesterday': const y = new Date(today); y.setDate(y.getDate()-1); from = to = formatDate(y); break;
        case '7days': const s7 = new Date(today); s7.setDate(s7.getDate()-7); from = formatDate(s7); to = formatDate(today); break;
        case '30days': const s30 = new Date(today); s30.setDate(s30.getDate()-30); from = formatDate(s30); to = formatDate(today); break;
        case 'custom': from = dateFilter.from || formatDate(today); to = dateFilter.to || formatDate(today); break;
        default: const def = new Date(today); def.setDate(def.getDate()-30); from = formatDate(def); to = formatDate(today);
    }
    return { date_from: from, date_to: to };
}

function setDateFilter(type, btn) {
    dateFilter = { type: type };
    document.querySelectorAll('.pnl-filter-btn, .card-filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    document.querySelectorAll('[data-filter="' + type + '"]').forEach(b => b.classList.add('active'));
    loadData();
}

function applyCustomDate() {
    const from = document.getElementById('pnl_from')?.value;
    const to = document.getElementById('pnl_to')?.value;
    if (from && to) {
        dateFilter = { type: 'custom', from: from, to: to };
        document.querySelectorAll('.pnl-filter-btn, .card-filter-btn').forEach(b => b.classList.remove('active'));
        loadData();
    }
}

function setPnlFilter(type, btn) { setDateFilter(type, btn); }
function setCardFilter(cardId, type) { setDateFilter(type, null); }
function applyPnlCustomDate() { applyCustomDate(); }
function applyCardCustomDate(cardId) { applyCustomDate(); }

async function loadPairs() {
    try { const res = await fetch('/api/pairs'); allPairs = await res.json(); } catch(e) { allPairs = []; }
    const select = document.getElementById('pairSelect');
    updateOverviewStats();
    if (!allPairs.length) {
        select.innerHTML = '<option value="">No pairs configured</option>';
        document.getElementById('accountsContainer').innerHTML = '<div class="no-pairs" style="grid-column:1/-1"><i class="fas fa-plug"></i><h3>No Copy Pairs</h3><p>Configure pairs to start</p><a href="/accounts"><i class="fas fa-plus"></i> Add Pair</a></div>';
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
    loadData();
}

async function loadData() {
    if (!selectedPairId || !selectedPair) return;
    if (isLoading) return;
    isLoading = true;
    try {
        try { const res = await fetch('/api/process-status'); processStatus = (await res.json()).status || {}; } catch(e) { processStatus = {}; }
        const pairStatus = processStatus[selectedPairId];
        isRunning = pairStatus && pairStatus.master_running;
        updateStatusUI();

        const params = getDateParams();
        const url = '/api/pairs/' + selectedPairId + '/mt5-data?date_from=' + params.date_from + '&date_to=' + params.date_to;
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

        try { const res3 = await fetch('/api/status'); globalStats = (await res3.json()).stats || { total: 0, success: 0, failed: 0 }; } catch(e) { globalStats = { total: 0, success: 0, failed: 0 }; }
        renderAccounts();
        renderPnlSection();
        updateStats();
    } catch(e) { console.error('Load data error:', e); }
    finally { isLoading = false; }
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
    const masterPositions = tradeData.master?.positions || [];
    const masterPnl = masterPositions.reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
    const closedMasterPnl = (tradeData.closed_master || []).reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
    const totalMasterPnl = masterPnl + closedMasterPnl;
    let html = '<div class="pnl-card master"><div class="pnl-card-header"><span class="pnl-account">' + selectedPair.master_account + '</span><span class="pnl-badge master">MASTER</span></div><div class="pnl-value ' + (totalMasterPnl >= 0 ? 'pos' : 'neg') + '">' + (totalMasterPnl >= 0 ? '+' : '') + totalMasterPnl.toFixed(2) + '</div><div class="pnl-label">Total P/L</div><div class="pnl-diff-row"><span class="pnl-diff-label">Floating</span><span class="pnl-diff-val ' + (masterPnl >= 0 ? 'pos' : 'neg') + '">' + (masterPnl >= 0 ? '+' : '') + masterPnl.toFixed(2) + '</span></div><div class="pnl-diff-row"><span class="pnl-diff-label">Closed</span><span class="pnl-diff-val ' + (closedMasterPnl >= 0 ? 'pos' : 'neg') + '">' + (closedMasterPnl >= 0 ? '+' : '') + closedMasterPnl.toFixed(2) + '</span></div></div>';
    (selectedPair.children||[]).forEach((child, i) => {
        const cid = child.id;
        const childData = tradeData.children?.[cid];
        const childPositions = Array.isArray(childData?.positions) ? childData.positions : (Array.isArray(childData) ? childData : []);
        const childPnl = childPositions.reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
        const closedChildPnl = (tradeData.closed_children?.[cid] || []).reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
        const totalChildPnl = childPnl + closedChildPnl;
        const diff = totalChildPnl - totalMasterPnl;
        html += '<div class="pnl-card child"><div class="pnl-card-header"><span class="pnl-account">' + child.account + '</span><span class="pnl-badge child">CHILD ' + (i+1) + '</span></div><div class="pnl-value ' + (totalChildPnl >= 0 ? 'pos' : 'neg') + '">' + (totalChildPnl >= 0 ? '+' : '') + totalChildPnl.toFixed(2) + '</div><div class="pnl-label">Total P/L</div><div class="pnl-diff-row"><span class="pnl-diff-label">Floating</span><span class="pnl-diff-val ' + (childPnl >= 0 ? 'pos' : 'neg') + '">' + (childPnl >= 0 ? '+' : '') + childPnl.toFixed(2) + '</span></div><div class="pnl-diff-row"><span class="pnl-diff-label">Closed</span><span class="pnl-diff-val ' + (closedChildPnl >= 0 ? 'pos' : 'neg') + '">' + (closedChildPnl >= 0 ? '+' : '') + closedChildPnl.toFixed(2) + '</span></div><div class="pnl-diff-row" style="background:rgba(255,68,102,0.05);margin:6px -14px -14px;padding:8px 14px;border-radius:0 0 5px 5px"><span class="pnl-diff-label" style="color:#ff4466">vs Master</span><span class="pnl-diff-val ' + (diff >= 0 ? 'pos' : 'neg') + '">' + (diff >= 0 ? '+' : '') + diff.toFixed(2) + '</span></div></div>';
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
    let html = buildCard('master', 'master', selectedPair.master_account, tradeData.balance || tradeData.master?.balance || 0, tradeData.equity || tradeData.master?.equity || 0, masterPositions, masterPnl, isRunning, masterActivities, closedMaster, masterError);
    if (children.length > 0) {
        children.forEach((child, i) => {
            const cid = child.id;
            const cardId = 'child_' + i;
            const childData = tradeData.children?.[cid];
            const childPositions = Array.isArray(childData?.positions) ? childData.positions : (Array.isArray(childData) ? childData : []);
            const childInfo = tradeData.child_data?.[cid] || childData || {};
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
    const scrollPositions = {};
    container.querySelectorAll('.trades-tbl, .activity-panel').forEach(el => {
        const id = el.closest('.acc-card')?.id + '_' + (el.classList.contains('trades-tbl') ? 'trades' : 'activity');
        if (el.scrollTop > 0) scrollPositions[id] = el.scrollTop;
    });
    container.innerHTML = html;
    for (const cardId in activeTab) switchTab(cardId, activeTab[cardId]);
    container.querySelectorAll('.trades-tbl, .activity-panel').forEach(el => {
        const id = el.closest('.acc-card')?.id + '_' + (el.classList.contains('trades-tbl') ? 'trades' : 'activity');
        if (scrollPositions[id]) el.scrollTop = scrollPositions[id];
    });
}

function buildCard(cardId, type, account, balance, equity, trades, pnl, connected, activities, closedTrades, error) {
    const pnlClass = pnl >= 0 ? 'pos' : 'neg';
    const currentTab = activeTab[cardId] || 'live';
    const currentFilter = dateFilter.type;
    let html = '<div class="acc-card '+type+'" id="card_'+cardId+'"><div class="acc-header"><div class="acc-info"><span class="acc-badge '+type+'">'+type.toUpperCase()+'</span><span class="acc-num">'+account+'</span></div><div class="acc-status '+(connected?'on':'off')+'"><i class="fas fa-circle"></i> '+(connected?'On':'Off')+'</div></div>';
    if (error) html += '<div class="error-msg"><i class="fas fa-exclamation-triangle"></i> '+error+'</div>';
    html += '<div class="bal-row"><div><div class="bal-label">Balance</div><div class="bal-value">$'+formatMoney(balance)+'</div></div><div><div class="bal-label">Equity</div><div class="bal-value">$'+formatMoney(equity)+'</div></div></div>';
    html += '<div class="card-filter"><span class="card-filter-label"><i class="fas fa-calendar-alt"></i></span>';
    ['today','yesterday','7days','30days'].forEach(f => {
        const label = f === 'today' ? 'Today' : f === 'yesterday' ? 'Yest' : f === '7days' ? '7D' : '30D';
        html += '<button class="card-filter-btn '+(currentFilter===f?'active':'')+'" data-filter="'+f+'" onclick="setDateFilter(\''+f+'\', this)">'+label+'</button>';
    });
    html += '<input type="date" class="card-date-input" id="date_from_'+cardId+'" style="margin-left:4px"><input type="date" class="card-date-input" id="date_to_'+cardId+'"><button class="card-filter-btn" onclick="applyCustomDate()"><i class="fas fa-check"></i></button></div>';
    html += '<div class="acc-tabs"><button class="tab-btn '+(currentTab==='live'?'active':'')+'" onclick="switchTab(\''+cardId+'\',\'live\')">Live ('+trades.length+')</button><button class="tab-btn '+(currentTab==='closed'?'active':'')+'" onclick="switchTab(\''+cardId+'\',\'closed\')">Closed ('+(closedTrades?.length||0)+')</button><button class="tab-btn '+(currentTab==='activity'?'active':'')+'" onclick="switchTab(\''+cardId+'\',\'activity\')">Activity</button></div>';
    html += '<div class="tab-panel '+(currentTab==='live'?'show':'')+'" id="'+cardId+'_live"><div class="trades-tbl"><div class="tbl-head"><span>Symbol</span><span>Type</span><span>Lots</span><span>Price</span><span style="text-align:right">P/L</span></div>';
    if (trades && trades.length > 0) {
        trades.forEach(t => {
            const dir = (t.type===0||t.type==='buy'||t.type==='BUY')?'buy':'sell';
            const profit = parseFloat(t.profit)||0;
            html += '<div class="tbl-row"><span class="t-sym">'+(t.symbol||'N/A')+'</span><span class="t-type '+dir+'">'+dir.toUpperCase()+'</span><span class="t-lots">'+(parseFloat(t.volume)||0).toFixed(2)+'</span><span class="t-price">'+(t.price_open||t.price||0)+'</span><span class="t-pnl '+(profit>=0?'pos':'neg')+'">'+(profit>=0?'+':'')+profit.toFixed(2)+'</span></div>';
        });
    } else { html += '<div class="empty-msg">No open positions</div>'; }
    html += '</div></div>';
    html += '<div class="tab-panel '+(currentTab==='closed'?'show':'')+'" id="'+cardId+'_closed"><div class="trades-tbl"><div class="tbl-head"><span>Symbol</span><span>Type</span><span>Lots</span><span>Close</span><span style="text-align:right">P/L</span></div>';
    if (closedTrades && closedTrades.length > 0) {
        closedTrades.forEach(t => {
            const dir = (t.type===0||t.type==='buy'||t.type==='BUY')?'buy':'sell';
            const profit = parseFloat(t.profit)||0;
            html += '<div class="tbl-row"><span class="t-sym">'+(t.symbol||'N/A')+'</span><span class="t-type '+dir+'">'+dir.toUpperCase()+'</span><span class="t-lots">'+(parseFloat(t.volume)||0).toFixed(2)+'</span><span class="t-price">'+(t.close_price||t.price||0)+'</span><span class="t-pnl '+(profit>=0?'pos':'neg')+'">'+(profit>=0?'+':'')+profit.toFixed(2)+'</span></div>';
        });
    } else { html += '<div class="empty-msg">No closed trades for selected period</div>'; }
    html += '</div></div>';
    html += '<div class="tab-panel '+(currentTab==='activity'?'show':'')+'" id="'+cardId+'_activity"><div class="activity-panel">';
    if (activities && activities.length > 0) {
        activities.slice(0,25).map(parseActivity).forEach(a => {
            const icons = { TRADE:'arrow-up', CLOSE:'arrow-down', SIGNAL:'bolt', INFO:'info-circle', ERROR:'exclamation-triangle', OPEN:'arrow-up' };
            html += '<div class="activity-item"><span class="activity-time">'+a.time+'</span><span class="activity-icon '+a.type+'"><i class="fas fa-'+(icons[a.type]||'info-circle')+'"></i></span><span class="activity-msg">'+a.message+'</span></div>';
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
    const masterPositions = tradeData.master?.positions || [];
    const totalPnl = masterPositions.reduce((s,t) => s + (parseFloat(t.profit)||0), 0);
    const copiedEl = document.getElementById('totalCopied');
    if (copiedEl) copiedEl.textContent = globalStats.total || 0;
    const profitEl = document.getElementById('totalProfit');
    if (profitEl) { profitEl.textContent = (totalPnl>=0?'+':'')+totalPnl.toFixed(2); profitEl.className = 'overview-value '+(totalPnl>=0?'green':'red'); }
    const ps = document.getElementById('profitStatus');
    if (ps) { ps.textContent = totalPnl > 0 ? 'Profit' : totalPnl < 0 ? 'Loss' : 'Neutral'; ps.className = 'overview-badge '+(totalPnl > 0 ? 'active' : totalPnl < 0 ? 'inactive' : 'neutral'); }
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
setInterval(() => { if (document.activeElement && document.activeElement.type === 'date') return; loadData(); }, 5000);
</script>
{% endblock %}"""

new_content = content[:script_start] + new_script
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Dashboard v3.0 SUPER FAST - JavaScript rewritten!')
