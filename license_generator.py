"""
License Generator for MT5 Trade Copier
Creates encrypted BAT license files for clients

This tool is for the DEVELOPER only - NOT distributed to clients
"""

import os
import sys
import base64
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# =====================================================
# CONFIGURATION - Change these for your security
# =====================================================
MASTER_SECRET = "JD_MT5_COPIER_2024_ULTRA_SECRET_KEY_CHANGE_THIS"
LICENSE_VERSION = "2.0"

def get_hwid():
    """Get Hardware ID of current machine (for testing/display purposes)"""
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

def generate_encryption_key(license_id):
    """Generate a unique encryption key based on license ID and master secret"""
    combined = f"{MASTER_SECRET}-{license_id}-{LICENSE_VERSION}"
    key_bytes = hashlib.sha256(combined.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)

def encrypt_license_data(license_data, license_id):
    """Encrypt license data"""
    key = generate_encryption_key(license_id)
    fernet = Fernet(key)
    json_data = json.dumps(license_data).encode()
    return fernet.encrypt(json_data)

def generate_license_id():
    """Generate a unique license ID"""
    return secrets.token_hex(8).upper()

def create_license_bat(client_name, expiry_date, max_pairs=5, max_children=10, output_folder=None, hwid_binding=None):
    """
    Create an encrypted BAT license file for a client
    
    Args:
        client_name: Client's name/company
        expiry_date: License expiry date (datetime object or string 'YYYY-MM-DD')
        max_pairs: Maximum number of copy pairs allowed
        max_children: Maximum children per pair
        output_folder: Where to save the license file
        hwid_binding: Hardware ID to bind license to (None = no binding)
    
    Returns:
        Tuple (license_file_path, license_id, license_key)
    """
    # Parse expiry date
    if isinstance(expiry_date, str):
        expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d")
    
    # Generate unique license ID
    license_id = generate_license_id()
    
    # Create the expiry date string for consistent checksum
    expiry_date_str = expiry_date.strftime("%Y-%m-%d")
    
    # Create license data
    license_data = {
        "version": LICENSE_VERSION,
        "license_id": license_id,
        "client_name": client_name,
        "created_at": datetime.now().isoformat(),
        "expiry_date": expiry_date_str,
        "expiry_timestamp": expiry_date.timestamp(),
        "max_pairs": max_pairs,
        "max_children": max_children,
        "hwid_binding": hwid_binding,  # None = no binding, otherwise HWID string
        "features": {
            "web_dashboard": True,
            "multi_pair": True,
            "trade_history": True,
            "real_time_sync": True
        },
        "checksum": hashlib.sha256(f"{license_id}{client_name}{expiry_date_str}".encode()).hexdigest()[:16]
    }
    
    # Encrypt the license data
    encrypted_data = encrypt_license_data(license_data, license_id)
    
    # Convert to base64 for BAT file (safe for command line)
    encoded_data = base64.b64encode(encrypted_data).decode()
    
    # Create BAT file content with obfuscation
    # The BAT file sets environment variables that the EXE reads
    bat_content = f'''@echo off
REM =====================================================
REM JD MT5 Trade Copier - License File
REM Licensed to: {client_name}
REM Valid until: {expiry_date.strftime("%Y-%m-%d")}
REM DO NOT MODIFY THIS FILE - License will become invalid
REM =====================================================
REM [LICENSE_DATA_START]
set "JD_LICENSE_ID={license_id}"
set "JD_LICENSE_DATA={encoded_data}"
set "JD_LICENSE_VER={LICENSE_VERSION}"
REM [LICENSE_DATA_END]
REM =====================================================
REM Starting MT5 Trade Copier...
if exist "JD_MT5_TradeCopier.exe" (
    start "" "JD_MT5_TradeCopier.exe" --license-file "%~f0"
) else (
    echo ERROR: JD_MT5_TradeCopier.exe not found in this folder!
    echo Please place this license file in the same folder as the EXE.
    pause
)
'''

    # Determine output folder
    if output_folder is None:
        output_folder = os.path.dirname(os.path.abspath(__file__))
    
    # Create license folder
    licenses_folder = os.path.join(output_folder, "licenses")
    os.makedirs(licenses_folder, exist_ok=True)
    
    # Create filename
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in client_name)
    filename = f"license_{safe_name}_{license_id[:8]}.bat"
    filepath = os.path.join(licenses_folder, filename)
    
    # Write BAT file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(bat_content)
    
    # Generate a license key for backup/verification
    license_key = f"{license_id[:4]}-{license_id[4:8]}-{license_id[8:12]}-{license_id[12:]}"
    
    print("")
    print("=" * 60)
    print("          LICENSE CREATED SUCCESSFULLY!")
    print("=" * 60)
    print(f"  Client Name:   {client_name}")
    print(f"  License ID:    {license_id}")
    print(f"  License Key:   {license_key}")
    print(f"  Expiry Date:   {expiry_date.strftime('%Y-%m-%d')}")
    print(f"  Max Pairs:     {max_pairs}")
    print(f"  Max Children:  {max_children}")
    print(f"  HWID Binding:  {hwid_binding if hwid_binding else 'Not bound (works on any PC)'}")
    print("-" * 60)
    print(f"  File saved to:")
    print(f"  {filepath}")
    print("=" * 60)
    print("")
    
    return filepath, license_id, license_key

