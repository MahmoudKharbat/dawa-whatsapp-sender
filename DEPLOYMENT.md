# Deployment Guide

Complete guide for building and distributing the Dawa WhatsApp Sender as an executable to your team.

## Overview

This guide covers:
1. Building standalone executables (.exe, .app, binary)
2. Creating installer packages
3. Distributing to team members
4. Setting up on end-user machines

## Prerequisites

- Target machine: Windows, macOS, or Linux
- Minimum requirements: 4GB RAM, 500MB disk space
- Internet connection for WhatsApp Web and Firestore

## Method 1: PyInstaller (Recommended)

### Windows (.exe File)

#### Step 1: Build Executable

```bash
# In project directory with venv activated
venv\Scripts\activate

pip install pyinstaller

# Build standalone exe
pyinstaller --name "Dawa WhatsApp Sender" ^
            --onefile ^
            --windowed ^
            --distpath=".\dist" ^
            --add-data "config.py:." ^
            --add-data "database.py:." ^
            --add-data "ui.py:." ^
            --add-data "whatsapp_sender.py:." ^
            main.py
```

Output: `dist/Dawa WhatsApp Sender.exe` (single file, ~200-300 MB)

#### Step 2: Build with Icon (Optional but Recommended)

1. Get icon (PNG or ICO format)
2. Build with icon:

```bash
pyinstaller --name "Dawa WhatsApp Sender" ^
            --onefile ^
            --windowed ^
            --icon="icon.ico" ^
            --distpath=".\dist" ^
            main.py
```

#### Step 3: Create Deployment Package

```
deployment/
├── Dawa WhatsApp Sender.exe
├── serviceAccountKey.json
├── SETUP_INSTRUCTIONS.txt
└── README.md
```

### macOS (.app File)

```bash
source venv/bin/activate

pip install pyinstaller

pyinstaller --name "Dawa WhatsApp Sender" \
            --onefile \
            --windowed \
            --icon="icon.icns" \
            main.py
```

Output: `dist/Dawa WhatsApp Sender.app`

To create a DMG installer:

```bash
# Install create-dmg
brew install create-dmg

# Create DMG
create-dmg "Dawa WhatsApp Sender.app" dist/

# Output: CRM WhatsApp Sender.dmg
```
## Distribution to Team

### Option 1: Direct File Distribution

#### For Windows:

1. Build .exe using PyInstaller
2. Place files in distribution folder:
   ```
   Dawa_WhatsApp_Deployment/
   ├── Dawa WhatsApp Sender.exe
   ├── serviceAccountKey.json
   ├── SETUP_INSTRUCTIONS.txt
   └── README.md
   ```
3. Zip folder
4. Share via email or cloud storage (Google Drive, OneDrive, etc.)

#### Setup Instructions (SETUP_INSTRUCTIONS.txt):

```
Dawa WhatsApp SENDER - TEAM SETUP GUIDE

Quick Setup (2 minutes):

1. Extract the ZIP file to your preferred location
   e.g., C:\Program Files\Dawa WhatsApp\

2. Double-click "Dawa WhatsApp Sender.exe" to launch application

3. Application first run:
   - Ensure you're logged into WhatsApp Web in your browser
   - Can test by adding a contact and sending a test message
   - Check system logs at: %APPDATA%\crm_whatsapp.log

```