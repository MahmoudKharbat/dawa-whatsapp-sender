"""
Dawa WhatsApp Sender - Main Application
Complete desktop application for managing contacts and sending bulk WhatsApp messages
"""

import customtkinter as ctk
import logging
import sys
from typing import Optional, List, Dict, Callable
from pathlib import Path

from auth_roles import can_use_messaging, can_manage_users
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE,
    BG_COLOR, SECONDARY_COLOR, ACCENT_COLOR, FIREBASE_CREDENTIALS_PATH
)
from database import FirebaseDatabase
from whatsapp_sender import WhatsAppSender
from ui import (
    SearchBar,
    SelectionBar,
    ContactListFrame,
    MessagePanel,
    AddEditContactModal,
    LoginApp,
    UsersAdminPanel,
)


def _configure_stdio_utf8() -> None:
    """Avoid UnicodeEncodeError when logging Arabic on Windows (e.g. cp1255 console)."""
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        enc = getattr(stream, "encoding", None) or ""
        if enc.lower() in ("utf-8", "utf8"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


_configure_stdio_utf8()

# Configure logging (UTF-8 file + console so Arabic errors don't crash the logging stack)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crm_whatsapp.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
    force=True,
)
logger = logging.getLogger(__name__)


class DawaWhatsApp(ctk.CTk):
    """Main application class (shown after login)."""
    
    def __init__(
        self,
        current_user: Dict,
        on_logout: Optional[Callable[[], None]] = None,
    ):
        super().__init__()
        self.current_user = current_user
        self._on_logout = on_logout
        
        # Configure window
        self.title(f"{WINDOW_TITLE} — {current_user.get('username', '')}")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(800, 600)
        
        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        # Initialize components
        self.db = FirebaseDatabase()
        self.whatsapp_sender = WhatsAppSender(
            on_progress=self._on_send_progress,
            on_complete=self._on_send_complete
        )
        
        # Application state
        self.all_contacts: List[dict] = []
        self.filtered_contacts: List[dict] = []
        self.users_admin_panel: Optional[UsersAdminPanel] = None
        
        # Build UI
        self._build_ui()
        self._apply_role_messaging()

        # Check if Firebase is initialized
        if not self.db.db:
            logger.error("Failed to initialize Firebase. Please check serviceAccountKey.json")
            self.message_panel.update_status(
                "Firebase غير مُهيأ. أضف ملف serviceAccountKey.json ثم أعد تشغيل التطبيق.",
                "error"
            )
            # Show the detailed dialog after the window is rendered.
            self.after(100, self._show_firebase_error_dialog)
        else:
            # Load initial data
            self._load_contacts()
            if self.users_admin_panel:
                self.users_admin_panel.refresh()

        self.protocol("WM_DELETE_WINDOW", self._on_app_closing)
        
        logger.info("Application started successfully")

    def _on_app_closing(self):
        """Close GUI and release Chrome (sending intentionally leaves the browser open)."""
        self.whatsapp_sender.shutdown_browser()
        self.destroy()

    def _do_logout(self):
        """Return to login screen (main loop shows LoginApp again)."""
        self.whatsapp_sender.shutdown_browser()
        if self._on_logout:
            self._on_logout()
        self.destroy()
    
    def _build_ui(self):
        """Build the user interface."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.header_bar = ctk.CTkFrame(self, fg_color=BG_COLOR, height=70)
        self.header_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.header_bar.grid_columnconfigure(0, weight=1)
        self.search_bar = SearchBar(
            self.header_bar,
            on_search=self._on_search,
            on_add=self._on_add_contact,
            fg_color=SECONDARY_COLOR,
            height=70,
        )
        self.search_bar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        ctk.CTkButton(
            self.header_bar,
            text="تسجيل الخروج",
            width=118,
            height=36,
            font=("Arial", 12, "bold"),
            fg_color="#555555",
            hover_color="#666666",
            command=self._do_logout,
        ).grid(row=0, column=1, padx=(8, 12), pady=10, sticky="e")

        self.workspace = ctk.CTkFrame(self, fg_color=BG_COLOR)
        self.workspace.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 6))
        self.workspace.grid_rowconfigure(0, weight=1)
        self.workspace.grid_columnconfigure(0, weight=1)

        role = self.current_user.get("role", "")
        if can_manage_users(role):

            def _on_tab_changed():
                if self.users_admin_panel:
                    self.users_admin_panel.refresh()

            self.tabview = ctk.CTkTabview(self.workspace, command=_on_tab_changed)
            self.tabview.grid(row=0, column=0, sticky="nsew")
            tab_contacts = self.tabview.add("جهات الاتصال")
            tab_users = self.tabview.add("المستخدمون")
            self._build_contacts_column(tab_contacts)
            tab_users.grid_columnconfigure(0, weight=1)
            tab_users.grid_rowconfigure(0, weight=1)
            self.users_admin_panel = UsersAdminPanel(
                tab_users,
                on_list_users=lambda: self.db.get_all_users(),
                on_add_user=self._admin_add_user,
                on_update_user=self._admin_update_user,
                on_delete_user=self._admin_delete_user,
                current_user_id=self.current_user["id"],
                fg_color=BG_COLOR,
            )
            self.users_admin_panel.grid(row=0, column=0, sticky="nsew")
        else:
            host = ctk.CTkFrame(self.workspace, fg_color=BG_COLOR)
            host.grid(row=0, column=0, sticky="nsew")
            self._build_contacts_column(host)

        self.message_panel = MessagePanel(
            self,
            on_send=self._on_send_messages,
            on_list_saved_messages=self._list_saved_messages,
            on_save_saved_message=self._save_saved_message,
            on_delete_saved_message=self._delete_saved_message,
            fg_color=SECONDARY_COLOR,
            height=260,
        )
        self.message_panel.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

    def _build_contacts_column(self, parent: ctk.CTkFrame):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        self.selection_bar = SelectionBar(
            parent,
            on_select_all=self._on_select_all,
            on_deselect_all=self._on_deselect_all,
            fg_color=SECONDARY_COLOR,
            height=50,
        )
        self.selection_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 4))
        self.contact_list = ContactListFrame(parent, fg_color=BG_COLOR)
        self.contact_list.set_callbacks(
            on_select=self._on_contact_selection_changed,
            on_edit=self._on_edit_contact,
            on_delete=self._on_delete_contact,
            on_selection_limit=self._on_selection_limit_reached,
        )
        self.contact_list.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

    def _apply_role_messaging(self):
        """ContactManager: no bulk selection for send; slim status strip only (no compose)."""
        role = self.current_user.get("role", "")
        self.message_panel.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        if can_use_messaging(role):
            self.contact_list.set_selection_enabled(True)
            self.selection_bar.set_bulk_select_enabled(True)
            self.message_panel.set_messaging_ui_visible(True)
        else:
            self.contact_list.set_selection_enabled(False)
            self.selection_bar.set_bulk_select_enabled(False)
            self.message_panel.set_messaging_ui_visible(False)

    def _admin_add_user(self, username: str, password: str, role: str) -> bool:
        return self.db.add_user(username, password, role) is not None

    def _admin_update_user(
        self, user_id: str, username: str, role: str, new_password: Optional[str]
    ) -> bool:
        return self.db.update_user(
            user_id, username=username, role=role, new_password=new_password
        )

    def _admin_delete_user(self, user_id: str) -> bool:
        return self.db.delete_user(user_id, self.current_user["id"])
    
    def _load_contacts(self):
        """Load contacts from Firestore and refresh UI."""
        logger.info("Loading contacts from Firestore...")
        self.all_contacts = self.db.get_all_contacts()
        self.filtered_contacts = self.all_contacts.copy()
        self._refresh_contact_list()
        
        logger.info(f"Loaded {len(self.all_contacts)} contacts")

    def _list_saved_messages(self) -> List[dict]:
        """Load saved message templates from Firestore collection `messages`."""
        if not self.db.db:
            return []
        return self.db.get_all_saved_messages()

    def _save_saved_message(self, text: str) -> bool:
        """Persist current compose text to Firestore `messages`."""
        if not self.db.db:
            self.message_panel.update_status("Firebase غير متصل", "error")
            return False
        doc_id = self.db.add_saved_message(text)
        return doc_id is not None

    def _delete_saved_message(self, message_id: str) -> bool:
        """Remove a saved message template from Firestore."""
        if not self.db.db:
            return False
        return self.db.delete_saved_message(message_id)

    @staticmethod
    def _display_name(contact: dict) -> str:
        """Build a display name from Firestore first/father/last name fields."""
        first = str(contact.get("first_name", "")).strip()
        father = str(contact.get("father_name", "")).strip()
        last = str(contact.get("last_name", "")).strip()
        return " ".join([part for part in (first, father, last) if part]).strip()
    
    def _refresh_contact_list(self):
        """Refresh the contact list display."""
        self.contact_list.add_contacts(self.filtered_contacts)
        self.selection_bar.update_count(0, len(self.filtered_contacts))
    
    def _on_search(self, query: str):
        """Handle search input."""
        if not query.strip():
            self.filtered_contacts = self.all_contacts.copy()
        else:
            self.filtered_contacts = self.db.search_contacts(query)
        
        self._refresh_contact_list()
    
    def _on_add_contact(self):
        """Open add contact modal."""
        def on_save(contact_id: Optional[str], data: dict):
            # Validation feedback is handled inside the modal itself.
            if not data.get('first_name') or not data.get('last_name') or not data.get('phone'):
                return
            result = self.db.add_contact(
                first_name=data['first_name'],
                father_name=data['father_name'],
                last_name=data['last_name'],
                phone=data['phone'],
                city=data['city']
            )
            
            if result:
                logger.info(f"Contact added: {data['first_name']} {data['last_name']}".strip())
                self._load_contacts()  # Refresh
                self.message_panel.update_status("تمت إضافة جهة الاتصال بنجاح!", "success")
            else:
                self.message_panel.update_status("فشل إضافة جهة الاتصال", "error")
        
        AddEditContactModal(self, on_save=on_save)
    
    def _on_edit_contact(self, contact_id: str):
        """Open edit contact modal."""
        contact = next((c for c in self.all_contacts if c['id'] == contact_id), None)
        if not contact:
            return
        
        def on_save(cid: Optional[str], data: dict):
            # Validation feedback is handled inside the modal itself.
            if not data.get('first_name') or not data.get('last_name') or not data.get('phone'):
                return
            success = self.db.update_contact(
                contact_id,
                first_name=data['first_name'],
                father_name=data['father_name'],
                last_name=data['last_name'],
                phone=data['phone'],
                city=data['city']
            )
            
            if success:
                logger.info(f"Contact updated: {data['first_name']} {data['last_name']}".strip())
                self._load_contacts()  # Refresh
                self.message_panel.update_status("تم تحديث جهة الاتصال بنجاح!", "success")
            else:
                self.message_panel.update_status("فشل تحديث جهة الاتصال", "error")
        
        AddEditContactModal(self, on_save=on_save, contact=contact)
    
    def _on_delete_contact(self, contact_id: str):
        """Delete a contact after confirmation."""
        contact = next((c for c in self.all_contacts if c['id'] == contact_id), None)
        if not contact:
            return
        
        # Create confirmation dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("تأكيد الحذف")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        
        ctk.CTkLabel(
            dialog,
            text=f"هل أنت متأكد أنك تريد حذف '{self._display_name(contact)}'؟",
            font=("Arial", 12),
            wraplength=360
        ).pack(padx=15, pady=20)
        
        frame = ctk.CTkFrame(dialog)
        frame.pack(padx=15, pady=10, fill="x")
        frame.grid_columnconfigure((0, 1), weight=1)
        
        def confirm_delete():
            success = self.db.delete_contact(contact_id)
            if success:
                logger.info(f"Contact deleted: {self._display_name(contact)}")
                self._load_contacts()  # Refresh
                self.message_panel.update_status("تم حذف جهة الاتصال!", "success")
            else:
                self.message_panel.update_status("فشل حذف جهة الاتصال", "error")
            dialog.destroy()
        
        ctk.CTkButton(
            frame,
            text="حذف",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=confirm_delete
        ).grid(row=0, column=0, padx=5, sticky="ew")
        
        ctk.CTkButton(
            frame,
            text="إلغاء",
            fg_color="#555555",
            hover_color="#666666",
            command=dialog.destroy
        ).grid(row=0, column=1, padx=5, sticky="ew")
    
    def _on_select_all(self):
        """Select all contacts."""
        self.contact_list.select_all()
        self.selection_bar.update_count(len(self.contact_list.contact_rows), len(self.contact_list.contact_rows))
    
    def _on_deselect_all(self):
        """Deselect all contacts."""
        self.contact_list.deselect_all()
        self.selection_bar.update_count(0, len(self.contact_list.contact_rows))
    
    def _on_contact_selection_changed(self, count: int):
        """Handle contact selection change."""
        self.selection_bar.update_count(count, len(self.contact_list.contact_rows))

    def _on_selection_limit_reached(self, limit: int):
        """Notify user when max selectable contacts is reached."""
        self.message_panel.update_status(f"الحد الأقصى للتحديد هو {limit} جهة اتصال", "error")
    
    def _on_send_messages(self, message: str, image_path: Optional[str] = None):
        """Send text and/or image to selected contacts via WhatsApp Web."""
        phone_numbers = self.contact_list.get_selected_phones()

        if not phone_numbers:
            self.message_panel.update_status("خطأ: لم يتم تحديد أي جهات اتصال", "error")
            return

        has_text = bool(message.strip())
        has_image = bool(image_path and Path(image_path).is_file())
        if not has_text and not has_image:
            self.message_panel.update_status("خطأ: أدخل نصاً أو اختر صورة", "error")
            return

        logger.info(
            f"Starting send to {len(phone_numbers)} contacts "
            f"(image={'yes' if has_image else 'no'})"
        )

        self.message_panel.set_send_button_enabled(False)
        self.message_panel.update_status(
            f"جارٍ التحضير للإرسال إلى {len(phone_numbers)} جهة اتصال...", "info"
        )

        self.whatsapp_sender.send_messages(phone_numbers, message, image_path=image_path)
    
    def _on_send_progress(self, current: int, total: int, message: str):
        """Update progress during sending (Thread-Safe)."""
        # self.after(0, ...) safely queues the UI update on the main thread
        self.after(0, lambda: self.message_panel.update_status(f"[{current}/{total}] {message}", "info"))
    
    def _on_send_complete(self, success_count: int, failed_count: int, errors: List[str]):
        """Handle sending completion (Thread-Safe)."""
        
        # Wrap all the UI updates in a helper function
        def update_ui():
            # Re-enable send button
            self.message_panel.set_send_button_enabled(True)
            
            # Update status — success only when every recipient completed fully (image+text counts as one).
            if failed_count == 0 and success_count > 0:
                status = f"تم بنجاح! اكتمل الإرسال لـ {success_count} جهة (الصورة والنص معاً عند التوفر)"
                self.message_panel.update_status(status, "success")
                self.message_panel.clear_message()
                self.message_panel.clear_attached_image()
            elif failed_count == 0 and success_count == 0:
                if errors:
                    self.message_panel.update_status(str(errors[-1])[:240], "error")
                else:
                    self.message_panel.update_status("لم يُرسل شيء", "info")
            else:
                status = f"فشل جزئي: نجح {success_count}، فشل {failed_count} (لا يُحتسب النجاح إلا عند اكتمال الإرسال)"
                self.message_panel.update_status(status, "error" if failed_count > success_count else "info")
            
            # Log errors if any
            if errors:
                logger.error(f"Sending errors: {errors}")
        
        # Send the helper function to the main thread
        self.after(0, update_ui)
        logger.info(f"Message sending complete. Success: {success_count}, Failed: {failed_count}")
    
    def _show_firebase_error_dialog(self):
        """Show error dialog if Firebase initialization fails."""
        error_dialog = ctk.CTkToplevel(self)
        error_dialog.title("خطأ Firebase")
        error_dialog.geometry("500x250")
        error_dialog.resizable(False, False)
        
        ctk.CTkLabel(
            error_dialog,
            text="فشل تهيئة Firebase",
            font=("Arial", 16, "bold"),
            text_color="#e74c3c"
        ).pack(padx=20, pady=20)
        
        ctk.CTkLabel(
            error_dialog,
            text=(
                "تعذر العثور على ملف serviceAccountKey.json أو تحميله\n\n"
                "يرجى التأكد من وجود مفتاح حساب خدمة Firebase في المسار التالي:\n"
                f"{FIREBASE_CREDENTIALS_PATH}\n\n"
                "يمكنك تنزيله من Firebase Console > Project Settings > Service Accounts"
            ),
            font=("Arial", 11),
            wraplength=460,
            justify="right"
        ).pack(padx=20, pady=20)
        
        ctk.CTkButton(
            error_dialog,
            text="إغلاق",
            command=self.quit
        ).pack(pady=10)


def main():
    """Entry point: login window, then main app; logout returns to login."""
    try:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        db = FirebaseDatabase()

        while True:
            logged_in_user: List[Optional[Dict]] = [None]

            def on_login_success(user: Dict) -> None:
                logged_in_user[0] = user

            login = LoginApp(db, on_success=on_login_success)
            login.mainloop()
            if not logged_in_user[0]:
                break

            logout_requested = [False]

            def on_logout() -> None:
                logout_requested[0] = True

            app = DawaWhatsApp(logged_in_user[0], on_logout=on_logout)
            app.mainloop()
            if not logout_requested[0]:
                break
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
