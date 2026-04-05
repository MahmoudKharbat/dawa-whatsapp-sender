# Architecture & Development Notes

Technical documentation for developers maintaining or extending the Dawa WhatsApp Sender.

## Project Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────┐
│   Main Application (main.py)            │
│   - UI Management                       │
│   - Event Handling                      │
│   - State Management                    │
└──────────┬──────────┬───────────────────┘
           │          │
        ┌──▼──┐    ┌──▼──────────┐
        │  UI │    │  Business   │
        │Layer│    │  Logic      │
        └──┬──┘    └──┬─────┬────┘
           │          │     │
       ┌───▼────┐  ┌──▼──┐ ┌──▼─────────┐
       │ui.py   │  │db.  │ │whatsapp_   │
       │        │  │py   │ │sender.py   │
       │Custom  │  │     │ │            │
       │TKinter │  │Fire-│ │Threading & │
       │Widgets │  │store│ │pywhatkit   │
       └────────┘  │CRUD │ └────────────┘
                   └──┬──┘
                      │
                   ┌──▼───────┐
                   │Firestore  │
                   │Database   │
                   │(Contacts) │
                   └───────────┘
```

### Data Flow

1. **User Interaction** → Main.py event handler
2. **State Update** → Database (Firestore) or WhatsApp sender
3. **UI Update** → Contact list refreshed, status label updated
4. **Threading** → Long operations happen in background, UI stays responsive

### Module Responsibilities

| Module | Responsibility | Key Classes |
|--------|-----------------|------------|
| `main.py` | Application lifecycle, event orchestration | `DawaWhatsApp` |
| `ui.py` | UI components and layout | `ContactRow`, `ContactListFrame`, `SearchBar`, `MessagePanel` |
| `database.py` | Firebase/Firestore CRUD operations | `FirebaseDatabase` |
| `whatsapp_sender.py` | WhatsApp automation with threading | `WhatsAppSender` |
| `config.py` | Constants and configuration | Module-level constants |

## Design Patterns Used

### 1. Singleton Pattern (Database)

```python
class FirebaseDatabase:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**Why**: Ensures single database connection across entire application

### 2. Observer Pattern (Threading Callbacks)

```python
def __init__(self, on_progress=None, on_complete=None):
    self.on_progress = on_progress
    self.on_complete = on_complete

# Usage
whatsapp_sender.send_messages(phones, message)
# Callbacks fire during/after sending
```

**Why**: UI stays responsive while background tasks notify of progress

### 3. MVC Pattern (Implicit)

- **Model**: `database.py` (data layer)
- **View**: `ui.py` (UI components)
- **Controller**: `main.py` (event handlers and business logic)

## Class Hierarchy

### UI Components

```
CTkFrame (customtkinter base)
├── SearchBar
├── SelectionBar
├── ContactListFrame (CTkScrollableFrame)
│   └── ContactRow (added dynamically)
├── MessagePanel
└── AddEditContactModal (CTkToplevel)
```

### Custom Components

**ContactRow**
- Represents single contact in list
- Handles checkbox selection
- Provides edit/delete buttons
- Self-contained styling

**ContactListFrame**
- Container for multiple ContactRows
- Manages selection state
- Provides add/remove/select-all operations

**MessagePanel**
- Message input and sending
- Real-time status display
- Progress tracking

**AddEditContactModal**
- Modal dialog for contact creation/editing
- Form validation
- Save/Cancel operations

## Threading Model

```
Main Thread (UI)
    └─ WhatsAppSender.send_messages()
        └─ spawn: _send_messages_worker() [Background Thread]
            ├─ For each contact:
            │  ├─ Call on_progress() callback
            │  ├─ Send message via pywhatkit
            │  └─ Sleep with random delay
            └─ Call on_complete() callback
```

