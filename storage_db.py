"""
Enhanced Storage Module with Real MT5 Data Support
Includes symbol mapping, comprehensive logging, and trade history
"""

import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# Application info
APP_NAME = "JD_MT5_TradeCopier"

def get_app_data_dir():
    """Get the application data directory in AppData/Local"""
    if os.name == 'nt':  # Windows
        base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~/.local/share')
    
    app_dir = os.path.join(base, APP_NAME)
    os.makedirs(app_dir, exist_ok=True)
    os.makedirs(os.path.join(app_dir, 'data'), exist_ok=True)
    os.makedirs(os.path.join(app_dir, 'logs'), exist_ok=True)
    return app_dir

class MT5DataStorage:
    """Database storage for MT5 real data, logs, and symbol mappings"""
    
    def __init__(self):
        self.app_dir = get_app_data_dir()
        self.db_path = os.path.join(self.app_dir, 'data', 'mt5_data.db')
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with all tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table: account_status - Real-time account data from MT5
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_status (
                account_id INTEGER PRIMARY KEY,
                pair_id TEXT NOT NULL,
                account_type TEXT NOT NULL,
                balance REAL DEFAULT 0,
                equity REAL DEFAULT 0,
                margin REAL DEFAULT 0,
                free_margin REAL DEFAULT 0,
                profit REAL DEFAULT 0,
                server TEXT,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table: positions - Current open positions from MT5
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                ticket INTEGER PRIMARY KEY,
                pair_id TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                account_type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                type INTEGER NOT NULL,
                volume REAL NOT NULL,
                price_open REAL NOT NULL,
                sl REAL DEFAULT 0,
                tp REAL DEFAULT 0,
                profit REAL DEFAULT 0,
                open_time TIMESTAMP,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table: trade_history - Closed trades from MT5
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket INTEGER NOT NULL,
                pair_id TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                account_type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                type INTEGER NOT NULL,
                volume REAL NOT NULL,
                price_open REAL NOT NULL,
                price_close REAL NOT NULL,
                sl REAL DEFAULT 0,
                tp REAL DEFAULT 0,
                profit REAL NOT NULL,
                open_time TIMESTAMP,
                close_time TIMESTAMP,
                duration_seconds INTEGER
            )
        ''')
        
        # Table: symbol_mappings - Inter-broker symbol translation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS symbol_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair_id TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                master_symbol TEXT NOT NULL,
                child_symbol TEXT NOT NULL,
                UNIQUE(pair_id, account_id, master_symbol)
            )
        ''')
        
        # Table: system_logs - Comprehensive debug/error logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pair_id TEXT NOT NULL,
                account_id INTEGER,
                component TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_pair ON positions(pair_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_pair ON trade_history(pair_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_account ON trade_history(account_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_pair ON system_logs(pair_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp)')
        
        conn.commit()
        conn.close()
    
    # === ACCOUNT STATUS ===
    
    def update_account_status(self, account_id, pair_id, account_type, balance, equity, 
                            margin=0, free_margin=0, profit=0, server=''):
        """Update real-time account status from MT5"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO account_status 
            (account_id, pair_id, account_type, balance, equity, margin, free_margin, profit, server, last_update)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (account_id, pair_id, account_type, balance, equity, margin, free_margin, profit, server))
        conn.commit()
        conn.close()
    
    def get_account_status(self, pair_id=None):
        """Get account status for dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if pair_id:
            cursor.execute('SELECT * FROM account_status WHERE pair_id = ? ORDER BY account_type', (pair_id,))
        else:
            cursor.execute('SELECT * FROM account_status ORDER BY pair_id, account_type')
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    # === POSITIONS ===
    
    def update_position(self, ticket, pair_id, account_id, account_type, symbol, 
                       pos_type, volume, price_open, sl=0, tp=0, profit=0, open_time=None):
        """Update current position from MT5"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO positions 
            (ticket, pair_id, account_id, account_type, symbol, type, volume, price_open, sl, tp, profit, open_time, last_update)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (ticket, pair_id, account_id, account_type, symbol, pos_type, volume, price_open, sl, tp, profit, open_time))
        conn.commit()
        conn.close()
    
    def remove_position(self, ticket):
        """Remove position when closed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM positions WHERE ticket = ?', (ticket,))
        conn.commit()
        conn.close()
    
    def get_positions(self, pair_id=None):
        """Get current positions for dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if pair_id:
            cursor.execute('SELECT * FROM positions WHERE pair_id = ? ORDER BY open_time DESC', (pair_id,))
        else:
            cursor.execute('SELECT * FROM positions ORDER BY pair_id, open_time DESC')
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    # === TRADE HISTORY ===
    
    def add_trade_history(self, ticket, pair_id, account_id, account_type, symbol, 
                         trade_type, volume, price_open, price_close, profit, 
                         open_time, close_time, sl=0, tp=0):
        """Add closed trade to history"""
        duration = None
        if open_time and close_time:
            try:
                open_dt = datetime.fromisoformat(open_time)
                close_dt = datetime.fromisoformat(close_time)
                duration = int((close_dt - open_dt).total_seconds())
            except:
                pass
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trade_history 
            (ticket, pair_id, account_id, account_type, symbol, type, volume, price_open, price_close, sl, tp, profit, open_time, close_time, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ticket, pair_id, account_id, account_type, symbol, trade_type, volume, price_open, price_close, sl, tp, profit, open_time, close_time, duration))
        conn.commit()
        conn.close()
    
    def get_trade_history(self, pair_id=None, limit=100):
        """Get trade history for dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if pair_id:
            cursor.execute('SELECT * FROM trade_history WHERE pair_id = ? ORDER BY close_time DESC LIMIT ?', (pair_id, limit))
        else:
            cursor.execute('SELECT * FROM trade_history ORDER BY close_time DESC LIMIT ?', (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    # === SYMBOL MAPPINGS ===
    
    def add_symbol_mapping(self, pair_id, account_id, master_symbol, child_symbol):
        """Add or update symbol mapping for inter-broker trading"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO symbol_mappings (pair_id, account_id, master_symbol, child_symbol)
            VALUES (?, ?, ?, ?)
        ''', (pair_id, account_id, master_symbol, child_symbol))
        conn.commit()
        conn.close()
    
    def get_symbol_mapping(self, pair_id, account_id, master_symbol):
        """Get mapped symbol for a child account"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT child_symbol FROM symbol_mappings 
            WHERE pair_id = ? AND account_id = ? AND master_symbol = ?
        ''', (pair_id, account_id, master_symbol))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else master_symbol  # Return original if no mapping
    
    def get_all_mappings(self, pair_id, account_id):
        """Get all symbol mappings for an account"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT master_symbol, child_symbol FROM symbol_mappings 
            WHERE pair_id = ? AND account_id = ?
        ''', (pair_id, account_id))
        results = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return results
    
    def delete_symbol_mapping(self, pair_id, account_id, master_symbol):
        """Delete a symbol mapping"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM symbol_mappings 
            WHERE pair_id = ? AND account_id = ? AND master_symbol = ?
        ''', (pair_id, account_id, master_symbol))
        conn.commit()
        conn.close()
    
    # === LOGGING ===
    
    def add_log(self, pair_id, component, level, message, account_id=None):
        """Add system log entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_logs (pair_id, account_id, component, level, message)
            VALUES (?, ?, ?, ?, ?)
        ''', (pair_id, account_id, component, level, message))
        conn.commit()
        conn.close()
    
    def get_logs(self, pair_id=None, level=None, limit=200):
        """Get system logs for dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM system_logs WHERE 1=1'
        params = []
        
        if pair_id:
            query += ' AND pair_id = ?'
            params.append(pair_id)
        
        if level:
            query += ' AND level = ?'
            params.append(level)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def clear_old_logs(self, days=7):
        """Clear logs older than specified days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM system_logs 
            WHERE timestamp < datetime('now', ? || ' days')
        ''', (f'-{days}',))
        conn.commit()
        conn.close()

# Global database instance
db = MT5DataStorage()
