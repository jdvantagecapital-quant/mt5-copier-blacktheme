"""
Secure Storage Module for MT5 Trade Copier
Handles encrypted data storage in AppData folder
"""

import os
import json
import base64
import hashlib
from cryptography.fernet import Fernet
from pathlib import Path

# Application info
APP_NAME = "JD_MT5_TradeCopier"
APP_VERSION = "1.0.0"

def get_app_data_dir():
    """Get the application data directory in AppData/Local"""
    if os.name == 'nt':  # Windows
        base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~/.local/share')
    
    app_dir = os.path.join(base, APP_NAME)
    
    # Create directories if they don't exist
    os.makedirs(app_dir, exist_ok=True)
    os.makedirs(os.path.join(app_dir, 'data'), exist_ok=True)
    os.makedirs(os.path.join(app_dir, 'logs'), exist_ok=True)
    
    return app_dir

def get_machine_id():
    """Generate a unique machine identifier for encryption"""
    import platform
    import uuid
    
    # Combine multiple system identifiers
    machine_info = f"{platform.node()}-{uuid.getnode()}-{os.name}"
    return hashlib.sha256(machine_info.encode()).hexdigest()[:32]

def get_encryption_key():
    """Get or generate encryption key tied to this machine"""
    app_dir = get_app_data_dir()
    key_file = os.path.join(app_dir, '.key')
    
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            return f.read()
    
    # Generate new key using machine ID as seed
    machine_id = get_machine_id()
    key = base64.urlsafe_b64encode(machine_id.encode()[:32].ljust(32, b'0'))
    
    with open(key_file, 'wb') as f:
        f.write(key)
    
    # Hide the key file on Windows
    if os.name == 'nt':
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(key_file, 2)  # FILE_ATTRIBUTE_HIDDEN
    
    return key

def encrypt_data(data):
    """Encrypt data using Fernet"""
    key = get_encryption_key()
    f = Fernet(key)
    json_data = json.dumps(data).encode()
    return f.encrypt(json_data)

def decrypt_data(encrypted_data):
    """Decrypt data using Fernet"""
    key = get_encryption_key()
    f = Fernet(key)
    decrypted = f.decrypt(encrypted_data)
    return json.loads(decrypted.decode())

class SecureStorage:
    """Secure storage for application data"""
    
    def __init__(self):
        self.app_dir = get_app_data_dir()
        self.data_dir = os.path.join(self.app_dir, 'data')
        self.logs_dir = os.path.join(self.app_dir, 'logs')
    
    def _get_file_path(self, filename, encrypted=True):
        """Get full path for a data file"""
        if encrypted:
            return os.path.join(self.data_dir, filename + '.enc')
        return os.path.join(self.data_dir, filename)
    
    def save(self, filename, data, encrypt=True):
        """Save data to file (optionally encrypted)"""
        filepath = self._get_file_path(filename, encrypt)
        
        if encrypt:
            encrypted = encrypt_data(data)
            with open(filepath, 'wb') as f:
                f.write(encrypted)
        else:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
    
    def load(self, filename, default=None, encrypted=True):
        """Load data from file (optionally decrypt)"""
        filepath = self._get_file_path(filename, encrypted)
        
        if not os.path.exists(filepath):
            return default if default is not None else {}
        
        try:
            if encrypted:
                with open(filepath, 'rb') as f:
                    return decrypt_data(f.read())
            else:
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return default if default is not None else {}
    
    def delete(self, filename, encrypted=True):
        """Delete a data file"""
        filepath = self._get_file_path(filename, encrypted)
        if os.path.exists(filepath):
            os.remove(filepath)
    
    def get_log_path(self, filename):
        """Get path for log files"""
        return os.path.join(self.logs_dir, filename)
    
    def save_log(self, filename, data):
        """Save log data (not encrypted, but in hidden folder)"""
        filepath = self.get_log_path(filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_log(self, filename, default=None):
        """Load log data"""
        filepath = self.get_log_path(filename)
        if not os.path.exists(filepath):
            return default if default is not None else []
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            return default if default is not None else []

# Global storage instance
storage = SecureStorage()

# File paths for compatibility
def get_config_path():
    return storage._get_file_path('config', True)

def get_users_path():
    return storage._get_file_path('users', True)

def get_status_path():
    return storage._get_file_path('status', False)

def get_stats_path():
    return storage._get_file_path('stats', False)

def get_secret_key_path():
    return os.path.join(storage.app_dir, '.secret')

def get_shared_file_path():
    return os.path.join(storage.app_dir, 'shared_positions.bin')

def get_master_activity_path():
    return storage.get_log_path('master_activity.json')

def get_child_activity_path():
    return storage.get_log_path('activity_log.json')

def get_trade_log_path():
    return storage.get_log_path('trade_log.txt')