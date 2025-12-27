"""
License Generator Web App for MT5 Trade Copier
A simple web interface to create encrypted license files

Run this and open http://127.0.0.1:5001 in your browser
"""

import os
import sys
import base64
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, jsonify, send_file
from cryptography.fernet import Fernet

# =====================================================
# CONFIGURATION - Change these for your security
# =====================================================
MASTER_SECRET = "JD_MT5_COPIER_2024_ULTRA_SECRET_KEY_CHANGE_THIS"
LICENSE_VERSION = "2.0"

app = Flask(__name__)

# Get app directory
APP_DIR = os.path.dirname(os.path.abspath(__file__))
LICENSES_DIR = os.path.join(APP_DIR, "licenses")
RECORDS_FILE = os.path.join(APP_DIR, "license_records.json")

# Create licenses folder
os.makedirs(LICENSES_DIR, exist_ok=True)

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

def create_license_bat(client_name, expiry_date, max_pairs=5, max_children=10, hwid_binding=None):
    """Create an encrypted BAT license file"""
    
    if isinstance(expiry_date, str):
        expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d")
    
    license_id = generate_license_id()
    expiry_date_str = expiry_date.strftime("%Y-%m-%d")
    
    license_data = {
        "version": LICENSE_VERSION,
        "license_id": license_id,
        "client_name": client_name,
        "created_at": datetime.now().isoformat(),
        "expiry_date": expiry_date_str,
        "expiry_timestamp": expiry_date.timestamp(),
        "max_pairs": max_pairs,
        "max_children": max_children,
        "hwid_binding": hwid_binding,
        "features": {
            "web_dashboard": True,
            "multi_pair": True,
            "trade_history": True,
            "real_time_sync": True
        },
        "checksum": hashlib.sha256(f"{license_id}{client_name}{expiry_date_str}".encode()).hexdigest()[:16]
    }
    
    encrypted_data = encrypt_license_data(license_data, license_id)
    encoded_data = base64.b64encode(encrypted_data).decode()
    
    bat_content = f'''@echo off
REM =====================================================
REM JD MT5 Trade Copier - License File
REM Licensed to: {client_name}
REM Valid until: {expiry_date_str}
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
    
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in client_name)
    filename = f"license_{safe_name}_{license_id[:8]}.bat"
    filepath = os.path.join(LICENSES_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(bat_content)
    
    license_key = f"{license_id[:4]}-{license_id[4:8]}-{license_id[8:12]}-{license_id[12:]}"

    save_license_record(license_id, license_key, client_name, expiry_date_str, filepath, max_pairs, max_children, hwid_binding)
    
    return {
        "success": True,
        "license_id": license_id,
        "license_key": license_key,
        "client_name": client_name,
        "expiry_date": expiry_date_str,
        "max_pairs": max_pairs,
        "max_children": max_children,
        "hwid_binding": hwid_binding,
        "filename": filename,
        "filepath": filepath
    }

def save_license_record(license_id, license_key, client_name, expiry_date, filepath, max_pairs, max_children, hwid_binding=None):
    """Save license record"""
    records = load_license_records()
    
    records.append({
        "license_id": license_id,
        "license_key": license_key,
        "client_name": client_name,
        "expiry_date": expiry_date,
        "max_pairs": max_pairs,
        "max_children": max_children,
        "hwid_binding": hwid_binding,
        "created_at": datetime.now().isoformat(),
        "file_path": filepath
    })
    
    with open(RECORDS_FILE, 'w') as f:
        json.dump(records, f, indent=2)

def load_license_records():
    """Load all license records"""
    if os.path.exists(RECORDS_FILE):
        with open(RECORDS_FILE, 'r') as f:
            return json.load(f)
    return []

# HTML Template - Compact Professional Black & White Theme with Glow
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>License Management System</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #000000;
            --bg-secondary: #080808;
            --bg-tertiary: #0f0f0f;
            --bg-card: #0a0a0a;
            --border-primary: #1a1a1a;
            --border-secondary: #252525;
            --border-hover: #333333;
            --text-primary: #ffffff;
            --text-secondary: #a0a0a0;
            --text-muted: #666666;
            --accent: #ffffff;
            --success: #22c55e;
            --danger: #ef4444;
            --warning: #f59e0b;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }
        
        .bg-gradient {
            position: fixed;
            inset: 0;
            background: 
                radial-gradient(ellipse at 20% 20%, rgba(255,255,255,0.02) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(255,255,255,0.015) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }
        
        .container {
            max-width: 1500px;
            margin: 0 auto;
            padding: 20px 24px;
            position: relative;
            z-index: 1;
        }
        
        /* Compact Header */
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 24px;
            margin-bottom: 20px;
            background: linear-gradient(145deg, var(--bg-secondary), var(--bg-primary));
            border: 1px solid var(--border-primary);
            border-radius: 16px;
            position: relative;
            box-shadow: 0 5px 20px rgba(0,0,0,0.3);
            animation: headerGlow 4s ease-in-out infinite;
        }
        
        @keyframes headerGlow {
            0%, 100% { box-shadow: 0 5px 20px rgba(0,0,0,0.3), 0 0 0 rgba(255,255,255,0); }
            50% { box-shadow: 0 5px 20px rgba(0,0,0,0.3), 0 0 30px rgba(255,255,255,0.03); }
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .logo {
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(145deg, var(--bg-tertiary), var(--bg-primary));
            border: 1px solid var(--border-secondary);
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }
        
        .logo i { font-size: 20px; color: var(--text-primary); }
        
        .header-title h1 {
            font-size: 20px;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: var(--text-primary);
        }
        
        .header-title p {
            font-size: 11px;
            color: var(--text-muted);
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        
        /* Compact Stats */
        .stats-row {
            display: flex;
            gap: 12px;
        }
        
        .stat-mini {
            padding: 12px 20px;
            background: linear-gradient(145deg, var(--bg-secondary), var(--bg-primary));
            border: 1px solid var(--border-primary);
            border-radius: 10px;
            text-align: center;
            min-width: 90px;
            transition: all 0.3s ease;
            animation: statGlow 3s ease-in-out infinite;
        }
        
        .stat-mini:nth-child(1) { animation-delay: 0s; }
        .stat-mini:nth-child(2) { animation-delay: 1s; }
        .stat-mini:nth-child(3) { animation-delay: 2s; }
        
        @keyframes statGlow {
            0%, 100% { box-shadow: 0 2px 10px rgba(0,0,0,0.2); }
            50% { box-shadow: 0 2px 10px rgba(0,0,0,0.2), 0 0 20px rgba(255,255,255,0.05); }
        }
        
        .stat-mini:hover {
            transform: translateY(-2px);
            border-color: var(--border-secondary);
        }
        
        .stat-mini .value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 24px;
            font-weight: 700;
            color: var(--text-primary);
        }
        
        .stat-mini .label {
            font-size: 9px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* Main Grid */
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1.3fr;
            gap: 20px;
        }
        
        @media (max-width: 1100px) {
            .main-grid { grid-template-columns: 1fr; }
            .header { flex-direction: column; gap: 16px; text-align: center; }
            .header-left { flex-direction: column; }
            .stats-row { justify-content: center; }
        }
        
        /* Glowing Cards */
        .card {
            background: linear-gradient(145deg, var(--bg-secondary), var(--bg-primary));
            border: 1px solid var(--border-primary);
            border-radius: 16px;
            overflow: hidden;
            position: relative;
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
            animation: cardGlow 5s ease-in-out infinite;
        }
        
        .card:nth-child(1) { animation-delay: 0s; }
        .card:nth-child(2) { animation-delay: 2.5s; }
        
        @keyframes cardGlow {
            0%, 100% { 
                box-shadow: 0 8px 30px rgba(0,0,0,0.3);
                border-color: var(--border-primary);
            }
            50% { 
                box-shadow: 0 8px 30px rgba(0,0,0,0.3), 0 0 40px rgba(255,255,255,0.03);
                border-color: var(--border-secondary);
            }
        }
        
        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
            animation: shimmer 3s ease-in-out infinite;
        }
        
        @keyframes shimmer {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 1; }
        }
        
        .card-header {
            padding: 18px 22px;
            border-bottom: 1px solid var(--border-primary);
            display: flex;
            align-items: center;
            gap: 12px;
            background: linear-gradient(180deg, rgba(255,255,255,0.015), transparent);
        }
        
        .card-header-icon {
            width: 38px;
            height: 38px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(145deg, var(--bg-tertiary), var(--bg-primary));
            border: 1px solid var(--border-secondary);
            border-radius: 10px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        }
        
        .card-header-icon i { font-size: 16px; color: var(--text-primary); }
        
        .card-header h2 {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .card-body { padding: 22px; }
        
        /* Form */
        .form-group { margin-bottom: 18px; }
        
        .form-label {
            display: block;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .form-control {
            width: 100%;
            padding: 12px 14px;
            background: var(--bg-primary);
            border: 1px solid var(--border-primary);
            border-radius: 8px;
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
            font-size: 13px;
            transition: all 0.25s ease;
        }
        
        .form-control:hover { border-color: var(--border-secondary); }
        
        .form-control:focus {
            outline: none;
            border-color: var(--text-muted);
            box-shadow: 0 0 0 3px rgba(255,255,255,0.03), 0 0 20px rgba(255,255,255,0.02);
        }
        
        .form-control::placeholder { color: var(--text-muted); }
        
        /* Duration Quick Options */
        .duration-quick {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
        }
        
        .duration-btn {
            flex: 1;
            padding: 10px 8px;
            background: linear-gradient(145deg, var(--bg-secondary), var(--bg-primary));
            border: 1px solid var(--border-primary);
            border-radius: 8px;
            text-align: center;
            cursor: pointer;
            transition: all 0.25s ease;
            animation: btnGlow 4s ease-in-out infinite;
        }
        
        .duration-btn:nth-child(1) { animation-delay: 0s; }
        .duration-btn:nth-child(2) { animation-delay: 1s; }
        .duration-btn:nth-child(3) { animation-delay: 2s; }
        .duration-btn:nth-child(4) { animation-delay: 3s; }
        
        @keyframes btnGlow {
            0%, 100% { box-shadow: none; }
            50% { box-shadow: 0 0 15px rgba(255,255,255,0.03); }
        }
        
        .duration-btn:hover {
            transform: translateY(-2px);
            border-color: var(--border-secondary);
        }
        
        .duration-btn.active {
            border-color: var(--text-secondary);
            box-shadow: 0 0 20px rgba(255,255,255,0.05);
        }
        
        .duration-btn .num {
            font-family: 'JetBrains Mono', monospace;
            font-size: 16px;
            font-weight: 700;
            color: var(--text-primary);
            display: block;
        }
        
        .duration-btn .txt {
            font-size: 9px;
            color: var(--text-muted);
            text-transform: uppercase;
        }
        
        /* Date Range Picker */
        .date-range-box {
            background: linear-gradient(145deg, var(--bg-secondary), var(--bg-primary));
            border: 1px solid var(--border-primary);
            border-radius: 10px;
            padding: 14px;
            animation: rangeGlow 4s ease-in-out infinite;
        }
        
        @keyframes rangeGlow {
            0%, 100% { box-shadow: inset 0 0 0 rgba(255,255,255,0); }
            50% { box-shadow: inset 0 0 30px rgba(255,255,255,0.01); }
        }
        
        .date-range-row {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .date-input-group {
            flex: 1;
        }
        
        .date-input-group label {
            display: block;
            font-size: 10px;
            color: var(--text-muted);
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .date-input {
            width: 100%;
            padding: 10px 12px;
            background: var(--bg-primary);
            border: 1px solid var(--border-primary);
            border-radius: 6px;
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .date-input:hover { border-color: var(--border-secondary); }
        .date-input:focus {
            outline: none;
            border-color: var(--text-muted);
            box-shadow: 0 0 15px rgba(255,255,255,0.03);
        }
        
        .date-separator {
            color: var(--text-muted);
            font-size: 18px;
            margin-top: 20px;
        }
        
        .duration-display {
            text-align: center;
            margin-top: 10px;
            padding: 8px;
            background: rgba(255,255,255,0.02);
            border-radius: 6px;
            font-size: 12px;
            color: var(--text-secondary);
        }
        
        .duration-display strong {
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
        }
        
        /* Form Row */
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        
        /* Glowing Input Wrapper */
        .input-glow {
            position: relative;
            animation: inputGlow 5s ease-in-out infinite;
        }
        
        @keyframes inputGlow {
            0%, 100% { filter: drop-shadow(0 0 0 rgba(255,255,255,0)); }
            50% { filter: drop-shadow(0 0 8px rgba(255,255,255,0.03)); }
        }
        
        /* HWID Row */
        .hwid-row {
            display: flex;
            gap: 8px;
        }
        
        .hwid-row .form-control {
            flex: 1;
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        
        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 20px;
            font-family: 'Inter', sans-serif;
            font-size: 12px;
            font-weight: 600;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.25s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
            position: relative;
            overflow: hidden;
        }
        
        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
            transition: 0.5s;
        }
        
        .btn:hover::before { left: 100%; }
        
        .btn-primary {
            width: 100%;
            padding: 14px 24px;
            background: linear-gradient(145deg, #ffffff, #d0d0d0);
            color: #000000;
            box-shadow: 0 5px 20px rgba(255,255,255,0.1);
            animation: primaryGlow 3s ease-in-out infinite;
        }
        
        @keyframes primaryGlow {
            0%, 100% { box-shadow: 0 5px 20px rgba(255,255,255,0.1); }
            50% { box-shadow: 0 5px 30px rgba(255,255,255,0.2); }
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(255,255,255,0.25);
        }
        
        .btn-secondary {
            background: linear-gradient(145deg, var(--bg-tertiary), var(--bg-primary));
            border: 1px solid var(--border-secondary);
            color: var(--text-primary);
        }
        
        .btn-secondary:hover {
            transform: translateY(-2px);
            border-color: var(--text-muted);
            box-shadow: 0 5px 20px rgba(0,0,0,0.3), 0 0 15px rgba(255,255,255,0.03);
        }
        
        .btn-icon {
            width: 42px;
            height: 42px;
            padding: 0;
        }
        
        /* Result Card */
        .result-card {
            display: none;
            margin-top: 20px;
            background: linear-gradient(145deg, rgba(34, 197, 94, 0.08), rgba(34, 197, 94, 0.02));
            border: 1px solid rgba(34, 197, 94, 0.25);
            border-radius: 12px;
            overflow: hidden;
            animation: resultGlow 2s ease-in-out infinite, slideDown 0.4s ease;
        }
        
        .result-card.show { display: block; }
        
        @keyframes resultGlow {
            0%, 100% { box-shadow: 0 0 20px rgba(34, 197, 94, 0.1); }
            50% { box-shadow: 0 0 40px rgba(34, 197, 94, 0.2); }
        }
        
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .result-header {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px 18px;
            background: rgba(34, 197, 94, 0.08);
            border-bottom: 1px solid rgba(34, 197, 94, 0.15);
        }
        
        .result-header i {
            font-size: 20px;
            color: var(--success);
            animation: checkPop 0.5s ease;
        }
        
        @keyframes checkPop {
            0% { transform: scale(0); }
            50% { transform: scale(1.2); }
            100% { transform: scale(1); }
        }
        
        .result-header span {
            font-size: 13px;
            font-weight: 600;
            color: var(--success);
        }
        
        .result-body { padding: 16px 18px; }
        
        .result-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--border-primary);
        }
        
        .result-row:last-child { border-bottom: none; }
        
        .result-label {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .result-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .result-actions {
            display: flex;
            gap: 10px;
            padding: 14px 18px;
            border-top: 1px solid var(--border-primary);
        }
        
        .result-actions .btn { flex: 1; padding: 10px 16px; }
        
        /* Filters */
        .filters-section {
            padding: 16px 20px;
            background: rgba(255,255,255,0.01);
            border-bottom: 1px solid var(--border-primary);
        }
        
        .filters-row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .filter-group { flex: 1; min-width: 120px; }
        .filter-group.search { flex: 2; }
        
        .filter-control {
            width: 100%;
            padding: 9px 12px;
            background: var(--bg-primary);
            border: 1px solid var(--border-primary);
            border-radius: 6px;
            color: var(--text-primary);
            font-size: 12px;
            transition: all 0.2s ease;
        }
        
        .filter-control:focus {
            outline: none;
            border-color: var(--text-muted);
            box-shadow: 0 0 10px rgba(255,255,255,0.02);
        }
        
        .filter-btn {
            padding: 9px 14px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-primary);
            border-radius: 6px;
            color: var(--text-secondary);
            font-size: 11px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .filter-btn:hover, .filter-btn.active {
            border-color: var(--text-muted);
            color: var(--text-primary);
            background: var(--bg-tertiary);
            box-shadow: 0 0 12px rgba(255,255,255,0.03);
        }
        
        /* Table */
        .table-wrapper {
            max-height: 450px;
            overflow: auto;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .data-table th, .data-table td {
            padding: 14px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border-primary);
        }
        
        .data-table th {
            font-size: 9px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            background: var(--bg-secondary);
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        .data-table td { font-size: 12px; color: var(--text-primary); }
        
        .data-table tbody tr {
            transition: all 0.2s ease;
        }
        
        .data-table tbody tr:hover {
            background: rgba(255,255,255,0.015);
        }
        
        .client-name { font-weight: 600; }
        
        .license-key {
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            color: var(--text-secondary);
            background: var(--bg-secondary);
            padding: 3px 6px;
            border-radius: 4px;
        }
        
        .date-cell {
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: var(--text-secondary);
        }
        
        /* Badge */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 9px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .badge-success {
            background: rgba(34, 197, 94, 0.12);
            color: var(--success);
            border: 1px solid rgba(34, 197, 94, 0.25);
        }
        
        .badge-danger {
            background: rgba(239, 68, 68, 0.12);
            color: var(--danger);
            border: 1px solid rgba(239, 68, 68, 0.25);
        }
        
        .badge i { font-size: 5px; }
        
        /* Action Buttons */
        .action-btns { display: flex; gap: 6px; }
        
        .action-btn {
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--bg-secondary);
            border: 1px solid var(--border-primary);
            border-radius: 6px;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 12px;
        }
        
        .action-btn:hover {
            border-color: var(--text-muted);
            color: var(--text-primary);
            transform: translateY(-1px);
            box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        }
        
        .action-btn.download:hover {
            border-color: var(--success);
            color: var(--success);
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 50px 20px;
        }
        
        .empty-state i {
            font-size: 40px;
            color: var(--border-secondary);
            margin-bottom: 12px;
        }
        
        .empty-state p {
            color: var(--text-muted);
            font-size: 13px;
        }
        
        .no-results {
            text-align: center;
            padding: 30px;
            color: var(--text-muted);
            font-size: 13px;
        }
        
        /* Toast */
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            display: none;
            align-items: center;
            gap: 10px;
            padding: 14px 20px;
            background: linear-gradient(145deg, #ffffff, #e0e0e0);
            color: #000000;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            box-shadow: 0 10px 40px rgba(0,0,0,0.4), 0 0 20px rgba(255,255,255,0.1);
            z-index: 1000;
        }
        
        .toast.show { display: flex; animation: toastIn 0.3s ease; }
        .toast.error { background: linear-gradient(145deg, #ef4444, #dc2626); color: white; }
        
        @keyframes toastIn {
            from { opacity: 0; transform: translateY(15px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Loading */
        .loading-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.85);
            align-items: center;
            justify-content: center;
            z-index: 2000;
        }
        
        .loading-overlay.show { display: flex; }
        
        .spinner {
            width: 44px;
            height: 44px;
            border: 3px solid var(--border-secondary);
            border-top-color: var(--text-primary);
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
            box-shadow: 0 0 25px rgba(255,255,255,0.1);
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-primary); }
        ::-webkit-scrollbar-thumb { background: var(--border-secondary); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
    </style>
</head>
<body>
    <div class="bg-gradient"></div>
    
    <div class="container">
        <!-- Compact Header -->
        <header class="header">
            <div class="header-left">
                <div class="logo">
                    <i class="fas fa-shield-halved"></i>
                </div>
                <div class="header-title">
                    <h1>License Manager</h1>
                    <p>JD MT5 Trade Copier</p>
                </div>
            </div>
            <div class="stats-row">
                <div class="stat-mini">
                    <span class="value" id="totalLicenses">0</span>
                    <span class="label">Total</span>
                </div>
                <div class="stat-mini">
                    <span class="value" id="activeLicenses">0</span>
                    <span class="label">Active</span>
                </div>
                <div class="stat-mini">
                    <span class="value" id="expiredLicenses">0</span>
                    <span class="label">Expired</span>
                </div>
            </div>
        </header>
        
        <div class="main-grid">
            <!-- Create License Form -->
            <div class="card">
                <div class="card-header">
                    <div class="card-header-icon">
                        <i class="fas fa-plus"></i>
                    </div>
                    <h2>Generate License</h2>
                </div>
                <div class="card-body">
                    <form id="licenseForm">
                        <div class="form-group">
                            <label class="form-label">Client Name</label>
                            <div class="input-glow">
                                <input type="text" class="form-control" id="clientName" placeholder="Enter client or company name" required>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">Duration</label>
                            <div class="duration-quick">
                                <div class="duration-btn" data-days="30">
                                    <span class="num">30</span>
                                    <span class="txt">Days</span>
                                </div>
                                <div class="duration-btn" data-days="90">
                                    <span class="num">90</span>
                                    <span class="txt">Days</span>
                                </div>
                                <div class="duration-btn" data-days="180">
                                    <span class="num">180</span>
                                    <span class="txt">Days</span>
                                </div>
                                <div class="duration-btn" data-days="365">
                                    <span class="num">365</span>
                                    <span class="txt">Days</span>
                                </div>
                            </div>
                            <div class="date-range-box">
                                <div class="date-range-row">
                                    <div class="date-input-group">
                                        <label>Start Date</label>
                                        <input type="date" class="date-input" id="startDate">
                                    </div>
                                    <span class="date-separator"><i class="fas fa-arrow-right"></i></span>
                                    <div class="date-input-group">
                                        <label>End Date</label>
                                        <input type="date" class="date-input" id="expiryDate" required>
                                    </div>
                                </div>
                                <div class="duration-display">
                                    Duration: <strong id="durationDays">30</strong> days
                                </div>
                            </div>
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label class="form-label">Max Pairs</label>
                                <div class="input-glow">
                                    <input type="number" class="form-control" id="maxPairs" value="5" min="1" max="100">
                                </div>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Max Children</label>
                                <div class="input-glow">
                                    <input type="number" class="form-control" id="maxChildren" value="10" min="1" max="100">
                                </div>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">HWID Binding (Optional)</label>
                            <div class="hwid-row">
                                <div class="input-glow" style="flex:1;">
                                    <input type="text" class="form-control" id="hwidBinding" placeholder="Leave empty for universal" maxlength="16">
                                </div>
                                <button type="button" class="btn btn-secondary btn-icon" onclick="showHwidHelp()" title="Help">
                                    <i class="fas fa-question"></i>
                                </button>
                            </div>
                        </div>
                        
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-key"></i> Generate License
                        </button>
                    </form>
                    
                    <div class="result-card" id="resultCard">
                        <div class="result-header">
                            <i class="fas fa-check-circle"></i>
                            <span>License Generated</span>
                        </div>
                        <div class="result-body">
                            <div class="result-row">
                                <span class="result-label">Client</span>
                                <span class="result-value" id="resultClient">—</span>
                            </div>
                            <div class="result-row">
                                <span class="result-label">License Key</span>
                                <span class="result-value" id="resultKey">—</span>
                            </div>
                            <div class="result-row">
                                <span class="result-label">Expires</span>
                                <span class="result-value" id="resultExpiry">—</span>
                            </div>
                            <div class="result-row">
                                <span class="result-label">Limits</span>
                                <span class="result-value" id="resultLimits">—</span>
                            </div>
                        </div>
                        <div class="result-actions">
                            <button class="btn btn-secondary" onclick="downloadLicense()">
                                <i class="fas fa-download"></i> Download
                            </button>
                            <button class="btn btn-secondary" onclick="openLicenseFolder()">
                                <i class="fas fa-folder-open"></i> Folder
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- License Records -->
            <div class="card">
                <div class="card-header">
                    <div class="card-header-icon">
                        <i class="fas fa-list"></i>
                    </div>
                    <h2>License Records</h2>
                </div>
                
                <div class="filters-section">
                    <div class="filters-row">
                        <div class="filter-group search">
                            <input type="text" class="filter-control" id="searchFilter" placeholder="Search client...">
                        </div>
                        <div class="filter-group">
                            <input type="date" class="filter-control" id="dateFilter">
                        </div>
                        <button class="filter-btn active" data-filter="all" onclick="setStatusFilter('all')">All</button>
                        <button class="filter-btn" data-filter="active" onclick="setStatusFilter('active')">Active</button>
                        <button class="filter-btn" data-filter="expired" onclick="setStatusFilter('expired')">Expired</button>
                    </div>
                </div>
                
                <div id="licenseHistory">
                    <div class="empty-state">
                        <i class="fas fa-file-shield"></i>
                        <p>No licenses generated yet</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="loading-overlay" id="loading">
        <div class="spinner"></div>
    </div>
    
    <div class="toast" id="toast">
        <i class="fas fa-check"></i>
        <span id="toastMessage"></span>
    </div>
    
    <script>
        let lastCreatedFile = '';
        let allLicenses = [];
        let currentStatusFilter = 'all';
        
        // Initialize dates
        const today = new Date();
        const startDate = document.getElementById('startDate');
        const expiryDate = document.getElementById('expiryDate');
        
        startDate.value = today.toISOString().split('T')[0];
        const endDate = new Date(today);
        endDate.setDate(endDate.getDate() + 30);
        expiryDate.value = endDate.toISOString().split('T')[0];
        
        updateDurationDisplay();
        
        // Date change handlers
        startDate.addEventListener('change', updateDurationDisplay);
        expiryDate.addEventListener('change', updateDurationDisplay);
        
        function updateDurationDisplay() {
            const start = new Date(startDate.value);
            const end = new Date(expiryDate.value);
            const diffTime = end - start;
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            document.getElementById('durationDays').textContent = diffDays > 0 ? diffDays : 0;
        }
        
        // Duration quick buttons
        document.querySelectorAll('.duration-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.duration-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                const days = parseInt(this.dataset.days);
                const start = new Date();
                const end = new Date();
                end.setDate(end.getDate() + days);
                startDate.value = start.toISOString().split('T')[0];
                expiryDate.value = end.toISOString().split('T')[0];
                updateDurationDisplay();
            });
        });
        
        // Search & filter
        document.getElementById('searchFilter').addEventListener('input', filterLicenses);
        document.getElementById('dateFilter').addEventListener('change', filterLicenses);
        
        function setStatusFilter(status) {
            currentStatusFilter = status;
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.filter === status);
            });
            filterLicenses();
        }
        
        function filterLicenses() {
            const searchTerm = document.getElementById('searchFilter').value.toLowerCase();
            const dateFilter = document.getElementById('dateFilter').value;
            const todayStr = new Date().toISOString().split('T')[0];
            
            let filtered = allLicenses.filter(lic => {
                if (searchTerm && !lic.client_name.toLowerCase().includes(searchTerm)) return false;
                if (dateFilter && lic.expiry_date !== dateFilter) return false;
                const isExpired = lic.expiry_date < todayStr;
                if (currentStatusFilter === 'active' && isExpired) return false;
                if (currentStatusFilter === 'expired' && !isExpired) return false;
                return true;
            });
            
            renderLicenseTable(filtered);
        }
        
        function renderLicenseTable(licenses) {
            const todayStr = new Date().toISOString().split('T')[0];
            
            if (licenses.length === 0) {
                document.getElementById('licenseHistory').innerHTML = '<div class="no-results"><i class="fas fa-search" style="display:block;font-size:20px;margin-bottom:8px;color:#333;"></i>No matches found</div>';
                return;
            }
            
            let html = '<div class="table-wrapper"><table class="data-table"><thead><tr>';
            html += '<th>Client</th><th>Key</th><th>Expiry</th><th>Status</th><th></th>';
            html += '</tr></thead><tbody>';
            
            licenses.forEach(lic => {
                const isExpired = lic.expiry_date < todayStr;
                const filename = lic.file_path.split('\\\\').pop().split('/').pop();
                
                html += '<tr>';
                html += '<td class="client-name">' + lic.client_name + '</td>';
                html += '<td><span class="license-key">' + lic.license_key + '</span></td>';
                html += '<td class="date-cell">' + lic.expiry_date + '</td>';
                html += '<td><span class="badge ' + (isExpired ? 'badge-danger' : 'badge-success') + '">';
                html += '<i class="fas fa-circle"></i>' + (isExpired ? 'Expired' : 'Active') + '</span></td>';
                html += '<td><div class="action-btns">';
                html += '<button class="action-btn download" onclick="window.location.href=\\'/api/download/' + filename + '\\'" title="Download"><i class="fas fa-download"></i></button>';
                html += '<button class="action-btn" onclick="copyKey(\\'' + lic.license_key + '\\')" title="Copy"><i class="fas fa-copy"></i></button>';
                html += '</div></td></tr>';
            });
            
            html += '</tbody></table></div>';
            document.getElementById('licenseHistory').innerHTML = html;
        }
        
        function copyKey(key) {
            navigator.clipboard.writeText(key);
            showToast('Key copied!');
        }
        
        // Form submit
        document.getElementById('licenseForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            document.getElementById('loading').classList.add('show');
            
            const hwidValue = document.getElementById('hwidBinding').value.trim().toUpperCase();
            
            const data = {
                client_name: document.getElementById('clientName').value,
                expiry_date: document.getElementById('expiryDate').value,
                max_pairs: parseInt(document.getElementById('maxPairs').value),
                max_children: parseInt(document.getElementById('maxChildren').value),
                hwid_binding: hwidValue.length === 16 ? hwidValue : null
            };
            
            try {
                const response = await fetch('/api/create-license', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                setTimeout(() => {
                    document.getElementById('loading').classList.remove('show');
                    
                    if (result.success) {
                        lastCreatedFile = result.filename;
                        document.getElementById('resultClient').textContent = result.client_name;
                        document.getElementById('resultKey').textContent = result.license_key;
                        document.getElementById('resultExpiry').textContent = result.expiry_date;
                        document.getElementById('resultLimits').textContent = result.max_pairs + ' / ' + result.max_children;
                        document.getElementById('resultCard').classList.add('show');
                        
                        showToast('License generated!');
                        loadHistory();
                        
                        document.getElementById('clientName').value = '';
                        document.getElementById('hwidBinding').value = '';
                    } else {
                        showToast(result.error, true);
                    }
                }, 500);
            } catch (err) {
                document.getElementById('loading').classList.remove('show');
                showToast('Failed to create', true);
            }
        });
        
        function downloadLicense() {
            if (lastCreatedFile) {
                window.location.href = '/api/download/' + lastCreatedFile;
                showToast('Downloading...');
            }
        }
        
        function openLicenseFolder() {
            fetch('/api/open-folder');
            showToast('Opening folder...');
        }
        
        function showToast(message, isError = false) {
            const toast = document.getElementById('toast');
            document.getElementById('toastMessage').textContent = message;
            toast.className = 'toast show' + (isError ? ' error' : '');
            toast.querySelector('i').className = isError ? 'fas fa-times-circle' : 'fas fa-check-circle';
            setTimeout(() => toast.classList.remove('show'), 2500);
        }
        
        function showHwidHelp() {
            alert('HWID Binding\\n\\nBind to specific hardware.\\nGet: wmic baseboard get serialnumber\\n\\nLeave empty for universal.');
        }
        
        async function loadHistory() {
            try {
                const response = await fetch('/api/licenses');
                allLicenses = await response.json();
                
                const todayStr = new Date().toISOString().split('T')[0];
                const active = allLicenses.filter(l => l.expiry_date >= todayStr).length;
                const expired = allLicenses.length - active;
                
                document.getElementById('totalLicenses').textContent = allLicenses.length;
                document.getElementById('activeLicenses').textContent = active;
                document.getElementById('expiredLicenses').textContent = expired;
                
                allLicenses = allLicenses.reverse();
                
                if (allLicenses.length === 0) {
                    document.getElementById('licenseHistory').innerHTML = '<div class="empty-state"><i class="fas fa-file-shield"></i><p>No licenses yet</p></div>';
                    return;
                }
                
                filterLicenses();
            } catch (err) {
                console.error(err);
            }
        }
        
        loadHistory();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/create-license', methods=['POST'])
def api_create_license():
    try:
        data = request.json
        hwid = data.get('hwid_binding')
        if hwid and len(hwid) != 16:
            hwid = None
        result = create_license_bat(
            client_name=data['client_name'],
            expiry_date=data['expiry_date'],
            max_pairs=data.get('max_pairs', 5),
            max_children=data.get('max_children', 10),
            hwid_binding=hwid
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/licenses')
def api_get_licenses():
    return jsonify(load_license_records())

@app.route('/api/download/<filename>')
def api_download(filename):
    filepath = os.path.join(LICENSES_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return "File not found", 404

@app.route('/api/open-folder')
def api_open_folder():
    import subprocess
    if sys.platform == 'win32':
        subprocess.Popen(f'explorer "{LICENSES_DIR}"')
    return jsonify({"success": True})

def main():
    print("\n" + "=" * 45)
    print("  License Management System")
    print("=" * 45)
    print(f"\n  URL: http://127.0.0.1:5001")
    print(f"  Licenses: {LICENSES_DIR}")
    print("\n  Press Ctrl+C to stop")
    print("=" * 45 + "\n")
    
    import webbrowser
    import threading
    threading.Timer(1.5, lambda: webbrowser.open('http://127.0.0.1:5001')).start()
    
    app.run(host='127.0.0.1', port=5001, debug=False)

if __name__ == '__main__':
    main()
