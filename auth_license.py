"""
Simplified Authentication Module for MT5 Trade Copier
License-based authentication - no user login required

The license file handles access control:
- Valid license = full access to dashboard
- No separate user management needed
"""

import os
import sys
from functools import wraps
from flask import session, redirect, url_for, request, flash, jsonify

# Get correct directory for config files (works in both dev and EXE)
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Import license module for access control
from license import get_license_info

def generate_secret_key():
    """Generate a secret key for Flask sessions"""
    import secrets
    import hashlib
    
    # Use license info as part of the key for uniqueness
    license_info = get_license_info()
    if license_info:
        base = f"{license_info.get('license_id', '')}-{license_info.get('client_name', '')}"
    else:
        base = "default-key-mt5-copier"
    
    # Generate a consistent key based on license
    return hashlib.sha256(base.encode()).hexdigest()

def login_required(f):
    """
    Decorator that checks if the application has a valid license.
    Since license is checked at startup, this just ensures session is valid.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        license_info = get_license_info()
        if not license_info:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'No valid license'}), 401
            return redirect(url_for('license_error'))
        
        # Ensure session has license info
        if 'licensed' not in session:
            session['licensed'] = True
            session['client_name'] = license_info.get('client_name', 'Unknown')
            session['license_id'] = license_info.get('license_id', '')
        
        return f(*args, **kwargs)
    return decorated_function

def developer_required(f):
    """
    Decorator for developer-only routes.
    With license system, all licensed users have full access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        license_info = get_license_info()
        if not license_info:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'No valid license'}), 401
            return redirect(url_for('license_error'))
        
        # All licensed users have developer-level access
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """
    Get current user info from license.
    Returns a user-like dict for template compatibility.
    """
    license_info = get_license_info()
    if not license_info:
        return None
    
    return {
        'id': license_info.get('license_id', ''),
        'username': license_info.get('client_name', 'Licensed User'),
        'role': 'developer',  # All licensed users have full access
        'active': True,
        'license_info': license_info
    }

def get_user_by_id(user_id):
    """Get user by ID - returns current license holder"""
    return get_current_user()

def authenticate_user(username, password):
    """
    Authenticate user - not used with license system.
    Returns license holder info.
    """
    license_info = get_license_info()
    if license_info:
        return get_current_user(), None
    return None, "No valid license"

def verify_access_code(code):
    """Not used with license system"""
    return None, "Access codes not supported with license authentication"

def create_user(username, role, assigned_pairs=None):
    """Not used with license system"""
    return None, "User management not available with license authentication"

def update_user(user_id, updates):
    """Not used with license system"""
    return False

def delete_user(user_id):
    """Not used with license system"""
    return False

def reset_password(user_id):
    """Not used with license system"""
    return None

def get_all_users():
    """Return current license holder as only user"""
    user = get_current_user()
    if user:
        return [user]
    return []

def generate_user_access_code(user_id):
    """Not used with license system"""
    return None

def can_access_pair(user, pair_index):
    """
    Check if user can access a pair.
    Licensed users can access all pairs within license limits.
    """
    license_info = get_license_info()
    if not license_info:
        return False
    
    max_pairs = license_info.get('max_pairs', 5)
    return pair_index < max_pairs

def get_user_pairs(user, all_pairs):
    """
    Get pairs user can access.
    Returns all pairs up to license limit.
    """
    license_info = get_license_info()
    if not license_info:
        return []
    
    max_pairs = license_info.get('max_pairs', 5)
    return [(i, p) for i, p in enumerate(all_pairs) if i < max_pairs]

def verify_password(password, stored_hash):
    """Not used with license system"""
    return False

def init_default_developer():
    """
    Initialize default developer - not needed with license system.
    Kept for backward compatibility.
    """
    pass

def hash_password(password, salt=None):
    """Not used with license system"""
    return ""

def load_users():
    """Return empty users - license handles auth"""
    return {'users': [], 'access_codes': {}}

def save_users(data):
    """Not used with license system"""
    pass
