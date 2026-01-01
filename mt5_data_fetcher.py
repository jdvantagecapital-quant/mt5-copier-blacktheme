"""
MT5 Data Fetcher - Direct fetching from MT5 terminals
Fetches live positions, closed trades, and account info
"""
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import json


def get_mt5_positions(login, server, password=None, terminal_path=None):
    """Get current open positions from MT5 account"""
    try:
        # Initialize MT5
        if terminal_path:
            if not mt5.initialize(path=terminal_path):
                return {'success': False, 'error': f'MT5 init failed: {mt5.last_error()}'}
        else:
            if not mt5.initialize():
                return {'success': False, 'error': f'MT5 init failed: {mt5.last_error()}'}
        
        # Check if already logged in (terminal running)
        account_info = mt5.account_info()
        
        # If not logged in and password provided, try login
        if account_info is None or account_info.login != login:
            if password:
                if not mt5.login(login=login, password=password, server=server):
                    mt5.shutdown()
                    return {'success': False, 'error': f'Login failed: {mt5.last_error()}'}
                account_info = mt5.account_info()
            else:
                # No password and not logged in
                mt5.shutdown()
                return {'success': False, 'error': 'Terminal not logged in and no password provided'}
        
        if account_info is None:
            mt5.shutdown()
            return {'success': False, 'error': 'Failed to get account info'}
        
        # Get positions
        positions = mt5.positions_get()
        if positions is None:
            positions = []
        
        # Convert positions to dict
        positions_list = []
        for pos in positions:
            positions_list.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': pos.type,
                'type_str': 'BUY' if pos.type == 0 else 'SELL',
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'sl': pos.sl,
                'tp': pos.tp,
                'profit': pos.profit,
                'time': datetime.fromtimestamp(pos.time).strftime('%Y-%m-%d %H:%M:%S'),
                'comment': pos.comment
            })
        
        result = {
            'success': True,
            'account': {
                'login': account_info.login,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'profit': account_info.profit,
                'margin': account_info.margin,
                'margin_free': account_info.margin_free,
                'margin_level': account_info.margin_level if account_info.margin > 0 else 0
            },
            'positions': positions_list,
            'count': len(positions_list)
        }
        
        mt5.shutdown()
        return result
        
    except Exception as e:
        try:
            mt5.shutdown()
        except:
            pass
        return {'success': False, 'error': str(e)}


def get_mt5_history(login, server, password=None, terminal_path=None, days=30, date_from=None, date_to=None):
    """Get trade history from MT5 account"""
    try:
        # Initialize MT5
        if terminal_path:
            if not mt5.initialize(path=terminal_path):
                return {'success': False, 'error': f'MT5 init failed: {mt5.last_error()}'}
        else:
            if not mt5.initialize():
                return {'success': False, 'error': f'MT5 init failed: {mt5.last_error()}'}
        
        # Login if credentials provided
        if password:
            if not mt5.login(login=login, password=password, server=server):
                mt5.shutdown()
                return {'success': False, 'error': f'Login failed: {mt5.last_error()}'}
        
        # Get history date range
        if date_from and date_to:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)  # Include end date
            except:
                from_date = datetime.now() - timedelta(days=days)
                to_date = datetime.now()
        else:
            from_date = datetime.now() - timedelta(days=days)
            to_date = datetime.now()
        
        deals = mt5.history_deals_get(from_date, to_date)
        if deals is None:
            deals = []
        
        # Convert deals to dict - filter only BUY/SELL trades (not balance, etc)
        deals_list = []
        for deal in deals:
            if deal.type in [0, 1]:  # Only BUY and SELL
                deals_list.append({
                    'ticket': deal.ticket,
                    'order': deal.order,
                    'symbol': deal.symbol,
                    'type': deal.type,
                    'type_str': 'BUY' if deal.type == 0 else 'SELL',
                    'volume': deal.volume,
                    'price': deal.price,
                    'profit': deal.profit,
                    'commission': deal.commission,
                    'swap': deal.swap,
                    'fee': deal.fee,
                    'time': datetime.fromtimestamp(deal.time).strftime('%Y-%m-%d %H:%M:%S'),
                    'close_time': datetime.fromtimestamp(deal.time).strftime('%Y-%m-%d %H:%M:%S'),
                    'close_price': deal.price,
                    'comment': deal.comment
                })
        
        mt5.shutdown()
        return {
            'success': True,
            'deals': deals_list,
            'count': len(deals_list),
            'from_date': from_date.strftime('%Y-%m-%d'),
            'to_date': to_date.strftime('%Y-%m-%d')
        }
        
    except Exception as e:
        try:
            mt5.shutdown()
        except:
            pass
        return {'success': False, 'error': str(e)}


def get_deal_type_str(deal_type):
    """Convert deal type to string"""
    types = {
        0: 'BUY',
        1: 'SELL',
        2: 'BALANCE',
        3: 'CREDIT',
        4: 'CHARGE',
        5: 'CORRECTION',
        6: 'BONUS',
        7: 'COMMISSION',
        8: 'DAILY_COMMISSION',
        9: 'DAILY_AGENT_COMMISSION',
        10: 'INTEREST',
        11: 'BUY_CANCELED',
        12: 'SELL_CANCELED',
        13: 'DIVIDEND',
        14: 'DIVIDEND_FRANKED',
        15: 'TAX'
    }
    return types.get(deal_type, 'UNKNOWN')


