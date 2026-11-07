# Dawa WhatsApp Sender

A modern desktop application built with Python for managing contacts and sending automated WhatsApp messages in bulk. Perfect for teams that need CRM capabilities with WhatsApp integration.

## Features

✨ **Modern UI**
- Clean, dark-mode desktop interface using customtkinter
- Responsive design (1000x750 window, resizable to 800x600 minimum)
- Real-time search and filtering by contact name or phone
- Intuitive contact management

📱 **Contact Management (CRM)**
- Add, edit, and delete contacts seamlessly
- Firestore integration for persistent cloud storage
- Real-time UI refresh on database changes

📤 **WhatsApp Bulk Messaging**
- Send messages to multiple selected contacts
- Randomized delays (10-20 seconds) between messages to avoid Meta bans
- Non-blocking threading to prevent UI freezing
- Real-time progress tracking and status updates
- Automatic browser tab cleanup

🔐 **Security & Reliability**
- Firebase authentication via service account key
- Structured logging for debugging
- Error handling and user-friendly error messages
- Contact validation before sending

## System Requirements

- **OS**: Windows, macOS, or Linux
- **Python**: 3.8 or higher
- **RAM**: Minimum 4GB
- **Disk Space**: 500MB (including dependencies)
- **Internet**: Required for Firestore and WhatsApp Web

## Installation

### 1. Clone or Extract Project

```bash
cd dawa-whatsapp-sender
```

### 2. Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- **customtkinter** - Modern desktop UI framework
- **firebase-admin** - Firebase/Firestore SDK
- **pywhatkit** - WhatsApp automation
- **PyInstaller** - For packaging to executable
- **python-dotenv** - Environment variable management

## Configuration

### Step 1: Set Up Firebase

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing one
3. Enable Firestore Database:
   - Click "Firestore Database" in left menu
   - Create database in production mode
   - Set rules to allow read/write (or set proper security rules)
4. Generate Service Account Key:
   - Click "Project Settings" (⚙️) at top
   - Go to "Service Accounts" tab
   - Click "Generate New Private Key"
   - Save the JSON file

### Step 2: Add Firebase Credentials

Place the downloaded `serviceAccountKey.json` file in the project root directory:

```
dawa-whatsapp-sender/
├── main.py
├── config.py
├── serviceAccountKey.json  ← Place here
├── requirements.txt
└── ...
```

### Step 3: Configure Environment (Optional)

```bash
cp .env.example .env
# Edit .env with your Firebase project ID
```

## Running the Application

### Development Mode

```bash
python main.py
```

The application window will open. You can now:
- Add contacts using the "+ Add Contact" button
- Search contacts by name or phone
- Select contacts and compose messages
- Send messages to selected contacts

### Important Notes on WhatsApp Sending

⚠️ **Browser Automation**
- When sending messages, pywhatkit will open your default web browser
- It will automatically:
  - Navigate to WhatsApp Web
  - Fill in the phone number
  - Type the message
  - Send it
  - Close the tab (with `tab_close=True`)
- **Be logged in**: Keep WhatsApp Web accessible. If not logged in, WhatsApp will show a QR code
- You'll need to scan QR on first use
- Consider keeping browser visible during sending or use headless mode (advanced)

⏱️ **Delay Strategy**
- Random 10-20 second delay between messages prevents Meta spam detection
- Helps maintain account health while sending bulk
- Messages send in a background thread (UI stays responsive)

## Project Structure

```
dawa-whatsapp-sender/
├── main.py                 # Entry point and main app class
├── config.py              # Configuration constants and settings
├── database.py            # Firestore database logic (CRUD)
├── whatsapp_sender.py     # WhatsApp automation with threading
├── ui.py                  # customtkinter UI components
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── serviceAccountKey.json # Firebase credentials (add this)
├── crm_whatsapp.log      # Auto-generated log file
└── README.md             # This file
```

## Application Architecture

### Components

