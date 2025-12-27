"""
License Validation Module for MT5 Trade Copier
Validates encrypted BAT license files

This module handles:
- Finding and parsing license BAT files
- Decrypting and validating license data
- Checking expiry and feature limits
"""

import os
import sys
import re
import base64
import json
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from cryptography.fernet import Fernet, InvalidToken

# =====================================================
# CONFIGURATION - Must match license_generator.py
# =====================================================
MASTER_SECRET = "JD_MT5_COPIER_2024_ULTRA_SECRET_KEY_CHANGE_THIS"
LICENSE_VERSION = "2.0"

# License cache (to avoid re-reading file)
_cached_license = None

def get_hwid():
    """Get Hardware ID of current machine"""
    import subprocess
    try:
        # Get motherboard serial
        result = subprocess.run(
            ['wmic', 'baseboard', 'get', 'serialnumber'],
            capture_output=True, text=True, timeout=10
        )
        mb_serial = result.stdout.strip().split('\n')[-1].strip()
        
        # Get CPU ID
        result = subprocess.run(
            ['wmic', 'cpu', 'get', 'processorid'],
            capture_output=True, text=True, timeout=10
        )
        cpu_id = result.stdout.strip().split('\n')[-1].strip()
        
        # Combine and hash
        combined = f"{mb_serial}-{cpu_id}"
        hwid = hashlib.sha256(combined.encode()).hexdigest()[:16].upper()
        return hwid
    except:
        return None

class LicenseError(Exception):
    """Custom exception for license errors"""
    pass

class LicenseExpiredError(LicenseError):
    """License has expired"""
    pass

class LicenseInvalidError(LicenseError):
    """License is invalid or corrupted"""
    pass

class LicenseHWIDMismatchError(LicenseError):
    """License is bound to different hardware"""
    pass

class LicenseNotFoundError(LicenseError):
    """License file not found"""
    pass

def generate_encryption_key(license_id):
    """Generate encryption key matching the generator"""
    combined = f"{MASTER_SECRET}-{license_id}-{LICENSE_VERSION}"
    key_bytes = hashlib.sha256(combined.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)

def decrypt_license_data(encrypted_data, license_id):
    """Decrypt license data"""
    try:
        key = generate_encryption_key(license_id)
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_data)
        return json.loads(decrypted.decode())
    except InvalidToken:
        raise LicenseInvalidError("License data is corrupted or has been modified")
    except Exception as e:
        raise LicenseInvalidError(f"Failed to decrypt license: {str(e)}")

def find_license_file():
    """
    Find the license BAT file in the same folder as the EXE
    Returns the path to the license file or None
    """
    # Get the directory where the EXE/script is located
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Look for license*.bat files
    license_files = []
    for file in os.listdir(exe_dir):
        if file.lower().startswith('license') and file.lower().endswith('.bat'):
            license_files.append(os.path.join(exe_dir, file))
    
    if len(license_files) == 1:
        return license_files[0]
    elif len(license_files) > 1:
        # Multiple license files - let user choose
        return None
    else:
        return None