def get_mt5_closed_orders(login, server, password=None, terminal_path=None, days=30, date_from=None, date_to=None):
    """Get closed orders from MT5 account"""
    try:
        # Initialize MT5
        if terminal_path:
            if not mt5.initialize(path=terminal_path):
                return {'success': False, 'error': f'MT5 init failed: {mt5.last_error()}'}
        else:
            if not mt5.initialize():
                return {'success': False, 'error': f'MT5 init failed: {mt5.last_error()}'}
        
        # Login if credentials provided
        if password:
            if not mt5.login(login=login, password=password, server=server):
                mt5.shutdown()
                return {'success': False, 'error': f'Login failed: {mt5.last_error()}'}
        
        # Get history date range
        if date_from and date_to:
            try:
                from_dt = datetime.strptime(date_from, '%Y-%m-%d')
                to_dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            except:
                from_dt = datetime.now() - timedelta(days=days)
                to_dt = datetime.now()
        else:
            from_dt = datetime.now() - timedelta(days=days)
            to_dt = datetime.now()
        
        orders = mt5.history_orders_get(from_dt, to_dt)
        if orders is None:
            orders = []
        
        # Filter completed orders and convert to dict
        orders_list = []
        for order in orders:
            if order.state in [1, 2]:  # Filled or Partially filled
                orders_list.append({
                    'ticket': order.ticket,
                    'symbol': order.symbol,
                    'type': order.type,
                    'type_str': 'BUY' if order.type == 0 else 'SELL' if order.type == 1 else 'OTHER',
                    'volume_initial': order.volume_initial,
                    'volume_current': order.volume_current,
                    'price_open': order.price_open,
                    'price_current': order.price_current,
                    'sl': order.sl,
                    'tp': order.tp,
                    'time_setup': datetime.fromtimestamp(order.time_setup).strftime('%Y-%m-%d %H:%M:%S'),
                    'time_done': datetime.fromtimestamp(order.time_done).strftime('%Y-%m-%d %H:%M:%S'),
                    'state': order.state,
                    'comment': order.comment
                })
        
        mt5.shutdown()
        return {
            'success': True,
            'orders': orders_list,
            'count': len(orders_list),
            'from_date': from_dt.strftime('%Y-%m-%d'),
            'to_date': to_dt.strftime('%Y-%m-%d')
        }
        
    except Exception as e:
        try:
            mt5.shutdown()
        except:
            pass
        return {'success': False, 'error': str(e)}


def get_account_live_data(login, server, password=None, terminal_path=None, date_from=None, date_to=None, days=30):
    """Get all account data - positions, history, balance in one call"""
    result = {
        'success': False,
        'balance': 0,
        'equity': 0,
        'positions': [],
        'closed_trades': [],
        'error': None
    }
    
    try:
        # Initialize MT5
        if terminal_path:
            if not mt5.initialize(path=terminal_path):
                result['error'] = f'MT5 init failed: {mt5.last_error()}'
                return result
        else:
            if not mt5.initialize():
                result['error'] = f'MT5 init failed: {mt5.last_error()}'
                return result
        
        # Check account info
        account_info = mt5.account_info()
        
        # Login if needed
        if account_info is None or account_info.login != login:
            if password:
                if not mt5.login(login=login, password=password, server=server):
                    mt5.shutdown()
                    result['error'] = f'Login failed: {mt5.last_error()}'
                    return result
                account_info = mt5.account_info()
        
        if account_info is None:
            mt5.shutdown()
            result['error'] = 'Failed to get account info'
            return result
        
        result['balance'] = round(account_info.balance, 2)
        result['equity'] = round(account_info.equity, 2)
        
        # Get open positions
        positions = mt5.positions_get()
        if positions:
            for pos in positions:
                result['positions'].append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': pos.type,
                    'volume': pos.volume,
                    'price_open': round(pos.price_open, 5),
                    'profit': round(pos.profit, 2)
                })
        
        # Get closed trades (deals)
        if date_from and date_to:
            try:
                from_dt = datetime.strptime(date_from, '%Y-%m-%d')
                to_dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            except:
                from_dt = datetime.now() - timedelta(days=days)
                to_dt = datetime.now()
        else:
            from_dt = datetime.now() - timedelta(days=days)
            to_dt = datetime.now()
        
        deals = mt5.history_deals_get(from_dt, to_dt)
        if deals:
            for deal in deals:
                if deal.type in [0, 1] and deal.entry == 1:  # BUY/SELL and OUT (closing deals)
                    result['closed_trades'].append({
                        'ticket': deal.ticket,
                        'symbol': deal.symbol,
                        'type': deal.type,
                        'volume': deal.volume,
                        'close_price': round(deal.price, 5),
                        'profit': round(deal.profit, 2),
                        'close_time': datetime.fromtimestamp(deal.time).strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        result['success'] = True
        mt5.shutdown()
        return result
        
    except Exception as e:
        try:
            mt5.shutdown()
        except:
            pass
        result['error'] = str(e)
        return result
