"""
Modern UI Components using customtkinter
Provides all UI elements for the CRM WhatsApp application
"""

import customtkinter as ctk
import tkinter as tk
import tkinter.filedialog as filedialog
from datetime import datetime, timezone
from typing import Callable, List, Dict, Optional
import logging
from pathlib import Path
from PIL import Image

from auth_roles import (
    ROLE_ADMIN,
    ROLE_CONTACT_MANAGER,
    ROLE_MANAGER,
    role_label_ar,
)

logger = logging.getLogger(__name__)

_ROLE_ORDER = (ROLE_CONTACT_MANAGER, ROLE_MANAGER, ROLE_ADMIN)
_ROLE_COMBO_LABELS = [role_label_ar(r) for r in _ROLE_ORDER]
_LABEL_TO_ROLE = {role_label_ar(r): r for r in _ROLE_ORDER}


def _format_last_login(val) -> str:
    """Format Firestore timestamp for display (local timezone when aware)."""
    if val is None:
        return "لم يسجل دخول بعد"
    try:
        dt = val
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone()
            return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return str(val)


def _display_name(contact: Dict) -> str:
    """Build display name from Firestore first_name/father_name/last_name fields."""
    first = str(contact.get("first_name", "")).strip()
    father = str(contact.get("father_name", "")).strip()
    last = str(contact.get("last_name", "")).strip()
    return " ".join([part for part in (first, father, last) if part]).strip()


