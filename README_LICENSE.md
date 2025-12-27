# JD MT5 Trade Copier v2.0 - License Protected Edition

## Overview

This is a professionally licensed version of the MT5 Trade Copier with encrypted BAT file authentication. The license system replaces the previous user/password authentication with a simpler, more secure license-based access control.

---

## For Developers (Selling the Software)

### Generating Licenses

Use the `license_generator.py` tool to create license files for your clients:

```bash
# Interactive mode
python license_generator.py

# Command line mode
python license_generator.py --client "John Doe Trading" --days 30
python license_generator.py --client "ABC Corp" --date 2025-12-31 --pairs 10
```

#### License Generator Options:
- `--client NAME` - Client name/company
- `--days DAYS` - License duration in days
- `--date YYYY-MM-DD` - Specific expiry date
- `--pairs N` - Maximum copy pairs allowed (default: 5)
- `--children N` - Maximum children per pair (default: 10)

### License Files

Generated licenses are saved to the `licenses/` folder as `license_ClientName_XXXXXXXX.bat`

Each license contains:
- Encrypted client information
- Expiry date
- Usage limits (pairs, children)
- Tamper-proof checksum

### License Records

All generated licenses are tracked in `license_records.json` for your records.

---

## Building the EXE

### Prerequisites
1. Python 3.8+
2. All dependencies installed: `pip install -r requirements.txt`

### Build Process

```bash
# Run the build script
build.bat
```

Or manually:
```bash
pip install -r requirements.txt
pyinstaller JD_MT5_TradeCopier.spec --clean --noconfirm
```

### Distribution Package

After building, find the distribution package at:
```
dist\JD_MT5_TradeCopier_Distribution\
├── JD_MT5_TradeCopier.exe
├── data\
└── README.txt
```

---

## For Clients (Using the Software)

### Installation

1. **Standard Install (Recommended)**
   - Copy all files to a folder (e.g., `C:\MT5TradeCopier\`)
   - Place your `license_*.bat` file in the same folder
   - Double-click the license BAT file to start

2. **Program Files Install (Advanced)**
   - Run `install.bat` as Administrator
   - Copy your license file to `C:\Program Files\JD_MT5_TradeCopier\`
   - Use the desktop shortcut to run

### Starting the Application

1. Place your license file (`license_*.bat`) in the same folder as the EXE
2. Either:
   - Double-click the license BAT file, OR
   - Double-click `JD_MT5_TradeCopier.exe`
3. Your web browser will open automatically to the dashboard

### License Validation

- The application checks your license on every startup
- If license is expired, you'll see an expiry message
- Contact your provider to renew your license

---

## Security Features

### License Protection

- **AES-256 Encryption**: License data is encrypted using Fernet (AES)
- **Tamper Detection**: Checksums verify license integrity
- **Version Control**: Licenses are tied to software versions
- **Expiry Enforcement**: Automatic blocking after expiry date

### BAT File Protection

The license BAT file contains:
- Encrypted license data (not human-readable)
- Tamper-proof structure
- Self-launching capability

**Warning**: Modifying the license file will invalidate it.

---

## File Structure

```
JD_MT5_TradeCopier/
├── JD_MT5_TradeCopier.exe       # Main application
├── license_*.bat                 # Client license file
├── config.json                   # Copy pair configuration
├── data/                         # Runtime data
│   ├── shared_positions_*.bin   # Live position data
│   └── closed_trades_*.json     # Trade history
├── Templates/                    # Web UI templates
└── static/                       # CSS/JS assets
```

### Data Storage Locations

- **Windows**: `%LOCALAPPDATA%\JD_MT5_TradeCopier\`
  - `data/` - Encrypted application data
  - `logs/` - Activity logs

---

## Troubleshooting

### "No license file found"
- Ensure your `license_*.bat` file is in the same folder as the EXE
- The file must start with "license" and end with ".bat"

### "License expired"
- Your license has passed its expiry date
- Contact your provider for a renewal

### "License has been modified"
- The license file was edited or corrupted
- Request a new license file from your provider

### Application doesn't start
- Run from Command Prompt to see error messages
- Check that MetaTrader 5 is installed
- Ensure all required files are present

---

## Developer Files (Do NOT Distribute)

Keep these files private - they are for license generation only:

- `license_generator.py` - Creates new licenses
- `license_records.json` - Your license database
- `licenses/` folder - Generated license files
- `MASTER_SECRET` in the code - Your encryption key

---

## Support

For technical support or license renewals, contact your software provider.

---

**Version**: 2.0  
**License System**: BAT File Encryption v2.0  
**Last Updated**: December 2025
