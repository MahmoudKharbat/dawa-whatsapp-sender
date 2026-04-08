# Configuration and Constants
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def _app_base_dir() -> Path:
    """Folder containing the .exe when frozen (PyInstaller), else the project directory."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _bundle_dir() -> Path:
    """PyInstaller one-file extraction dir, or project dir in development."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


PROJECT_ROOT = _app_base_dir()
load_dotenv(PROJECT_ROOT / ".env")

# Bundled assets (e.g. logo.png added via PyInstaller --add-data)
BUNDLE_DIR = _bundle_dir()
LOGO_PATH = BUNDLE_DIR / "logo.png"
WHATSAPP_SESSION_DIR = PROJECT_ROOT / "whatsapp_session"
LOG_FILE_PATH = PROJECT_ROOT / "crm_whatsapp.log"

# Application version (shown on login screen, etc.)
APP_VERSION = "1.0.1"

# Firebase Configuration
_firebase_credentials_env = os.getenv("FIREBASE_CREDENTIALS_PATH", "").strip()
if _firebase_credentials_env:
    FIREBASE_CREDENTIALS_PATH = Path(_firebase_credentials_env).expanduser()
else:
    default_credentials = PROJECT_ROOT / "serviceAccountKey.json"  # beside .exe when packaged
    if default_credentials.exists():
        FIREBASE_CREDENTIALS_PATH = default_credentials
    else:
        detected_admin_keys = sorted(PROJECT_ROOT.glob("*firebase-adminsdk*.json"))
        FIREBASE_CREDENTIALS_PATH = (
            detected_admin_keys[0] if detected_admin_keys else default_credentials
        )
FIRESTORE_COLLECTION = "contacts"
FIRESTORE_MESSAGES_COLLECTION = "messages"
FIRESTORE_USERS_COLLECTION = "users"

# UI Constants
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 750
WINDOW_TITLE = "مرسل واتساب الدعوة"

# Colors (Modern Dark Theme)
BG_COLOR = "#1e1e1e"
FG_COLOR = "#ffffff"
ACCENT_COLOR = "#51dc85"  # WhatsApp Green
SECONDARY_COLOR = "#2d2d2d"
BORDER_COLOR = "#3d3d3d"
DANGER_COLOR = "#e74c3c"
SUCCESS_COLOR = "#27ae60"

# WhatsApp Sending
MIN_DELAY = 5   # Minimum delay in seconds between messages
MAX_DELAY = 10  # Maximum delay in seconds between messages

# WhatsApp Web (Selenium): extra time for the app to open and each chat to load
WHATSAPP_LOGIN_TIMEOUT_SEC = 120  # max seconds to wait for main UI (#side) after opening web.whatsapp.com
WHATSAPP_INITIAL_PAGE_PAUSE_SEC = 10  # pause after first navigation so Chrome/WhatsApp can settle
WHATSAPP_CHAT_NAV_PAUSE_SEC = 8  # pause after each /send?phone=... load before looking for composer/send
WHATSAPP_COMPOSER_WAIT_SEC = 40  # max wait for message box after opening a chat
WHATSAPP_SEND_BUTTON_WAIT_SEC = 20  # max wait for send control after composer is ready
WHATSAPP_IMAGE_PREVIEW_WAIT_SEC = 8  # wait after choosing file until preview/send is ready
# After clicking send on media, wait until preview clears (blob thumb gone) before counting success
WHATSAPP_MEDIA_SEND_CONFIRM_TIMEOUT_SEC = 45
WHATSAPP_MEDIA_POST_CLEAR_HOLD_SEC = 5  # extra stable time after preview disappears (upload pipeline)

# UI Sizing
HEADER_HEIGHT = 80
FOOTER_HEIGHT = 120
CONTACT_ROW_HEIGHT = 45

# Font Sizes
FONT_LARGE = 16
FONT_MEDIUM = 14
FONT_SMALL = 12

# Environment Variables
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