class ContactRow(ctk.CTkFrame):
    """A single contact row in the contact list."""
    
    def __init__(
        self,
        parent,
        contact: Dict,
        on_select: Callable[[str, bool], None],
        on_edit: Callable[[str], None],
        on_delete: Callable[[str], None],
        selection_enabled: bool = True,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.contact = contact
        self.contact_id = contact['id']
        self.on_select = on_select
        self.on_edit = on_edit
        self.on_delete = on_delete
        self._selection_enabled = selection_enabled
        
        self.is_selected = False
        
        # RTL layout: [حذف] [تعديل] [هاتف] [مدينة] [اسم] [☐]
        self.grid_columnconfigure(4, weight=1)

        self.checkbox = ctk.CTkCheckBox(self, text="", command=self._on_checkbox_toggle)
        self.checkbox.grid(row=0, column=5, padx=10, pady=5)
        if not selection_enabled:
            self.checkbox.configure(state="disabled")

        name_label = ctk.CTkLabel(self, text=_display_name(contact), font=("Arial", 14, "bold"))
        name_label.grid(row=0, column=4, sticky="e", padx=5)

        city_value = str(contact.get('city', '')).strip()
        city_label = ctk.CTkLabel(
            self,
            text=city_value,
            font=("Arial", 11),
            text_color="#888888"
        )
        city_label.grid(row=0, column=3, sticky="e", padx=5)
        if not city_value:
            city_label.grid_remove()

        phone_label = ctk.CTkLabel(
            self,
            text=contact['phone'],
            font=("Arial", 12),
            text_color="#aaaaaa"
        )
        phone_label.grid(row=0, column=2, sticky="e", padx=5)

        edit_btn = ctk.CTkButton(
            self,
            text="تعديل",
            width=60,
            height=30,
            font=("Arial", 11),
            command=lambda: self.on_edit(self.contact_id)
        )
        edit_btn.grid(row=0, column=1, padx=5)

        delete_btn = ctk.CTkButton(
            self,
            text="حذف",
            width=60,
            height=30,
            font=("Arial", 11),
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=lambda: self.on_delete(self.contact_id)
        )
        delete_btn.grid(row=0, column=0, padx=5)
    
    def _on_checkbox_toggle(self):
        """Handle checkbox toggle."""
        if not self._selection_enabled:
            return
        self.is_selected = self.checkbox.get()
        self.on_select(self.contact_id, self.is_selected)
    
    def set_selected(self, selected: bool):
        """Set checkbox state without triggering callback."""
        self.is_selected = selected
        if selected:
            self.checkbox.select()
        else:
            self.checkbox.deselect()


class ContactListFrame(ctk.CTkScrollableFrame):
    """Scrollable frame containing all contact rows."""
    MAX_SELECTED_CONTACTS = 100
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.contact_rows: Dict[str, ContactRow] = {}
        self.selected_contacts: set = set()
        
        self.on_select_callback: Optional[Callable] = None
        self.on_edit_callback: Optional[Callable] = None
        self.on_delete_callback: Optional[Callable] = None
        self.on_selection_limit_callback: Optional[Callable[[int], None]] = None
        self._selection_enabled: bool = True
    
    def set_callbacks(
        self,
        on_select: Callable,
        on_edit: Callable,
        on_delete: Callable,
        on_selection_limit: Optional[Callable[[int], None]] = None,
    ):
        """Set callback functions."""
        self.on_select_callback = on_select
        self.on_edit_callback = on_edit
        self.on_delete_callback = on_delete
        self.on_selection_limit_callback = on_selection_limit
    
    def add_contacts(self, contacts: List[Dict]):
        """Add multiple contacts to the list."""
        # Clear existing contacts
        for row in self.contact_rows.values():
            row.destroy()
        self.contact_rows.clear()
        self.selected_contacts.clear()
        
        # Add new contacts
        for contact in contacts:
            self.add_contact(contact)
    
    def add_contact(self, contact: Dict):
        """Add a single contact row."""
        row = ContactRow(
            self,
            contact,
            on_select=self._on_contact_select,
            on_edit=self.on_edit_callback,
            on_delete=self.on_delete_callback,
            selection_enabled=self._selection_enabled,
            fg_color="#2d2d2d",
            border_width=1,
            border_color="#3d3d3d",
            corner_radius=5
        )
        row.pack(fill="x", padx=5, pady=3)
        
        self.contact_rows[contact['id']] = row
    
    def _on_contact_select(self, contact_id: str, selected: bool):
        """Handle contact selection."""
        if not self._selection_enabled:
            return
        if selected:
            if len(self.selected_contacts) >= self.MAX_SELECTED_CONTACTS:
                row = self.contact_rows.get(contact_id)
                if row:
                    row.set_selected(False)
                if self.on_selection_limit_callback:
                    self.on_selection_limit_callback(self.MAX_SELECTED_CONTACTS)
                if self.on_select_callback:
                    self.on_select_callback(len(self.selected_contacts))
                return
            self.selected_contacts.add(contact_id)
        else:
            self.selected_contacts.discard(contact_id)
        
        if self.on_select_callback:
            self.on_select_callback(len(self.selected_contacts))
    
    def select_all(self):
        """Select contacts up to the configured maximum."""
        if not self._selection_enabled:
            if self.on_select_callback:
                self.on_select_callback(0)
            return
        self.selected_contacts.clear()
        selected_now = 0
        for contact_id, row in self.contact_rows.items():
            if selected_now < self.MAX_SELECTED_CONTACTS:
                row.set_selected(True)
                self.selected_contacts.add(contact_id)
                selected_now += 1
            else:
                row.set_selected(False)
        if len(self.contact_rows) > self.MAX_SELECTED_CONTACTS and self.on_selection_limit_callback:
            self.on_selection_limit_callback(self.MAX_SELECTED_CONTACTS)
        if self.on_select_callback:
            self.on_select_callback(len(self.selected_contacts))
    
    def deselect_all(self):
        """Deselect all contacts."""
        for _, row in self.contact_rows.items():
            row.set_selected(False)
        self.selected_contacts.clear()
        if self.on_select_callback:
            self.on_select_callback(0)

    def set_selection_enabled(self, enabled: bool):
        """When False, checkboxes are disabled and selection is cleared."""
        self._selection_enabled = enabled
        if not enabled:
            self.deselect_all()
        elif self.on_select_callback:
            self.on_select_callback(len(self.selected_contacts))
    
    def get_selected_phones(self) -> List[str]:
        """Get phone numbers of selected contacts."""
        phones = []
        for contact_id in self.selected_contacts:
            row = self.contact_rows.get(contact_id)
            if row:
                phones.append(row.contact['phone'])
        return phones
    
    def remove_contact(self, contact_id: str):
        """Remove a contact from the list."""
        row = self.contact_rows.pop(contact_id, None)
        if row:
            row.destroy()
        self.selected_contacts.discard(contact_id)


class SearchBar(ctk.CTkFrame):
    """Top search and action bar."""
    
    def __init__(self, parent, on_search: Callable, on_add: Callable, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.on_search = on_search
        self.on_add = on_add
        
        # RTL: wide search (cols 0–2), then :بحث, إضافة, شعار
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        self.search_entry = ctk.CTkEntry(
            self,
            placeholder_text="الاسم، الهاتف، البلد",
            font=("Arial", 12),
            justify="right",
        )
        self.search_entry.grid(row=0, column=0, columnspan=3, padx=(10, 6), pady=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.on_search(self.search_entry.get()))

        search_label = ctk.CTkLabel(
            self,
            text=":بحث",
            font=("Arial", 12, "bold")
        )
        search_label.grid(row=0, column=3, padx=6, pady=10, sticky="e")

        add_btn = ctk.CTkButton(
            self,
            text="+ إضافة جهة اتصال",
            width=150,
            height=35,
            font=("Arial", 12, "bold"),
            fg_color="#25d366",
            hover_color="#20c354",
            command=self.on_add
        )
        add_btn.grid(row=0, column=4, padx=10, pady=10)

        self._logo_image = None
        logo_path = Path(__file__).with_name("logo.png")
        if logo_path.exists():
            try:
                pil_img = Image.open(logo_path)
                self._logo_image = ctk.CTkImage(
                    light_image=pil_img,
                    dark_image=pil_img,
                    size=(40, 40)
                )
                logo_label = ctk.CTkLabel(self, text="", image=self._logo_image)
                logo_label.grid(row=0, column=5, padx=10, pady=10, sticky="e")
            except Exception:
                self._logo_image = None
    
    def clear_search(self):
        """Clear search field."""
        self.search_entry.delete(0, "end")


class SelectionBar(ctk.CTkFrame):
    """Bar with Select All/Deselect All and contact count."""
    
    def __init__(self, parent, on_select_all: Callable, on_deselect_all: Callable, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.grid_columnconfigure(1, weight=1)

        self.master_checkbox = ctk.CTkCheckBox(
            self,
            text=":الكل تحديد",
            command=self._on_master_toggle
        )
        self.master_checkbox.grid(row=0, column=1, padx=10, pady=8, sticky="e")

        self.count_label = ctk.CTkLabel(
            self,
            text="المحدد: 0",
            font=("Arial", 11),
            text_color="#aaaaaa"
        )
        self.count_label.grid(row=0, column=0, padx=10, pady=8, sticky="w")
        
        self.on_select_all = on_select_all
        self.on_deselect_all = on_deselect_all
        self.is_all_selected = False
        self._bulk_enabled = True
    
    def set_bulk_select_enabled(self, enabled: bool):
        """Disable master checkbox when user cannot select contacts for sending."""
        self._bulk_enabled = enabled
        if not enabled:
            self.master_checkbox.deselect()
            self.is_all_selected = False
            self.master_checkbox.configure(state="disabled")
            self.on_deselect_all()
        else:
            self.master_checkbox.configure(state="normal")
    
    def _on_master_toggle(self):
        """Handle master checkbox toggle."""
        if not self._bulk_enabled:
            return
        if self.master_checkbox.get():
            self.is_all_selected = True
            self.on_select_all()
        else:
            self.is_all_selected = False
            self.on_deselect_all()
    
    def update_count(self, count: int, total: int):
        """Update the selected count display."""
        self.count_label.configure(text=f"المحدد: {count} / {total}")
        if not self._bulk_enabled:
            self.master_checkbox.deselect()
            self.is_all_selected = False
            return
        # Update master checkbox state if needed
        if count == 0:
            self.master_checkbox.deselect()
            self.is_all_selected = False
        elif count == total and total > 0:
            self.master_checkbox.select()
            self.is_all_selected = True
        else:
            self.master_checkbox.deselect()
            self.is_all_selected = False
    
    def reset(self):
        """Reset selection bar."""
        self.master_checkbox.deselect()
        self.is_all_selected = False
        self.count_label.configure(text="المحدد: 0")


class MessagePanel(ctk.CTkFrame):
    """Bottom panel: compose/send messages and manage saved templates (Firestore `messages`)."""

    def __init__(
        self,
        parent,
        on_send: Callable[[str, Optional[str]], None],
        on_list_saved_messages: Callable[[], List[Dict]],
        on_save_saved_message: Callable[[str], bool],
        on_delete_saved_message: Callable[[str], bool],
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.on_send = on_send
        self._image_path: Optional[str] = None
        self.on_list_saved_messages = on_list_saved_messages
        self.on_save_saved_message = on_save_saved_message
        self.on_delete_saved_message = on_delete_saved_message

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        self.status_strip = ctk.CTkLabel(
            self,
            text="جاهز",
            font=("Arial", 11),
            text_color="#aaaaaa",
            anchor="e",
        )
        self.status_strip.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 4))

        # --- Compose view ---
        self.compose_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.compose_frame.grid_columnconfigure(0, weight=1)
        self.compose_frame.grid_rowconfigure(2, weight=1)

        manage_btn = ctk.CTkButton(
            self.compose_frame,
            text="إدارة الرسائل",
            height=32,
            font=("Arial", 12, "bold"),
            fg_color="#3d3d3d",
            hover_color="#4a4a4a",
            command=self._show_manager_view,
        )
        manage_btn.grid(row=0, column=0, padx=10, pady=(10, 4), sticky="ew")

        msg_label = ctk.CTkLabel(
            self.compose_frame,
            text=":الرسالة",
            font=("Arial", 12, "bold"),
        )
        msg_label.grid(row=1, column=0, padx=10, pady=(4, 0), sticky="e")

        self.message_text = ctk.CTkTextbox(
            self.compose_frame,
            font=("Arial", 11),
            height=80,
        )
        self.message_text.grid(row=2, column=0, padx=10, pady=8, sticky="nsew")
        self._setup_message_text_edit_shortcuts()
        self._setup_message_text_rtl()
        self.message_text.bind("<Control-v>", self._on_message_paste)
        self.message_text.bind("<Control-V>", self._on_message_paste)
        self.message_text.bind("<Shift-Insert>", self._on_message_paste)
        self.message_text.bind("<<Paste>>", self._on_message_paste)

        img_row = ctk.CTkFrame(self.compose_frame, fg_color="transparent")
        img_row.grid(row=3, column=0, padx=10, pady=(0, 4), sticky="ew")
        img_row.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            img_row,
            text="رفع صورة",
            height=32,
            font=("Arial", 12, "bold"),
            fg_color="#8e44ad",
            hover_color="#7d3c98",
            command=self._on_pick_image,
        ).grid(row=0, column=0, padx=(0, 8), sticky="e")

        ctk.CTkButton(
            img_row,
            text="إزالة الصورة",
            height=32,
            width=110,
            font=("Arial", 11),
            fg_color="#555555",
            hover_color="#666666",
            command=self._on_clear_image,
        ).grid(row=0, column=1, sticky="w")

        self._image_hint = ctk.CTkLabel(
            img_row,
            text="",
            font=("Arial", 10),
            text_color="#888888",
            anchor="e",
        )
        self._image_hint.grid(row=0, column=2, padx=(8, 0), sticky="ew")

        save_msg_btn = ctk.CTkButton(
            self.compose_frame,
            text="إحفظ الرسالة",
            height=32,
            font=("Arial", 12, "bold"),
            fg_color="#2980b9",
            hover_color="#2471a3",
            command=self._on_save_current_message,
        )
        save_msg_btn.grid(row=4, column=0, padx=10, pady=(0, 6), sticky="ew")

        control_frame = ctk.CTkFrame(self.compose_frame, fg_color="transparent")
        control_frame.grid(row=5, column=0, padx=10, pady=(4, 10), sticky="ew")
        control_frame.grid_columnconfigure(0, weight=1)

        self.send_btn = ctk.CTkButton(
            control_frame,
            text="إرسال إلى المحددين",
            height=40,
            font=("Arial", 13, "bold"),
            fg_color="#25d366",
            hover_color="#20c354",
            command=self._on_send_click,
        )
        self.send_btn.grid(row=0, column=1, padx=5, sticky="e")

        self.progress_label = ctk.CTkLabel(
            control_frame,
            text="جاهز",
            font=("Arial", 11),
            text_color="#aaaaaa",
        )
        self.progress_label.grid(row=0, column=0, padx=10, sticky="w")

        # --- Saved messages manager view ---
        self.manager_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.manager_frame.grid_columnconfigure(0, weight=1)
        self.manager_frame.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(self.manager_frame, fg_color="transparent")
        top_bar.grid(row=0, column=0, padx=10, pady=(10, 6), sticky="ew")
        top_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_bar,
            text="الرسائل المحفوظة",
            font=("Arial", 14, "bold"),
        ).grid(row=0, column=0, sticky="e")

        ctk.CTkButton(
            top_bar,
            text="← العودة",
            width=120,
            height=32,
            font=("Arial", 12, "bold"),
            fg_color="#555555",
            hover_color="#666666",
            command=self._show_compose_view,
        ).grid(row=0, column=1, padx=(10, 0), sticky="e")

        self.messages_scroll = ctk.CTkScrollableFrame(
            self.manager_frame,
            fg_color="#252525",
            corner_radius=6,
        )
        self.messages_scroll.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.messages_scroll.grid_columnconfigure(0, weight=1)

        self.compose_frame.grid(row=1, column=0, sticky="nsew")
        self.manager_frame.grid_remove()

    def set_messaging_ui_visible(self, visible: bool):
        """Hide compose/manager for ContactManager; status_strip still shows messages."""
        if visible:
            self.compose_frame.grid(row=1, column=0, sticky="nsew")
            self.manager_frame.grid_remove()
            self.configure(height=260)
        else:
            self.compose_frame.grid_remove()
            self.manager_frame.grid_remove()
            self.configure(height=56)
            self.status_strip.configure(
                text="صلاحية: إدارة جهات الاتصال فقط (بدون إرسال واتساب)",
                text_color="#888888",
            )

    def _show_compose_view(self):
        self.manager_frame.grid_remove()
        self.compose_frame.grid(row=1, column=0, sticky="nsew")

    def _show_manager_view(self):
        self.compose_frame.grid_remove()
        self.manager_frame.grid(row=1, column=0, sticky="nsew")
        self._refresh_saved_messages_list()

    def _refresh_saved_messages_list(self):
        for child in self.messages_scroll.winfo_children():
            child.destroy()

        items = self.on_list_saved_messages()
        if not items:
            ctk.CTkLabel(
                self.messages_scroll,
                text="لا توجد رسائل محفوظة",
                font=("Arial", 12),
                text_color="#888888",
            ).grid(row=0, column=0, padx=8, pady=12, sticky="ew")
            return

        for idx, item in enumerate(items):
            self._add_saved_message_row(idx, item)

    @staticmethod
    def _preview_text(text: str, max_len: int = 120) -> str:
        t = (text or "").replace("\n", " ").strip()
        if len(t) <= max_len:
            return t
        return t[: max_len - 1] + "…"

    def _add_saved_message_row(self, row_index: int, item: Dict):
        msg_id = item.get("id", "")
        full_text = str(item.get("text", ""))

        row = ctk.CTkFrame(self.messages_scroll, fg_color="#2d2d2d", corner_radius=6)
        row.grid(row=row_index, column=0, padx=6, pady=4, sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        preview = ctk.CTkLabel(
            row,
            text=self._preview_text(full_text),
            font=("Arial", 11),
            wraplength=520,
            justify="right",
            anchor="e",
        )
        preview.grid(row=0, column=0, rowspan=2, padx=8, pady=6, sticky="nsew")

        def do_insert():
            self.message_text.delete("1.0", "end")
            self.message_text.insert("1.0", full_text)
            self._apply_message_text_rtl()
            self._show_compose_view()
            self.update_status("تم إدراج الرسالة", "success")

        def do_delete():
            if self.on_delete_saved_message(msg_id):
                self.update_status("تم حذف الرسالة", "success")
                self._refresh_saved_messages_list()
            else:
                self.update_status("فشل حذف الرسالة", "error")

        ctk.CTkButton(
            row,
            text="إدراج",
            width=72,
            height=28,
            font=("Arial", 11, "bold"),
            fg_color="#27ae60",
            hover_color="#219a52",
            command=do_insert,
        ).grid(row=0, column=1, padx=(4, 8), pady=(6, 2), sticky="e")

        ctk.CTkButton(
            row,
            text="حذف",
            width=72,
            height=28,
            font=("Arial", 11, "bold"),
            fg_color="#c0392b",
            hover_color="#a93226",
            command=do_delete,
        ).grid(row=1, column=1, padx=(4, 8), pady=(2, 6), sticky="e")

    def _on_pick_image(self):
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="اختر صورة",
            filetypes=[
                ("صور", "*.png *.jpg *.jpeg *.gif *.webp *.bmp"),
                ("كل الملفات", "*.*"),
            ],
        )
        if path:
            self._image_path = path
            self._image_hint.configure(text=Path(path).name)
            self.update_status("تم رفع صورة ", "success")

    def _on_clear_image(self):
        self._image_path = None
        self._image_hint.configure(text="")
        self.update_status("جاهز", "info")

    def clear_attached_image(self):
        """Clear selected image after a successful send."""
        self._on_clear_image()

    def _on_save_current_message(self):
        text = self.message_text.get("1.0", "end").strip()
        if not text:
            self.update_status("لا يمكن حفظ رسالة فارغة", "error")
            return
        if self.on_save_saved_message(text):
            self.update_status("تم حفظ الرسالة", "success")
        else:
            self.update_status("فشل حفظ الرسالة", "error")

    def _on_send_click(self):
        message = self.message_text.get("1.0", "end").strip()
        if not message and not self._image_path:
            self.update_status("خطأ: أدخل نصاً أو اختر صورة", "error")
            return
        self.on_send(message, self._image_path)

    def _setup_message_text_edit_shortcuts(self):
        """Enable Ctrl+A (select all) and Ctrl+Z (undo) on the underlying Tk Text widget."""
        inner = getattr(self.message_text, "_textbox", None)
        if inner is None:
            return
        inner.configure(undo=True, autoseparators=True, maxundo=-1)
        inner.bind("<Control-a>", MessagePanel._message_text_select_all)
        inner.bind("<Control-A>", MessagePanel._message_text_select_all)
        inner.bind("<Control-z>", MessagePanel._message_text_undo)
        inner.bind("<Control-Z>", MessagePanel._message_text_undo)

    def _setup_message_text_rtl(self):
        """Right-align message textbox content for RTL typing."""
        inner = getattr(self.message_text, "_textbox", None)
        if inner is None:
            return
        inner.tag_configure("rtl", justify="right")
        self._apply_message_text_rtl()
        inner.bind("<KeyRelease>", lambda _e: self._apply_message_text_rtl(), add="+")

    def _apply_message_text_rtl(self):
        """Apply RTL alignment tag to whole textbox content."""
        inner = getattr(self.message_text, "_textbox", None)
        if inner is None:
            return
        try:
            inner.tag_add("rtl", "1.0", "end")
            inner.mark_set("insert", "end-1c")
            inner.see("insert")
        except tk.TclError:
            pass

    @staticmethod
    def _message_text_select_all(event):
        w = event.widget
        try:
            w.tag_add("sel", "1.0", "end-1c")
            w.mark_set("insert", "end-1c")
            w.see("insert")
        except tk.TclError:
            pass
        return "break"

    @staticmethod
    def _message_text_undo(event):
        try:
            event.widget.edit_undo()
        except tk.TclError:
            pass
        return "break"

    def _on_message_paste(self, event=None):
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                self.message_text.insert("insert", clipboard_text)
                self._apply_message_text_rtl()
            return "break"
        except Exception:
            return None

    def get_message(self) -> str:
        return self.message_text.get("1.0", "end").strip()

    def clear_message(self):
        self.message_text.delete("1.0", "end")
        self._apply_message_text_rtl()

    def update_status(self, status: str, status_type: str = "info"):
        color_map = {
            "info": "#aaaaaa",
            "success": "#27ae60",
            "error": "#e74c3c",
        }
        c = color_map.get(status_type, "#aaaaaa")
        self.status_strip.configure(text=status, text_color=c)
        self.progress_label.configure(text=status, text_color=c)

    def set_send_button_enabled(self, enabled: bool):
        self.send_btn.configure(state="normal" if enabled else "disabled")


