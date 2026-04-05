"""
Firebase/Firestore Database Logic
Handles all CRUD operations with Firestore
"""

import base64
import logging
from typing import List, Dict, Optional

import bcrypt
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

from auth_roles import VALID_ROLES, normalize_username
from config import (
    FIREBASE_CREDENTIALS_PATH,
    FIRESTORE_COLLECTION,
    FIRESTORE_MESSAGES_COLLECTION,
    FIRESTORE_USERS_COLLECTION,
)

logger = logging.getLogger(__name__)


class FirebaseDatabase:
    """Manages Firebase/Firestore connections and operations."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one database connection."""
        if cls._instance is None:
            cls._instance = super(FirebaseDatabase, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.db = None
        self.initialize()
    
    def initialize(self) -> bool:
        """
        Initialize Firebase connection.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not FIREBASE_CREDENTIALS_PATH.exists():
                logger.error(f"Firebase credentials file not found: {FIREBASE_CREDENTIALS_PATH}")
                return False
            
            # Initialize Firebase only if not already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(str(FIREBASE_CREDENTIALS_PATH))
                firebase_admin.initialize_app(cred)
            
            self.db = firestore.client()
            logger.info("Firebase initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            return False
    
    def get_all_contacts(self) -> List[Dict]:
        """
        Fetch all contacts from Firestore.
        
        Returns:
            List[Dict]: List of contact dictionaries
        """
        try:
            docs = self.db.collection(FIRESTORE_COLLECTION).stream()
            contacts = []
            
            for doc in docs:
                raw_contact = doc.to_dict() or {}
                contact = self._normalize_contact(raw_contact)
                contact['id'] = doc.id
                contacts.append(contact)
            
            logger.info(f"Fetched {len(contacts)} contacts from Firestore")
            return contacts
        
        except Exception as e:
            logger.error(f"Error fetching contacts: {e}")
            return []
    
    def get_contact_by_id(self, contact_id: str) -> Optional[Dict]:
        """
        Fetch a specific contact by ID.
        
        Args:
            contact_id: Document ID in Firestore
        
        Returns:
            Dict or None: Contact data with Firestore schema fields plus UI `id`
        """
        try:
            doc = self.db.collection(FIRESTORE_COLLECTION).document(contact_id).get()
            
            if doc.exists:
                raw_contact = doc.to_dict() or {}
                contact = self._normalize_contact(raw_contact)
                contact['id'] = doc.id
                return contact
            
            return None
        
        except Exception as e:
            logger.error(f"Error fetching contact {contact_id}: {e}")
            return None

    def _normalize_contact(self, contact: Dict) -> Dict:
        """
        Normalize contact payload from Firestore to the exact Firestore schema.
        Expected keys: first_name, father_name, last_name, phone, city, created_at, updated_at.
        """
        return {
            'first_name': str(contact.get('first_name', '')).strip(),
            'father_name': str(contact.get('father_name', '')).strip(),
            'last_name': str(contact.get('last_name', '')).strip(),
            'phone': str(contact.get('phone', '')).strip(),
            'city': str(contact.get('city', '')).strip(),
            'created_at': contact.get('created_at'),
            'updated_at': contact.get('updated_at'),
        }
    
    def add_contact(
        self,
        first_name: str,
        father_name: str,
        last_name: str,
        phone: str,
        city: str = ""
    ) -> Optional[str]:
        """
        Add a new contact to Firestore.
        
        Args:
            first_name: Contact first name
            father_name: Contact father name
            last_name: Contact last name
            phone: Contact phone number
            city: Contact city
        
        Returns:
            str or None: Document ID if successful, None otherwise
        """
        try:
            if not first_name or not last_name or not phone:
                logger.warning("First name, last name, and phone are required")
                return None

            data = {
                'first_name': first_name.strip(),
                'father_name': father_name.strip(),
                'last_name': last_name.strip(),
                'phone': phone.strip(),
                'city': city.strip(),
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
            }
            
            doc_ref = self.db.collection(FIRESTORE_COLLECTION).document()
            doc_ref.set(data)
            
            logger.info(f"Contact added: {first_name} {last_name} ({phone})")
            return doc_ref.id
        
        except Exception as e:
            logger.error(f"Error adding contact: {e}")
            return None
    
    def update_contact(
        self,
        contact_id: str,
        first_name: str,
        father_name: str,
        last_name: str,
        phone: str,
        city: str = ""
    ) -> bool:
        """
        Update an existing contact in Firestore.
        
        Args:
            contact_id: Document ID
            first_name: Updated first name
            father_name: Updated father name
            last_name: Updated last name
            phone: Updated phone number
            city: Updated city
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not first_name or not last_name or not phone:
                logger.warning("First name, last name, and phone are required")
                return False

            data = {
                'first_name': first_name.strip(),
                'father_name': father_name.strip(),
                'last_name': last_name.strip(),
                'phone': phone.strip(),
                'city': city.strip(),
                'updated_at': firestore.SERVER_TIMESTAMP,
            }
            
            self.db.collection(FIRESTORE_COLLECTION).document(contact_id).update(data)
            
            logger.info(f"Contact updated: {contact_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error updating contact {contact_id}: {e}")
            return False
    
    def delete_contact(self, contact_id: str) -> bool:
        """
        Delete a contact from Firestore.
        
        Args:
            contact_id: Document ID to delete
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.db.collection(FIRESTORE_COLLECTION).document(contact_id).delete()
            logger.info(f"Contact deleted: {contact_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting contact {contact_id}: {e}")
            return False
    
    def search_contacts(self, query: str) -> List[Dict]:
        """
        Search contacts by first name, father name, last name, phone, or city (client-side filtering).
        
        Args:
            query: Search string
        
        Returns:
            List[Dict]: Filtered contacts
        """
        try:
            all_contacts = self.get_all_contacts()
            query_lower = query.lower().strip()
            
            filtered = [
                c for c in all_contacts
                if query_lower in c.get('first_name', '').lower() or
                   query_lower in c.get('father_name', '').lower() or
                   query_lower in c.get('last_name', '').lower() or
                   query_lower in c.get('phone', '') or
                   query_lower in c.get('city', '').lower()
            ]
            
            return filtered
        
        except Exception as e:
            logger.error(f"Error searching contacts: {e}")
            return []

    def get_all_saved_messages(self) -> List[Dict]:
        """Fetch all saved message templates from Firestore (collection: messages)."""
        if not self.db:
            return []
        try:
            docs = self.db.collection(FIRESTORE_MESSAGES_COLLECTION).stream()
            messages: List[Dict] = []
            for doc in docs:
                data = doc.to_dict() or {}
                messages.append({
                    "id": doc.id,
                    "text": str(data.get("text", "")),
                    "created_at": data.get("created_at"),
                })

            def _sort_key(m: Dict) -> float:
                ts = m.get("created_at")
                if ts is None:
                    return 0.0
                try:
                    return float(ts.timestamp())
                except Exception:
                    return 0.0

            messages.sort(key=_sort_key, reverse=True)
            return messages
        except Exception as e:
            logger.error(f"Error fetching saved messages: {e}")
            return []

    def add_saved_message(self, text: str) -> Optional[str]:
        """Add a message template document: fields text, created_at."""
        if not self.db:
            return None
        body = (text or "").strip()
        if not body:
            return None
        try:
            doc_ref = self.db.collection(FIRESTORE_MESSAGES_COLLECTION).document()
            doc_ref.set({
                "text": body,
                "created_at": firestore.SERVER_TIMESTAMP,
            })
            logger.info("Saved message template to Firestore")
            return doc_ref.id
        except Exception as e:
            logger.error(f"Error saving message template: {e}")
            return None

    def delete_saved_message(self, message_id: str) -> bool:
        """Delete a message template by document id."""
        if not self.db:
            return False
        try:
            self.db.collection(FIRESTORE_MESSAGES_COLLECTION).document(message_id).delete()
            logger.info(f"Deleted saved message {message_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting saved message {message_id}: {e}")
            return False

    # --- Users (hashed passwords; never return password_hash to UI) ---

    @staticmethod
    def _hash_password(plain: str) -> str:
        raw = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())
        return base64.b64encode(raw).decode("ascii")

    @staticmethod
    def _verify_password(plain: str, stored_b64: str) -> bool:
        try:
            raw = base64.b64decode(stored_b64.encode("ascii"))
            return bcrypt.checkpw(plain.encode("utf-8"), raw)
        except Exception:
            return False

    def count_users(self) -> int:
        if not self.db:
            return 0
        try:
            return sum(1 for _ in self.db.collection(FIRESTORE_USERS_COLLECTION).stream())
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0

    def _count_admins(self) -> int:
        if not self.db:
            return 0
        try:
            q = self.db.collection(FIRESTORE_USERS_COLLECTION).where("role", "==", "Admin").stream()
            return sum(1 for _ in q)
        except Exception:
            return 0

    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Return {id, username, role} on success."""
        if not self.db:
            return None
        un = normalize_username(username)
        if not un or not password:
            return None
        try:
            docs = (
                self.db.collection(FIRESTORE_USERS_COLLECTION)
                .where("username", "==", un)
                .limit(1)
                .stream()
            )
            for doc in docs:
                data = doc.to_dict() or {}
                ph = str(data.get("password_hash", ""))
                if not ph or not self._verify_password(password, ph):
                    return None
                role = str(data.get("role", ""))
                if role not in VALID_ROLES:
                    return None
                try:
                    doc.reference.update({"last_login": firestore.SERVER_TIMESTAMP})
                except Exception as ex:
                    logger.warning("Could not update last_login for %s: %s", doc.id, ex)
                return {"id": doc.id, "username": data.get("username", un), "role": role}
            return None
        except Exception as e:
            logger.error(f"authenticate_user error: {e}")
            return None

    def get_all_users(self) -> List[Dict]:
        """List users without password fields."""
        if not self.db:
            return []
        try:
            out: List[Dict] = []
            for doc in self.db.collection(FIRESTORE_USERS_COLLECTION).stream():
                data = doc.to_dict() or {}
                out.append({
                    "id": doc.id,
                    "username": str(data.get("username", "")),
                    "role": str(data.get("role", "")),
                    "created_at": data.get("created_at"),
                    "last_login": data.get("last_login"),
                })
            out.sort(key=lambda u: u.get("username", "").lower())
            return out
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []

    def _username_taken(self, username: str, exclude_user_id: Optional[str] = None) -> bool:
        un = normalize_username(username)
        if not un:
            return True
        try:
            for doc in self.db.collection(FIRESTORE_USERS_COLLECTION).where("username", "==", un).limit(5).stream():
                if exclude_user_id and doc.id == exclude_user_id:
                    continue
                return True
            return False
        except Exception:
            return True

    def add_user(self, username: str, password: str, role: str) -> Optional[str]:
        if not self.db:
            return None
        un = normalize_username(username)
        if not un or not password or role not in VALID_ROLES:
            return None
        if self._username_taken(un):
            logger.warning("Username already exists")
            return None
        try:
            ref = self.db.collection(FIRESTORE_USERS_COLLECTION).document()
            ref.set({
                "username": un,
                "password_hash": self._hash_password(password),
                "role": role,
                "created_at": firestore.SERVER_TIMESTAMP,
            })
            logger.info(f"User created: {un}")
            return ref.id
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return None

    def update_user(
        self,
        user_id: str,
        username: Optional[str] = None,
        role: Optional[str] = None,
        new_password: Optional[str] = None,
    ) -> bool:
        if not self.db:
            return False
        try:
            ref = self.db.collection(FIRESTORE_USERS_COLLECTION).document(user_id)
            snap = ref.get()
            if not snap.exists:
                return False
            current = snap.to_dict() or {}
            current_role = str(current.get("role", ""))
            updates: Dict = {}

            if username is not None:
                un = normalize_username(username)
                if not un:
                    return False
                if self._username_taken(un, exclude_user_id=user_id):
                    return False
                updates["username"] = un

            if role is not None:
                if role not in VALID_ROLES:
                    return False
                if current_role == "Admin" and role != "Admin":
                    if self._count_admins() <= 1:
                        logger.warning("Cannot demote the last admin")
                        return False
                updates["role"] = role

            if new_password:
                if len(new_password) < 4:
                    return False
                updates["password_hash"] = self._hash_password(new_password)

            if not updates:
                return True
            updates["updated_at"] = firestore.SERVER_TIMESTAMP
            ref.update(updates)
            logger.info(f"User updated: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    def delete_user(self, user_id: str, acting_user_id: str) -> bool:
        if not self.db:
            return False
        if user_id == acting_user_id:
            logger.warning("Cannot delete own account")
            return False
        try:
            ref = self.db.collection(FIRESTORE_USERS_COLLECTION).document(user_id)
            snap = ref.get()
            if not snap.exists:
                return False
            data = snap.to_dict() or {}
            if str(data.get("role", "")) == "Admin" and self._count_admins() <= 1:
                logger.warning("Cannot delete the last admin")
                return False
            ref.delete()
            logger.info(f"User deleted: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False