def parse_license_bat(filepath):
    """
    Parse a license BAT file and extract license data
    Returns tuple (license_id, encrypted_data, version)
    """
    if not os.path.exists(filepath):
        raise LicenseNotFoundError(f"License file not found: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        with open(filepath, 'r', encoding='latin-1') as f:
            content = f.read()
    
    # Extract license ID
    license_id_match = re.search(r'set\s+"?JD_LICENSE_ID=([A-F0-9]+)"?', content, re.IGNORECASE)
    if not license_id_match:
        raise LicenseInvalidError("Invalid license file format - missing license ID")
    license_id = license_id_match.group(1)
    
    # Extract license data
    license_data_match = re.search(r'set\s+"?JD_LICENSE_DATA=([A-Za-z0-9+/=]+)"?', content, re.IGNORECASE)
    if not license_data_match:
        raise LicenseInvalidError("Invalid license file format - missing license data")
    encoded_data = license_data_match.group(1)
    
    # Extract version
    version_match = re.search(r'set\s+"?JD_LICENSE_VER=([0-9.]+)"?', content, re.IGNORECASE)
    version = version_match.group(1) if version_match else "1.0"
    
    # Decode the base64 data
    try:
        encrypted_data = base64.b64decode(encoded_data)
    except:
        raise LicenseInvalidError("License data is corrupted")
    
    return license_id, encrypted_data, version

def validate_license(license_data):
    """
    Validate the decrypted license data
    Returns True if valid, raises exception if not
    """
    # Check required fields
    required_fields = ['license_id', 'client_name', 'expiry_date', 'expiry_timestamp']
    for field in required_fields:
        if field not in license_data:
            raise LicenseInvalidError(f"License is missing required field: {field}")
    
    # Check version compatibility
    if license_data.get('version', '1.0') != LICENSE_VERSION:
        # Allow older versions for backward compatibility
        pass
    
    # Check checksum
    expected_checksum = hashlib.sha256(
        f"{license_data['license_id']}{license_data['client_name']}{license_data['expiry_date']}".encode()
    ).hexdigest()[:16]
    if license_data.get('checksum') != expected_checksum:
        raise LicenseInvalidError("License has been modified and is no longer valid")
    
    # Check HWID binding
    hwid_binding = license_data.get('hwid_binding')
    if hwid_binding:
        current_hwid = get_hwid()
        if current_hwid and current_hwid != hwid_binding:
            raise LicenseHWIDMismatchError(
                f"License is bound to a different computer.\n"
                f"Expected HWID: {hwid_binding}\n"
                f"Current HWID: {current_hwid}"
            )
    
    # Check expiry
    expiry_timestamp = license_data.get('expiry_timestamp', 0)
    if datetime.now().timestamp() > expiry_timestamp:
        expiry_date = license_data.get('expiry_date', 'unknown')
        raise LicenseExpiredError(f"License expired on {expiry_date}")
    
    return True

def load_license(filepath=None, force_reload=False):
    """
    Load and validate a license file
    
    Args:
        filepath: Path to the license BAT file (optional)
        force_reload: Force reload even if cached
    
    Returns:
        dict with license information
    """
    global _cached_license
    
    # Return cached if available
    if _cached_license and not force_reload:
        # Re-check expiry
        if datetime.now().timestamp() < _cached_license.get('expiry_timestamp', 0):
            return _cached_license
    
    # Find license file if not provided
    if filepath is None:
        filepath = find_license_file()
    
    if filepath is None:
        raise LicenseNotFoundError("No license file found. Please place your license.bat file in the same folder as the application.")
    
    # Parse the BAT file
    license_id, encrypted_data, version = parse_license_bat(filepath)
    
    # Decrypt the license data
    license_data = decrypt_license_data(encrypted_data, license_id)
    
    # Validate the license
    validate_license(license_data)
    
    # Cache it
    _cached_license = license_data
    
    return license_data

def get_license_info():
    """Get cached license info or None if not loaded"""
    return _cached_license

def check_license_limits(current_pairs, pair_children_count):
    """
    Check if current usage is within license limits
    
    Args:
        current_pairs: Current number of copy pairs
        pair_children_count: Dict of {pair_id: child_count}
    
    Returns:
        Tuple (is_ok, error_message)
    """
    if not _cached_license:
        return False, "License not loaded"
    
    max_pairs = _cached_license.get('max_pairs', 5)
    max_children = _cached_license.get('max_children', 10)
    
    if current_pairs > max_pairs:
        return False, f"License allows maximum {max_pairs} copy pairs. You have {current_pairs}."
    
    for pair_id, child_count in pair_children_count.items():
        if child_count > max_children:
            return False, f"License allows maximum {max_children} children per pair. Pair {pair_id} has {child_count}."
    
    return True, None

def show_license_dialog():
    """
    Show a dialog to select license file
    Returns the selected file path or None
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Center the dialog
    root.update_idletasks()
    
    # Show file dialog
    filepath = filedialog.askopenfilename(
        title="Select License File",
        filetypes=[
            ("License Files", "*.bat"),
            ("All Files", "*.*")
        ],
        initialdir=os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
    )
    
    root.destroy()
    
    return filepath if filepath else None

def show_error_dialog(title, message):
    """Show an error dialog"""
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title, message)
    root.destroy()

def show_info_dialog(title, message):
    """Show an info dialog"""
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(title, message)
    root.destroy()

def verify_license_startup():
    """
    Verify license at application startup
    
    Returns:
        Tuple (success, license_data or error_message)
    """
    try:
        # First try to find license automatically
        license_file = find_license_file()
        
        if license_file is None:
            # Show dialog to select license file
            print("[*] No license file found. Asking user to select...")
            license_file = show_license_dialog()
            
            if license_file is None:
                return False, "No license file selected. Application cannot start."
        
        print(f"[*] Loading license from: {license_file}")
        
        # Load and validate
        license_data = load_license(license_file)
        
        # Calculate days remaining
        expiry_timestamp = license_data.get('expiry_timestamp', 0)
        days_remaining = int((expiry_timestamp - datetime.now().timestamp()) / 86400)
        
        print(f"[*] License valid for: {license_data.get('client_name', 'Unknown')}")
        print(f"[*] Expires: {license_data.get('expiry_date', 'Unknown')} ({days_remaining} days remaining)")
        
        # Show warning if expiring soon
        if days_remaining <= 7:
            show_info_dialog(
                "License Expiring Soon",
                f"Your license will expire in {days_remaining} days.\n"
                f"Expiry date: {license_data.get('expiry_date')}\n\n"
                "Please contact support to renew your license."
            )
        
        return True, license_data
        
    except LicenseExpiredError as e:
        error_msg = str(e)
        show_error_dialog("License Expired", error_msg + "\n\nPlease contact support to renew your license.")
        return False, error_msg
        
    except LicenseInvalidError as e:
        error_msg = str(e)
        show_error_dialog("Invalid License", error_msg + "\n\nPlease ensure you are using a valid license file.")
        return False, error_msg
        
    except LicenseNotFoundError as e:
        error_msg = str(e)
        show_error_dialog("License Not Found", error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Unexpected error validating license: {str(e)}"
        show_error_dialog("License Error", error_msg)
        return False, error_msg

# For testing
if __name__ == "__main__":
    print("Testing license validation...")
    success, result = verify_license_startup()
    if success:
        print(f"License loaded successfully!")
        print(f"Client: {result.get('client_name')}")
        print(f"Expires: {result.get('expiry_date')}")
        print(f"Max Pairs: {result.get('max_pairs')}")
        print(f"Max Children: {result.get('max_children')}")
    else:
        print(f"License validation failed: {result}")
