"""
MT5 Data Fetcher - Direct fetching from MT5 terminals
Fetches live positions, closed trades, and account info

IMPORTANT: The MT5 Python library can only connect to ONE terminal at a time.
Each account has its own terminal, so we must:
1. Connect to the specific terminal using mt5.initialize(path=terminal_path)
2. Fetch the data we need
3. Shutdown before connecting to the next terminal

This module connects to ALREADY RUNNING MT5 terminals.
The Activate Pair feature opens the terminals first.
"""
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import os
import hashlib

# Track current connection to avoid unnecessary reconnects
# We also track password hash so if password changes, we force re-login
_current_terminal_path = None
_current_login = None
_current_password_hash = None


def _connect_to_terminal(terminal_path, login, server, password):
    """
    Connect to a specific MT5 terminal and login to the account.
    
    The MT5 Python library can only connect to ONE terminal at a time.
    If we need to connect to a different terminal, we must shutdown first.
    
    Returns (success, error_message)
    """
    global _current_terminal_path, _current_login, _current_password_hash
    
    try:
        # Ensure login is an integer
        login = int(login) if login else 0
        if not login:
            return False, 'Invalid login account number'
        
        # Clean and normalize terminal path - strip whitespace, newlines, quotes
        if terminal_path:
            terminal_path = terminal_path.strip().strip('"').strip("'")
        norm_path = os.path.normpath(terminal_path) if terminal_path else None
        
        # Hash password for comparison (so we don't store plaintext)
        pwd_hash = hashlib.md5(password.encode()).hexdigest() if password else None
        
        # Check if we're already connected to this exact terminal, account AND same password
        if _current_terminal_path == norm_path and _current_login == login and _current_password_hash == pwd_hash:
            # Verify connection is still alive
            if mt5.terminal_info() is not None:
                account_info = mt5.account_info()
                if account_info and account_info.login == login:
                    return True, None
        
        # Need to connect to a different terminal - shutdown current first
        try:
            mt5.shutdown()
        except:
            pass
        
        _current_terminal_path = None
        _current_login = None
        
        # Initialize MT5 with specific terminal path
        if terminal_path and os.path.exists(terminal_path):
            if not mt5.initialize(path=terminal_path):
                error = mt5.last_error()
                return False, f'Failed to connect to terminal {terminal_path}: {error}'
        else:
            # No terminal path - try default
            if not mt5.initialize():
                return False, 'MT5 not connected - please activate the pair first or set terminal path'
        
        _current_terminal_path = norm_path
        
        # Check if already logged into correct account with same password
        account_info = mt5.account_info()
        if account_info is not None and account_info.login == login:
            _current_login = login
            _current_password_hash = pwd_hash
            return True, None
        
        # Need to login
        if password:
            if not mt5.login(login=login, password=password, server=server):
                error = mt5.last_error()
                return False, f'Login failed for {login}: {error}'
            _current_login = login
            _current_password_hash = pwd_hash
            return True, None
        else:
            # No password - check if terminal is already logged in
            if account_info is not None:
                # Terminal is logged into a different account
                return False, f'Terminal is logged into {account_info.login}, not {login}. Please provide password.'
            return False, 'No account logged in and no password provided'
            
    except Exception as e:
        return False, str(e)


def _disconnect():
    """Disconnect from current terminal"""
    global _current_terminal_path, _current_login, _current_password_hash
    try:
        mt5.shutdown()
    except:
        pass
    _current_terminal_path = None
    _current_login = None
    _current_password_hash = None


def get_mt5_positions(login, server, password=None, terminal_path=None):
    """Get current open positions from MT5 account"""
    try:
        # Connect to the specific terminal for this account
        success, error = _connect_to_terminal(terminal_path, login, server, password)
        if not success:
            return {'success': False, 'error': error}
        
        account_info = mt5.account_info()
        if account_info is None:
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
        
        # Don't disconnect here - let next call handle it if needed
        return result
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_mt5_history(login, server, password=None, terminal_path=None, days=30, date_from=None, date_to=None):
    """Get trade history from MT5 account"""
    try:
        # Connect to the specific terminal for this account
        success, error = _connect_to_terminal(terminal_path, login, server, password)
        if not success:
            return {'success': False, 'error': error}
        
        # Get history date range
        if date_from and date_to:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            except:
                from_date = datetime.now() - timedelta(days=days)
                to_date = datetime.now()
        else:
            from_date = datetime.now() - timedelta(days=days)
            to_date = datetime.now()
        
        deals = mt5.history_deals_get(from_date, to_date)
        if deals is None:
            deals = []
        
        # Convert deals to dict - filter only BUY/SELL trades
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
        
        return {
            'success': True,
            'deals': deals_list,
            'count': len(deals_list),
            'from_date': from_date.strftime('%Y-%m-%d'),
            'to_date': to_date.strftime('%Y-%m-%d')
        }
        
    except Exception as e:
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
        # Connect to the specific terminal for this account
        success, error = _connect_to_terminal(terminal_path, login, server, password)
        if not success:
            return {'success': False, 'error': error}
        
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
        
        return {
            'success': True,
            'orders': orders_list,
            'count': len(orders_list),
            'from_date': from_dt.strftime('%Y-%m-%d'),
            'to_date': to_dt.strftime('%Y-%m-%d')
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_account_live_data(login, server, password=None, terminal_path=None, date_from=None, date_to=None, days=30):
    """
    Get all account data - positions, history, balance in one call.
    
    IMPORTANT: Each account must have its own terminal_path.
    The MT5 library can only connect to one terminal at a time.
    """
    result = {
        'success': False,
        'balance': 0,
        'equity': 0,
        'positions': [],
        'closed_trades': [],
        'error': None
    }
    
    try:
        # Connect to the specific terminal for this account
        success, error = _connect_to_terminal(terminal_path, login, server, password)
        if not success:
            result['error'] = error
            return result
        
        # Get account info
        account_info = mt5.account_info()
        if account_info is None:
            result['error'] = 'Failed to get account info'
            return result
        
        # Verify we're connected to the right account
        if account_info.login != login:
            result['error'] = f'Connected to wrong account: {account_info.login} instead of {login}'
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
        return result
        
    except Exception as e:
        result['error'] = str(e)
        return result