def create_license_record(filepath, license_id, license_key, client_name, expiry_date):
    """Save license record for your records"""
    records_file = os.path.join(os.path.dirname(filepath), "..", "license_records.json")
    
    # Load existing records
    records = []
    if os.path.exists(records_file):
        with open(records_file, 'r') as f:
            records = json.load(f)
    
    # Add new record
    records.append({
        "license_id": license_id,
        "license_key": license_key,
        "client_name": client_name,
        "expiry_date": expiry_date.strftime("%Y-%m-%d") if isinstance(expiry_date, datetime) else expiry_date,
        "created_at": datetime.now().isoformat(),
        "file_path": filepath
    })
    
    # Save records
    with open(records_file, 'w') as f:
        json.dump(records, f, indent=2)

def interactive_mode():
    """Interactive license generation"""
    print("")
    print("=" * 60)
    print("     JD MT5 Trade Copier - License Generator")
    print("              Developer Tool v2.0")
    print("=" * 60)
    print("")
    
    # Get client info
    client_name = input("Enter client name/company: ").strip()
    if not client_name:
        print("Error: Client name is required!")
        return
    
    # Get expiry date
    print("\nExpiry options:")
    print("  1. 30 days from now")
    print("  2. 90 days from now")
    print("  3. 180 days from now")
    print("  4. 1 year from now")
    print("  5. Custom date (YYYY-MM-DD)")
    
    choice = input("\nSelect option (1-5): ").strip()
    
    if choice == "1":
        expiry_date = datetime.now() + timedelta(days=30)
    elif choice == "2":
        expiry_date = datetime.now() + timedelta(days=90)
    elif choice == "3":
        expiry_date = datetime.now() + timedelta(days=180)
    elif choice == "4":
        expiry_date = datetime.now() + timedelta(days=365)
    elif choice == "5":
        date_str = input("Enter date (YYYY-MM-DD): ").strip()
        try:
            expiry_date = datetime.strptime(date_str, "%Y-%m-%d")
        except:
            print("Error: Invalid date format!")
            return
    else:
        print("Error: Invalid option!")
        return
    
    # Get limits
    try:
        max_pairs = int(input("\nMax copy pairs allowed (default 5): ").strip() or "5")
        max_children = int(input("Max children per pair (default 10): ").strip() or "10")
    except:
        max_pairs = 5
        max_children = 10
    
    # HWID Binding option
    print("\nHWID (Hardware ID) Binding:")
    print("  1. No binding (license works on any PC)")
    print("  2. Bind to specific HWID")
    print("  3. Show my current HWID")
    
    hwid_binding = None
    hwid_choice = input("\nSelect option (1-3, default 1): ").strip() or "1"
    
    if hwid_choice == "2":
        hwid_input = input("Enter client's HWID (16 characters): ").strip().upper()
        if len(hwid_input) == 16:
            hwid_binding = hwid_input
        else:
            print("Warning: Invalid HWID format. Proceeding without binding.")
    elif hwid_choice == "3":
        my_hwid = get_hwid()
        if my_hwid:
            print(f"\nYour current HWID: {my_hwid}")
        else:
            print("\nCould not retrieve HWID.")
        # Ask again for binding
        hwid_input = input("\nEnter client's HWID to bind (or press Enter to skip): ").strip().upper()
        if len(hwid_input) == 16:
            hwid_binding = hwid_input
    
    # Create license
    filepath, license_id, license_key = create_license_bat(
        client_name, 
        expiry_date, 
        max_pairs, 
        max_children,
        hwid_binding=hwid_binding
    )
    
    # Save record
    create_license_record(filepath, license_id, license_key, client_name, expiry_date)
    
    print("\nLicense file created! Send this BAT file to your client.")
    print("They should place it in the same folder as JD_MT5_TradeCopier.exe")

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        # Command line mode
        if sys.argv[1] == "--help":
            print("""
Usage: python license_generator.py [OPTIONS]

Options:
    --help                  Show this help
    --client NAME          Client name
    --days DAYS            License duration in days
    --date YYYY-MM-DD      Expiry date
    --pairs N              Max pairs (default 5)
    --children N           Max children per pair (default 10)
    --hwid HWID            Bind license to specific HWID (16 char hex)
    --show-hwid            Show current machine's HWID and exit

Examples:
    python license_generator.py --client "John Doe Trading" --days 30
    python license_generator.py --client "ABC Corp" --date 2025-12-31 --pairs 10
    python license_generator.py --client "XYZ Ltd" --days 90 --hwid ABC123DEF4567890
    python license_generator.py --show-hwid
""")
            return
        
        # Show HWID option
        if sys.argv[1] == "--show-hwid":
            my_hwid = get_hwid()
            if my_hwid:
                print(f"Current Machine HWID: {my_hwid}")
            else:
                print("Could not retrieve HWID.")
            return
        
        # Parse command line args
        client_name = None
        expiry_date = None
        max_pairs = 5
        max_children = 10
        hwid_binding = None
        
        i = 1
        while i < len(sys.argv):
            if sys.argv[i] == "--client" and i + 1 < len(sys.argv):
                client_name = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--days" and i + 1 < len(sys.argv):
                expiry_date = datetime.now() + timedelta(days=int(sys.argv[i + 1]))
                i += 2
            elif sys.argv[i] == "--date" and i + 1 < len(sys.argv):
                expiry_date = datetime.strptime(sys.argv[i + 1], "%Y-%m-%d")
                i += 2
            elif sys.argv[i] == "--pairs" and i + 1 < len(sys.argv):
                max_pairs = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--children" and i + 1 < len(sys.argv):
                max_children = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--hwid" and i + 1 < len(sys.argv):
                hwid_binding = sys.argv[i + 1].upper()
                if len(hwid_binding) != 16:
                    print("Warning: HWID should be 16 characters. Proceeding anyway.")
                i += 2
            else:
                i += 1
        
        if client_name and expiry_date:
            filepath, license_id, license_key = create_license_bat(
                client_name, expiry_date, max_pairs, max_children, hwid_binding=hwid_binding
            )
            create_license_record(filepath, license_id, license_key, client_name, expiry_date)
        else:
            print("Error: --client and --days/--date are required!")
    else:
        # Interactive mode
        interactive_mode()

if __name__ == "__main__":
    main()