**Key Aspects**:
- Background thread is daemon (won't prevent app exit)
- Callbacks execute on main thread (UI-safe)
- is_sending flag prevents concurrent sends
- Random delays implemented with `random.randint()`

## Database Schema

### Firestore Collection: `contacts`

```
contacts/
├── <doc_id_1>/
│   ├── name: string
│   ├── phone: string
│   ├── (no email field)
│   ├── created_at: timestamp
│   └── updated_at: timestamp
└── <doc_id_2>/
    └── ...
```

**Indexes**: None required for basic usage. Create compound indexes if adding complex queries.

**Backup Strategy**: Firestore auto-backs up to Cloud Storage (check Console).

## Configuration System

### config.py Structure

```python
# UI Constants
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 750

# Firebase
FIREBASE_CREDENTIALS_PATH = Path(__file__).parent / "serviceAccountKey.json"

# WhatsApp timing
MIN_DELAY = 10
MAX_DELAY = 20

# Appearance
BG_COLOR = "#1e1e1e"
ACCENT_COLOR = "#25d366"
```

**Why**: Easy to customize without touching code logic

### Environment Variables (Optional)

```python
# In config.py
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")

# In .env
FIREBASE_PROJECT_ID=my-project-id
```

## Error Handling Strategy

### Database Errors
```python
try:
    result = self.db.collection(...).get()
except Exception as e:
    logger.error(f"Error fetching: {e}")
    return None
```

### WhatsApp Sending Errors
```python
try:
    kit.sendwhatmsg_instantly(...)
except Exception as e:
    failed_count += 1
    errors.append(str(e))
    # Continue to next contact
```

### UI Errors
```python
if not name or not phone:
    self._show_error("Name and phone required")
    return
```

**Approach**: Graceful degradation - app continues even if individual operations fail

## Logging System

### Configuration

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crm_whatsapp.log'),
        logging.StreamHandler()
    ]
)
```

### Log Levels Used

- `INFO` - Normal operations (contact loaded, message sent)
- `WARNING` - Skipped operations (empty phone, no contacts selected)
- `ERROR` - Failed operations (Firebase connection, send failures)

### Log Locations

- **File**: `crm_whatsapp.log` (in app directory)
- **Console**: Printed to terminal/cmd during development

## Security Considerations

### Credentials Management

```python
# ❌ WRONG - Never hardcode
FIREBASE_KEY = {
    "type": "service_account",
    ...
}

# ✅ CORRECT - Load from external file
cred = credentials.Certificate("serviceAccountKey.json")
```

### Firestore Security Rules

```javascript
// Recommended for team usage
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /contacts/{document=**} {
      // Only authenticated users can access
      allow read, write: if request.auth != null;
    }
  }
}
```

### Message Handling

- No logging of actual message content (privacy)
- No storing chat history (use contact metadata instead)
- Phone numbers validated but not encrypted

## Performance Considerations

### UI Responsiveness

**Problem**: Sending 100 messages would freeze UI if done on main thread

**Solution**: Threading
```python
threading.Thread(target=self._send_messages_worker, daemon=True).start()
```

### Database Queries

**Optimization**: Search happens client-side (in memory)
```python
def search_contacts(self, query):
    all_contacts = self.get_all_contacts()  # Ram cache
    return [c for c in all_contacts if query in c['name']]
```

For 10k+ contacts, would need:
- Pagination
- Server-side filtering (Firestore queries)
- Caching layer

### Memory Usage

- All contacts loaded into memory on startup (~10KB per contact)
- UI creates widget per contact (use virtualization for 1000+)

## Testing Recommendations

### Unit Tests

```python
# test_database.py
def test_add_contact():
    db = FirebaseDatabase()
    contact_id = db.add_contact("John", "+1234567890")
    assert contact_id is not None

def test_search_contacts():
    results = db.search_contacts("john")
    assert len(results) > 0
```

### Integration Tests

```python
def test_end_to_end():
    # Add contact
    contact_id = db.add_contact(...)
    # Update contact
    db.update_contact(...)
    # Send message (with mock)
    # Delete contact
    db.delete_contact(...)
```

### Manual Testing Checklist

- [ ] Add contact and send a message
- [ ] Edit contact details
- [ ] Delete contact (confirm dialog)
- [ ] Search by name and phone
- [ ] Send message to single contact
- [ ] Send to multiple selected
- [ ] Select/deselect all
- [ ] Message with special characters
- [ ] Firebase error handling
- [ ] WhatsApp Web not open
- [ ] Invalid phone numbers

## Future Enhancements

### Planned Features

1. **Message Templates**
   ```python
   # templates.py
   TEMPLATES = {
       "greeting": "Hello {name}!",
       "follow_up": "Following up on..."
   }
   ```

2. **Scheduled Sending**
   ```python
   from schedule import every, run_pending
   
   every().day.at("10:30").do(send_messages)
   ```

3. **Contact Groups**
   ```python
   # Database schema addition
   contacts/{id}:
       group_id: string
   ```

4. **Message History**
   ```python
   # New collection
   message_log/{id}:
       contact_id: string
       message: string
       sent_at: timestamp
       status: "sent" | "failed"
   ```

5. **WhatsApp Business API Integration**
   ```python
   # Use official API instead of web automation
   from twilio.rest import Client
   
   client = Client(account_sid, auth_token)
   client.messages.create(...)
   ```

### Code TODOs

Search codebase for comments:

```python
# TODO: Implement message templates
# TODO: Add scheduled sending feature
# TODO: Create backup/export functionality
```

## Dependency Management

### Current Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| customtkinter | 5.2.0 | Modern UI framework |
| firebase-admin | 6.1.0 | Firebase SDK |
| pywhatkit | 5.3 | WhatsApp automation |
| PyInstaller | 6.1.0 | Packaging to .exe/.app |
| python-dotenv | 1.0.0 | Environment variables |

### Potential Upgrades

```
# Check for updates
pip list --outdated