class AddEditContactModal(ctk.CTkToplevel):
    """Modal dialog for adding/editing contacts."""
    
    def __init__(
        self,
        parent,
        on_save: Callable,
        contact: Optional[Dict] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.contact = contact
        self.on_save = on_save
        self.result = None
        
        # Configure window
        self.title("إضافة جهة اتصال" if not contact else "تعديل جهة اتصال")
        self.geometry("560x620")
        self.resizable(True, True)

        self.default_cities = [
            "يمة - زيمر",
            "ابثان - زيمر",
            "المرجة الشمالية - زيمر",
            "المرجة الجنوبية - زيمر",
            "حارة أبو ياسين - زيمر",
            "بئر السكة - زيمر",
            "جت المثلث",
            "باقة الغربية",
        ]
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Required fields helper
        ctk.CTkLabel(
            self,
            text="الحقول المعلّمة بـ * مطلوبة",
            font=("Arial", 11),
            text_color="#aaaaaa"
        ).grid(row=0, column=0, padx=15, pady=(10, 5), sticky="e")
        
        # First name field
        ctk.CTkLabel(
            self,
            text="الاسم الأول: *",
            font=("Arial", 12, "bold")
        ).grid(row=1, column=0, padx=15, pady=(10, 5), sticky="e")
        
        self.first_name_entry = ctk.CTkEntry(
            self,
            font=("Arial", 12),
            height=35
        )
        self.first_name_entry.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="ew")
        
        # Father name field
        ctk.CTkLabel(
            self,
            text="اسم الأب:",
            font=("Arial", 12, "bold")
        ).grid(row=3, column=0, padx=15, pady=(10, 5), sticky="e")

        self.father_name_entry = ctk.CTkEntry(
            self,
            font=("Arial", 12),
            height=35
        )
        self.father_name_entry.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="ew")

        # Last name field
        ctk.CTkLabel(
            self,
            text="اسم العائلة: *",
            font=("Arial", 12, "bold")
        ).grid(row=5, column=0, padx=15, pady=(10, 5), sticky="e")
        
        self.last_name_entry = ctk.CTkEntry(
            self,
            font=("Arial", 12),
            height=35
        )
        self.last_name_entry.grid(row=6, column=0, padx=15, pady=(0, 10), sticky="ew")

        # Phone field
        ctk.CTkLabel(
            self,
            text="الهاتف: *",
            font=("Arial", 12, "bold")
        ).grid(row=7, column=0, padx=15, pady=(10, 5), sticky="e")

        self.phone_entry = ctk.CTkEntry(
            self,
            font=("Arial", 12),
            height=35
        )
        self.phone_entry.grid(row=8, column=0, padx=15, pady=(0, 10), sticky="ew")

        # City field
        ctk.CTkLabel(
            self,
            text="المدينة:",
            font=("Arial", 12, "bold")
        ).grid(row=9, column=0, padx=15, pady=(10, 5), sticky="e")

        self.city_combo = ctk.CTkComboBox(
            self,
            values=self.default_cities,
            font=("Arial", 12),
            height=35
        )
        self.city_combo.grid(row=10, column=0, padx=15, pady=(0, 10), sticky="ew")
        self.city_combo.set(self.default_cities[0])

        # Button frame
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=11, column=0, padx=15, pady=15, sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Save button
        ctk.CTkButton(
            btn_frame,
            text="حفظ",
            font=("Arial", 12, "bold"),
            fg_color="#25d366",
            hover_color="#20c354",
            command=self._on_save
        ).grid(row=0, column=0, padx=5, sticky="ew")
        
        # Cancel button
        ctk.CTkButton(
            btn_frame,
            text="إلغاء",
            font=("Arial", 12, "bold"),
            fg_color="#555555",
            hover_color="#666666",
            command=self.destroy
        ).grid(row=0, column=1, padx=5, sticky="ew")
        
        # Populate fields if editing
        if contact:
            self.first_name_entry.insert(0, contact.get('first_name', ''))
            self.father_name_entry.insert(0, contact.get('father_name', ''))
            self.last_name_entry.insert(0, contact.get('last_name', ''))
            self.phone_entry.insert(0, contact.get('phone', ''))
            existing_city = str(contact.get('city', '')).strip()
            if existing_city:
                if existing_city not in self.default_cities:
                    self.default_cities.append(existing_city)
                    self.city_combo.configure(values=self.default_cities)
                self.city_combo.set(existing_city)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        self.focus()
    
    def _on_save(self):
        """Handle save button."""
        first_name = self.first_name_entry.get().strip()
        father_name = self.father_name_entry.get().strip()
        last_name = self.last_name_entry.get().strip()
        phone = self.phone_entry.get().strip()
        city = self.city_combo.get().strip()
        
        if not first_name or not last_name or not phone:
            self._show_error("يرجى تعبئة الحقول المطلوبة: الاسم الأول، اسم العائلة، الهاتف")
            return

        # Israeli local format validation: must be exactly 10 digits and start with 0.
        if len(phone) != 10 or not phone.isdigit() or not phone.startswith("0"):
            self._show_error("رقم الهاتف يجب أن يكون 10 أرقام ويبدأ بـ 0")
            return
        
        self.result = {
            'first_name': first_name,
            'father_name': father_name,
            'last_name': last_name,
            'phone': phone,
            'city': city
        }
        self.on_save(self.contact['id'] if self.contact else None, self.result)
        self.destroy()
    
    def _show_error(self, message: str):
        """Show error message."""
        error_window = ctk.CTkToplevel(self)
        error_window.title("خطأ")
        error_window.geometry("300x150")
        error_window.resizable(False, False)
        error_window.transient(self)
        error_window.lift()
        error_window.attributes("-topmost", True)
        error_window.after(100, lambda: error_window.attributes("-topmost", False))
        error_window.grab_set()
        error_window.focus_force()
        
        ctk.CTkLabel(
            error_window,
            text=message,
            font=("Arial", 12),
            wraplength=280
        ).pack(padx=15, pady=15)
        
        ctk.CTkButton(
            error_window,
            text="موافق",
            command=error_window.destroy
        ).pack(pady=10)