**UI Layer (ui.py)**
- `ContactRow` - Individual contact display with checkbox
- `ContactListFrame` - Scrollable contact list
- `SearchBar` - Search and add contact controls
- `SelectionBar` - Master select/deselect and counter
- `MessagePanel` - Message composition and sending
- `AddEditContactModal` - Contact creation/editing dialog

**Business Logic (whatsapp_sender.py)**
- WhatsApp message sending with threading
- Automatic delays between messages
- Progress callbacks for UI updates
- Phone number formatting and validation

**Database Layer (database.py)**
- Firestore CRUD operations
- Search functionality
- Singleton pattern for connection pooling
- Error handling and logging

**Configuration (config.py)**
- UI constants (colors, sizes, fonts)
- Firebase paths
- WhatsApp settings
- Environment variables

## Troubleshooting

### Firebase Connection Error
- ✅ Verify `serviceAccountKey.json` exists in project root
- ✅ Check file is valid JSON (no corruption)
- ✅ Ensure Firestore database is created in Firebase Console
- ✅ Check internet connection

### WhatsApp Sending Issues

**"Failed to send" errors:**
- ✅ Ensure WhatsApp Web is accessible in your browser
- ✅ Log in to WhatsApp Web first (scan QR if needed)
- ✅ Check phone number format (must include country code: +1234567890)
- ✅ Verify browser hasn't blocked WhatsApp Web popups
- ✅ Check browser console for WhatsApp Web-specific errors

**Delay not working:**
- ✅ Verify `MIN_DELAY` and `MAX_DELAY` in config.py
- ✅ Check system time sync (affects delays)

**Chrome crashes on start (`DevToolsActivePort`, `session not created`):**
- ✅ Close all Chrome windows; only one process can use the `whatsapp_session` profile folder
- ✅ If Chrome is closed but it still fails, delete `whatsapp_session\SingletonLock` (Windows) when no `chrome.exe` is running
- ✅ Set `DAWA_CHROME_NO_SANDBOX=1` in `.env` or the environment, then restart the app
- ✅ Allow `chrome.exe` and `chromedriver.exe` in antivirus / Windows Smart App Control

### UI Not Showing
- ✅ Check Python version: `python --version` (3.8+)
- ✅ Verify customtkinter installed: `pip install customtkinter`
- ✅ Check for display server on Linux (X11/Wayland)

### High CPU Usage
- ✅ This is normal during active sending (pywhatkit uses browser)
- ✅ Check log file for hung processes: `crm_whatsapp.log`

## Packaging to Executable

Convert the Python script to a standalone .exe (Windows), .app (macOS), or binary (Linux).

### Windows (.exe)

```bash
# Activate virtual environment
venv\Scripts\activate

# Install additional dependencies
pip install --upgrade pywin32

# Build executable
pyinstaller --name "CRM WhatsApp Sender" `
            --onefile `
            --windowed `
            --icon=path/to/icon.ico `
            --add-data "serviceAccountKey.json:." `
            main.py

# Output: dist/CRM WhatsApp Sender.exe
```

### macOS (.app)

```bash
# Activate virtual environment
source venv/bin/activate

# Build app bundle
pyinstaller --name "CRM WhatsApp Sender" \
            --onefile \
            --windowed \
            --icon=path/to/icon.icns \
            --add-data "serviceAccountKey.json:." \
            main.py

# Output: dist/CRM WhatsApp Sender.app
```

### Linux (Binary)

```bash
# Activate virtual environment
source venv/bin/activate

# Build binary
pyinstaller --name "dawa-whatsapp-sender" \
            --onefile \
            --add-data "serviceAccountKey.json:." \
            main.py

# Output: dist/dawa-whatsapp-sender
chmod +x dist/dawa-whatsapp-sender
```

### Full Build Script (Windows)

Create `build.bat`:

```batch
@echo off
setlocal

echo ===== Building CRM WhatsApp Sender =====

if exist venv (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
)

echo Installing dependencies...
pip install -r requirements.txt --upgrade

echo Building executable...
pyinstaller --name "CRM WhatsApp Sender" ^
            --onefile ^
            --windowed ^
            --icon=icon.ico ^
            --add-data "serviceAccountKey.json:." ^
            --distpath=".\dist" ^
            --buildpath=".\build" ^
            --specpath=".\spec" ^
            main.py