# Update all packages
pip install --upgrade -r requirements.txt
```

### Conflicting Dependencies

- None known as of v1.0
- pywhatkit requires older Selenium version (bundled)

## Build Optimization

### PyInstaller Performance

**Current build time**: ~30 seconds
**Binary size**: ~200-300 MB

**To reduce size**:
```bash
pyinstaller --onefile \
            --exclude-module=numpy \
            --exclude-module=matplotlib \
            main.py
```

**To reduce build time**:
- Skip rebuilding if files unchanged
- Use cache: `--bootloader-ignore-signals`

## Deployment Strategy

### Version Tagging

```
v1.0.0 - Initial release
v1.1.0 - Bug fixes + new features
v2.0.0 - Major rewrite (breaking changes)
```

### Release Checklist

- [ ] Update version in README
- [ ] Update CHANGELOG
- [ ] Test on Windows, Mac, Linux
- [ ] Build executables
- [ ] Create release notes
- [ ] Tag git commit
- [ ] Upload to release platform

## Monitoring & Maintenance

### Health Checks

```python
def health_check():
    # Verify Firebase connection
    db = FirebaseDatabase()
    if not db.db:
        return "Firebase: FAIL"
    
    # Verify WhatsApp Web accessibility
    # Note: Hard to automate, requires manual check
    
    return "OK"
```

### Metrics to Track

- Successful message sends (per user)
- Failed sends and error types
- Average send time per message
- Active users
- Firebase operation costs
- Application uptime

## Known Limitations

1. **pywhatkit Bottleneck**: 
   - Limited to ~1 message per 10-20 seconds
   - Not suitable for 1000+ daily message volume
   - Solution: Use WhatsApp Business API

2. **Browser Dependency**:
   - Requires WhatsApp Web accessible
   - Can't run on headless servers
   - Solution: Cloud browser instances (BrowserStack)

3. **No Built-in Security**:
   - No user authentication
   - No message encryption
   - Solution: Add OAuth2, add HTTPS

4. **UI Limitations**:
   - Doesn't handle 10k+ contacts well
   - Solution: Implement virtualization

## Code Style Guide

### Naming Conventions

```python
# Classes: PascalCase
class ContactListFrame: pass

# Functions/methods: snake_case
def add_contact(self): pass

# Constants: UPPER_SNAKE_CASE
MIN_DELAY = 10

# Private methods: _leading_underscore
def _on_send_click(self): pass

# UI callbacks: follow_event_pattern
def _on_contact_selection_changed(self): pass
```

### Documentation

```python
def search_contacts(self, query: str) -> List[Dict]:
    """
    Search contacts by name or phone number.
    
    Args:
        query: Search string (name or phone)
    
    Returns:
        List[Dict]: Filtered contacts with 'id', 'name', 'phone'
    
    Raises:
        Exception: If Firestore connection fails
    """
```

### Code Organization

```python
# Order in class:
# 1. __init__
# 2. Public methods (alphabetical)
# 3. Private methods (alphabetical)
# 4. Properties

class Example:
    def __init__(self): pass
    def add_item(self): pass
    def get_items(self): pass
    def _validate(self): pass
    @property
    def count(self): pass
```

## Debugging Tips

### Enable Verbose Logging

```python
# In config.py
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

### Print with Context

```python
import traceback

try:
    result = db.add_contact(...)
except Exception as e:
    logger.error(f"Failed to add contact: {e}")
    logger.debug(traceback.format_exc())
```

### Firestore Debug

```python
# Check what's in Firestore console
# See actual documents in:
# Firebase Console > Firestore Database > collections > contacts
```

### WhatsApp Debug

```python
# Check browser console (F12) for WhatsApp Web errors
# Check pywhatkit logs for automation issues
```

## References & Resources

- **customtkinter**: https://github.com/TomSchimansky/CustomTkinter
- **firebase-admin**: https://firebase.google.com/docs/database/admin/start
- **pywhatkit**: https://github.com/Shayneobrien/pywhatkit
- **PyInstaller**: https://pyinstaller.org/
- **WhatsApp Web**: https://web.whatsapp.com

---

**Last Updated**: March 2026  
**Maintainer**: Development Team  
**Version**: 1.0.0