class LoginApp(ctk.CTk):
    """Login or bootstrap first admin; calls on_success(user_dict) then destroys itself."""

    def __init__(self, db, on_success: Callable[[Dict], None], **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.on_success = on_success
        self.title("تسجيل الدخول")
        self.geometry("440x480")
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self._bootstrap_mode = db.count_users() == 0

        self._login_logo_image = None
        logo_path = Path(__file__).with_name("logo.png")
        if logo_path.exists():
            try:
                pil_img = Image.open(logo_path)
                self._login_logo_image = ctk.CTkImage(
                    light_image=pil_img,
                    dark_image=pil_img,
                    size=(52, 52),
                )
                ctk.CTkLabel(self, text="", image=self._login_logo_image).grid(
                    row=0, column=0, padx=(16, 6), pady=(18, 4), sticky="nw"
                )
            except Exception:
                self._login_logo_image = None

        ctk.CTkLabel(
            self,
            text="مرسل واتساب الدعوة",
            font=("Arial", 18, "bold"),
        ).grid(row=0, column=1, padx=(0, 20), pady=(24, 8), sticky="ne")

        subtitle = (
            "أنشئ حساب المسؤول الأول (اسم مستخدم وكلمة مرور)"
            if self._bootstrap_mode
            else "أدخل بيانات الدخول"
        )
        ctk.CTkLabel(self, text=subtitle, font=("Arial", 12), text_color="#aaaaaa").grid(
            row=1, column=0, columnspan=2, padx=20, pady=(0, 16), sticky="e"
        )

        ctk.CTkLabel(self, text="اسم المستخدم:", font=("Arial", 12, "bold")).grid(
            row=2, column=0, columnspan=2, padx=20, pady=(8, 4), sticky="e"
        )
        self.user_entry = ctk.CTkEntry(self, font=("Arial", 13), height=36, justify="right")
        self.user_entry.grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(self, text="كلمة المرور:", font=("Arial", 12, "bold")).grid(
            row=4, column=0, columnspan=2, padx=20, pady=(8, 4), sticky="e"
        )
        self.pass_entry = ctk.CTkEntry(self, font=("Arial", 13), height=36, show="*", justify="right")
        self.pass_entry.grid(row=5, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")

        self.confirm_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.confirm_frame.grid_columnconfigure(0, weight=1)
        if self._bootstrap_mode:
            ctk.CTkLabel(self.confirm_frame, text="تأكيد كلمة المرور:", font=("Arial", 12, "bold")).grid(
                row=0, column=0, padx=0, pady=(8, 4), sticky="e"
            )
            self.confirm_entry = ctk.CTkEntry(
                self.confirm_frame, font=("Arial", 13), height=36, show="*", justify="right"
            )
            self.confirm_entry.grid(row=1, column=0, pady=(0, 0), sticky="ew")
            self.confirm_frame.grid(row=6, column=0, columnspan=2, padx=20, pady=0, sticky="ew")

        self.status_label = ctk.CTkLabel(self, text="", font=("Arial", 11), text_color="#e74c3c")
        self.status_label.grid(row=7, column=0, columnspan=2, padx=20, pady=(12, 8), sticky="e")

        btn_text = "إنشاء والدخول" if self._bootstrap_mode else "دخول"
        ctk.CTkButton(
            self,
            text=btn_text,
            font=("Arial", 14, "bold"),
            height=40,
            fg_color="#25d366",
            hover_color="#20c354",
            command=self._submit,
        ).grid(row=8, column=0, columnspan=2, padx=20, pady=(8, 24), sticky="ew")

        if not self.db.db:
            self.status_label.configure(text="Firebase غير متصل — أضف serviceAccountKey.json")
            self.user_entry.configure(state="disabled")
            self.pass_entry.configure(state="disabled")

        self.user_entry.focus()

    def _submit(self):
        if not self.db.db:
            return
        user = self.user_entry.get().strip()
        pw = self.pass_entry.get()
        if self._bootstrap_mode:
            if not user:
                self.status_label.configure(text="أدخل اسم المستخدم")
                return
            pw2 = self.confirm_entry.get()
            if len(pw) < 4:
                self.status_label.configure(text="كلمة المرور قصيرة جداً (4 أحرف على الأقل)")
                return
            if pw != pw2:
                self.status_label.configure(text="كلمتا المرور غير متطابقتين")
                return
            uid = self.db.add_user(user, pw, ROLE_ADMIN)
            if not uid:
                self.status_label.configure(text="تعذر إنشاء المستخدم — ربما اسم المستخدم مستخدم")
                return
        else:
            if not user or not pw:
                self.status_label.configure(text="أدخل اسم المستخدم وكلمة المرور")
                return

        session = self.db.authenticate_user(user, pw)
        if session:
            self.status_label.configure(text="")
            self.on_success(session)
            self.destroy()
        else:
            self.status_label.configure(text="اسم المستخدم أو كلمة المرور غير صحيحة")


class AddEditUserModal(ctk.CTkToplevel):
    """Create or edit an application user (admin only)."""

    def __init__(
        self,
        parent,
        on_save: Callable[..., None],
        user: Optional[Dict] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.user = user
        self.on_save = on_save
        self.title("مستخدم جديد" if not user else "تعديل مستخدم")
        self.geometry("480x420")
        self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="اسم المستخدم (فريد):",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="e")
        self.username_entry = ctk.CTkEntry(self, font=("Arial", 13), height=34, justify="right")
        self.username_entry.grid(row=1, column=0, padx=16, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(
            self,
            text="كلمة المرور:" + ("" if not user else " (اتركها فارغة للإبقاء على الحالية)"),
            font=("Arial", 12, "bold"),
        ).grid(row=2, column=0, padx=16, pady=(8, 4), sticky="e")
        self.password_entry = ctk.CTkEntry(self, font=("Arial", 13), height=34, show="*", justify="right")
        self.password_entry.grid(row=3, column=0, padx=16, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(self, text="الدور:", font=("Arial", 12, "bold")).grid(
            row=4, column=0, padx=16, pady=(8, 4), sticky="e"
        )
        self.role_combo = ctk.CTkComboBox(
            self,
            values=_ROLE_COMBO_LABELS,
            font=("Arial", 12),
            height=34,
            state="readonly",
        )
        self.role_combo.grid(row=5, column=0, padx=16, pady=(0, 16), sticky="ew")
        self.role_combo.set(_ROLE_COMBO_LABELS[-1])

        if user:
            self.username_entry.insert(0, user.get("username", ""))
            r = user.get("role", ROLE_CONTACT_MANAGER)
            if r in _ROLE_ORDER:
                self.role_combo.set(role_label_ar(r))
            else:
                self.role_combo.set(_ROLE_COMBO_LABELS[0])

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.grid(row=6, column=0, padx=16, pady=12, sticky="ew")
        bf.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            bf,
            text="حفظ",
            font=("Arial", 12, "bold"),
            fg_color="#25d366",
            hover_color="#20c354",
            command=self._on_save,
        ).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(
            bf,
            text="إلغاء",
            font=("Arial", 12, "bold"),
            fg_color="#555555",
            hover_color="#666666",
            command=self.destroy,
        ).grid(row=0, column=1, padx=4, sticky="ew")

        self.transient(parent)
        self.grab_set()
        self.focus()

    def _on_save(self):
        username = self.username_entry.get().strip()
        pw = self.password_entry.get()
        label = self.role_combo.get()
        role = _LABEL_TO_ROLE.get(label, ROLE_CONTACT_MANAGER)
        if not username:
            return
        if not self.user and len(pw) < 4:
            return
        pw_out = pw.strip() if pw.strip() else None
        self.on_save(self.user["id"] if self.user else None, username, role, pw_out)
        self.destroy()


class UsersAdminPanel(ctk.CTkFrame):
    """Admin tab: list users (username, role, last login) and add/edit/delete."""

    def __init__(
        self,
        parent,
        on_list_users: Callable[[], List[Dict]],
        on_add_user: Callable[[str, str, str], bool],
        on_update_user: Callable[[str, str, str, Optional[str]], bool],
        on_delete_user: Callable[[str], bool],
        current_user_id: str,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.on_list_users = on_list_users
        self.on_add_user = on_add_user
        self.on_update_user = on_update_user
        self.on_delete_user = on_delete_user
        self.current_user_id = current_user_id

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text="المستخدمون", font=("Arial", 16, "bold")).grid(row=0, column=0, sticky="e")
        ctk.CTkButton(
            top,
            text="+ مستخدم جديد",
            width=140,
            height=32,
            font=("Arial", 12, "bold"),
            fg_color="#25d366",
            hover_color="#20c354",
            command=self._open_add,
        ).grid(row=0, column=1, padx=(8, 0), sticky="e")

        self.status = ctk.CTkLabel(self, text="", font=("Arial", 11), text_color="#aaaaaa")
        self.status.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="e")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#252525", corner_radius=6)
        self.scroll.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

    def refresh(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        users = self.on_list_users()
        if not users:
            ctk.CTkLabel(
                self.scroll,
                text="لا يوجد مستخدمون",
                font=("Arial", 12),
                text_color="#888888",
            ).grid(row=0, column=0, padx=8, pady=12, sticky="ew")
            return
        for i, u in enumerate(users):
            self._row(i, u)

    def _row(self, i: int, u: Dict):
        row = ctk.CTkFrame(self.scroll, fg_color="#2d2d2d", corner_radius=6)
        row.grid(row=i, column=0, padx=4, pady=4, sticky="ew")
        row.grid_columnconfigure(1, weight=1)
        un = str(u.get("username", ""))
        role = str(u.get("role", ""))
        ctk.CTkLabel(row, text=un, font=("Arial", 13, "bold"), anchor="e").grid(
            row=0, column=2, padx=10, pady=8, sticky="e"
        )
        ctk.CTkLabel(
            row,
            text=role_label_ar(role),
            font=("Arial", 12),
            text_color="#aaaaaa",
            anchor="e",
        ).grid(row=0, column=1, padx=8, pady=8, sticky="ew")

        def edit():
            self._open_edit(u)

        def delete():
            if self.on_delete_user(u["id"]):
                self.status.configure(text="تم حذف المستخدم", text_color="#27ae60")
                self.refresh()
            else:
                self.status.configure(text="تعذر الحذف (مستخدمك أو آخر مسؤول)", text_color="#e74c3c")

        ctk.CTkButton(
            row, text="تعديل", width=72, height=28, font=("Arial", 11), command=edit
        ).grid(row=0, column=0, padx=(8, 4), pady=8, sticky="e")
        ctk.CTkButton(
            row,
            text="حذف",
            width=72,
            height=28,
            font=("Arial", 11),
            fg_color="#c0392b",
            hover_color="#a93226",
            command=delete,
        ).grid(row=0, column=3, padx=(4, 8), pady=8, sticky="e")

        ctk.CTkLabel(
            row,
            text=f"آخر دخول: {_format_last_login(u.get('last_login'))}",
            font=("Arial", 11),
            text_color="#888888",
            anchor="e",
        ).grid(row=1, column=0, columnspan=4, padx=10, pady=(0, 8), sticky="ew")

    def _open_add(self):
        def save(_uid, username, role, pw):
            if pw and self.on_add_user(username, pw, role):
                self.status.configure(text="تم إنشاء المستخدم", text_color="#27ae60")
                self.refresh()
            elif not pw:
                self.status.configure(text="كلمة المرور مطلوبة", text_color="#e74c3c")
            else:
                self.status.configure(text="فشل الإنشاء (اسم مستخدم مكرر؟)", text_color="#e74c3c")

        AddEditUserModal(self.winfo_toplevel(), on_save=save)

    def _open_edit(self, u: Dict):
        def save(uid, username, role, pw):
            if self.on_update_user(uid, username, role, pw):
                self.status.configure(text="تم التحديث", text_color="#27ae60")
                self.refresh()
            else:
                self.status.configure(text="فشل التحديث", text_color="#e74c3c")

        AddEditUserModal(self.winfo_toplevel(), on_save=save, user=u)