echo.
echo ===== Build Complete! =====
echo Executable located at: dist\CRM WhatsApp Sender.exe
echo.
pause
```

Run with: `build.bat`

### Deployment Checklist

Before distributing to team:

- [ ] Test app on clean system without Python installed
- [ ] Verify all dependencies bundled
- [ ] Include updated `serviceAccountKey.json` (or instructions)
- [ ] Create quick start guide for team
- [ ] Test WhatsApp sending functionality
- [ ] Verify Firestore permissions are correct
- [ ] Check log file location is writable

## API Reference

### Database Operations

```python
from database import FirebaseDatabase

db = FirebaseDatabase()

# Get all contacts
contacts = db.get_all_contacts()

# Add contact
contact_id = db.add_contact(name="John Doe", phone="+1234567890")

# Update contact
success = db.update_contact(contact_id, name="Jane Doe", phone="+1234567891")

# Delete contact
success = db.delete_contact(contact_id)

# Search contacts
results = db.search_contacts("john")
```

### WhatsApp Sending

```python
from whatsapp_sender import WhatsAppSender

def on_progress(current, total, message):
    print(f"[{current}/{total}] {message}")

def on_complete(success, failed, errors):
    print(f"Sent: {success}, Failed: {failed}")

sender = WhatsAppSender(on_progress=on_progress, on_complete=on_complete)
sender.send_messages(["+1234567890", "+1234567891"], "Hello!")
```

## Configuration Options

Edit `config.py` to customize:

```python
# Window size
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 750

# WhatsApp delays (seconds)
MIN_DELAY = 10
MAX_DELAY = 20

# Colors (dark theme)
ACCENT_COLOR = "#25d366"  # WhatsApp green

# Font sizes
FONT_LARGE = 16
FONT_MEDIUM = 14
FONT_SMALL = 12
```

## Logging

Logs are stored in `crm_whatsapp.log` and printed to console:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Application started")
logger.warning("Low memory")
logger.error("Firebase connection failed")
```

Check log file to debug issues.

## Security Notes

🔒 **Important Security Practices**

1. **Never commit** `serviceAccountKey.json` to version control
2. Add to `.gitignore`:
   ```
   serviceAccountKey.json
   crm_whatsapp.log
   venv/
   __pycache__/
   .env
   ```
3. **Firestore Rules**: Set proper security rules in Firebase Console
   ```javascript
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /contacts/{document=**} {
         allow read, write: if request.auth != null;
       }
     }
   }
   ```
4. **WhatsApp Account**: Use a dedicated business account if possible
5. **Phone Numbers**: Ensure GDPR/privacy compliance before sending

## Limitations & Notes

⚠️ **Known Limitations**

- Requires WhatsApp Web access (not compatible with 2FA on some accounts)
- pywhatkit relies on browser automation (slower than API)
- Message delivery depends on internet connection
- WhatsApp may temporarily ban accounts sending too many messages
- Each contact needs international format (+CC...)

💡 **Future Improvements**

- Integration with WhatsApp Business API (for production)
- Scheduled message sending
- Template library for common messages
- Contact groups/segmentation
- Message history and analytics
- Automatic account management

## Support & Contribution

📧 For issues, bugs, or feature requests:
1. Check log files first (`crm_whatsapp.log`)
2. Verify Firebase and WhatsApp Web are working
3. Review troubleshooting section above
4. Check Python version and dependencies

## License

This project is provided as-is for business automation purposes.

## Disclaimer

This application uses WhatsApp Web browser automation. By using this tool:
- You accept responsibility for message content
- You comply with WhatsApp Terms of Service
- You ensure proper consent from message recipients
- You take responsibility for GDPR/privacy compliance
- Meta/WhatsApp may restrict or ban accounts sending bulk messages

Use responsibly and ethically.

---

**Version**: 1.0.0  
**Last Updated**: March 2026  
**Python**: 3.8+  
**Platform**: Windows, macOS, Linux
