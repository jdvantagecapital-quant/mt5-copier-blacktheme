with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Update the closed trades to use the date filter
old_closed = 'closedTrades.forEach(t => {'
new_closed = 'filterTradesByDate(closedTrades || [], cardId).forEach(t => {'
content = content.replace(old_closed, new_closed)

# Update the closed trades count
old_count = '''html += '<button class=\"tab-btn ' + (currentTab === 'closed' ? 'active' : '') + '\" onclick=\"switchTab(\\'' + cardId + '\\', \\'closed\\')\">Closed (' + (closedTrades?.length || 0) + ')</button>';'''
new_count = '''html += '<button class=\"tab-btn ' + (currentTab === 'closed' ? 'active' : '') + '\" onclick=\"switchTab(\\'' + cardId + '\\', \\'closed\\')\">Closed (' + filterTradesByDate(closedTrades || [], cardId).length + ')</button>';'''
content = content.replace(old_count, new_count)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Step 4: Updated closed trades to use date filter')
