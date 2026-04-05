"""
Test Script - Verify Firebase Connection and Configuration
Run this before launching the main application to diagnose issues
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Check if all required packages are installed."""
    required_packages = {
        'customtkinter': 'customtkinter',
        'firebase_admin': 'firebase-admin',
        'pywhatkit': 'pywhatkit',
    }
    
    print("\n📦 Checking Dependencies...")
    print("-" * 50)
    
    missing = []
    for module_name, package_name in required_packages.items():
        try:
            __import__(module_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} - NOT INSTALLED")
            missing.append(package_name)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print(f"\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    print("\n✅ All dependencies installed!")
    return True


def check_firebase_credentials():
    """Check if Firebase credentials file exists and is valid."""
    print("\n🔐 Checking Firebase Credentials...")
    print("-" * 50)
    
    from config import FIREBASE_CREDENTIALS_PATH
    
    if not FIREBASE_CREDENTIALS_PATH.exists():
        print(f"❌ Firebase credentials not found!")
        print(f"   Expected location: {FIREBASE_CREDENTIALS_PATH}")
        print(f"\n   How to get credentials:")
        print(f"   1. Go to Firebase Console (console.firebase.google.com)")
        print(f"   2. Click ⚙️ Project Settings")
        print(f"   3. Go to 'Service Accounts' tab")
        print(f"   4. Click 'Generate New Private Key'")
        print(f"   5. Save the JSON file as: {FIREBASE_CREDENTIALS_PATH}")
        return False
    
    print(f"✅ Found: {FIREBASE_CREDENTIALS_PATH}")
    
    # Try to parse JSON
    import json
    try:
        with open(FIREBASE_CREDENTIALS_PATH) as f:
            creds = json.load(f)
            
            required_fields = ['type', 'project_id', 'private_key']
            missing_fields = [f for f in required_fields if f not in creds]
            
            if missing_fields:
                print(f"❌ Invalid credentials - missing: {missing_fields}")
                return False
            
            print(f"✅ Valid Firebase credentials JSON")
            print(f"   Project ID: {creds.get('project_id')}")
            return True
    
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in credentials file!")
        return False
    
    except Exception as e:
        print(f"❌ Error reading credentials: {e}")
        return False


def test_firebase_connection():
    """Test actual Firebase connection."""
    print("\n🔌 Testing Firebase Connection...")
    print("-" * 50)
    
    try:
        from database import FirebaseDatabase
        
        db = FirebaseDatabase()
        
        if not db.db:
            print("❌ Failed to initialize Firebase")
            return False
        
        print("✅ Firebase initialized successfully")
        
        # Try to read one contact
        try:
            contacts = db.get_all_contacts()
            print(f"✅ Successfully read from Firestore ({len(contacts)} contacts)")
            
            if len(contacts) > 0:
                sample = contacts[0]
                print(f"   Sample contact: {sample.get('name')} ({sample.get('phone')})")
            
            return True
        
        except Exception as e:
            print(f"❌ Error reading from Firestore: {e}")
            print(f"\n   Check Firebase Firestore Rules:")
            print(f"   1. Go to Firestore Console")
            print(f"   2. Click 'Rules' tab")
            print(f"   3. Update rules to allow read access:")
            print(f"      allow read, write: if true; // for testing only!")
            return False
    
    except Exception as e:
        print(f"❌ Firebase connection error: {e}")
        return False


def check_whatsapp_web():
    """Check WhatsApp Web accessibility (manual)."""
    print("\n💬 WhatsApp Web Check...")
    print("-" * 50)
    print("⚠️  Manual check required")
    print("\n   1. Open https://web.whatsapp.com in your browser")
    print("   2. Login or scan QR code with phone")
    print("   3. Keep browser open while testing")
    print("   4. If you see 'WhatsApp' interface, you're ready!")
    
    response = input("\n   Is WhatsApp Web accessible? (yes/no): ").lower().strip()
    return response in ['yes', 'y']


def check_python_version():
    """Check Python version."""
    print("\n🐍 Checking Python Version...")
    print("-" * 50)
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version_str} - Need 3.8 or higher!")
        return False
    
    print(f"✅ Python {version_str}")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 50)
    print("  CRM WhatsApp Sender - Diagnostic Test")
    print("=" * 50)
    
    tests = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Firebase Credentials", check_firebase_credentials),
        ("Firebase Connection", test_firebase_connection),
        ("WhatsApp Web", check_whatsapp_web),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ Error running test: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("  Test Summary")
    print("=" * 50)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("✅ All checks passed! You can now run:")
        print("\n   python main.py\n")
        return 0
    else:
        failed = [name for name, passed in results.items() if not passed]
        print(f"❌ Some checks failed: {', '.join(failed)}")
        print("\nPlease fix the issues above and try again.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
