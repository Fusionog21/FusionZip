"""
===============================================================================
FUSION ZIP — Advanced Desktop Zip Engine & Custom UI
===============================================================================
"""

import os
import sys
import time
import json
import socket
import shutil
import hashlib
import zipfile
import tarfile
import threading
import datetime
import tempfile
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

# Register AppUserModelID for Windows Taskbar & Titlebar Icons
if sys.platform == "win32":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FusionZip.DesktopApp.1.0")
    except Exception:
        pass

# Modern UI Engine
try:
    import customtkinter as ctk
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
except ImportError:
    messagebox.showerror(
        "Missing Dependency",
        "CustomTkinter is required.\nPlease run: pip install customtkinter pyzipper py7zr rarfile"
    )
    sys.exit(1)

# AES Encryption Support
try:
    import pyzipper
    HAS_PYZIPPER = True
except ImportError:
    HAS_PYZIPPER = False

# Header-Encryption (7z/Vault) Engine Support
try:
    import py7zr
    HAS_PY7ZR = True
except ImportError:
    HAS_PY7ZR = False

# RAR Archive Support
try:
    import rarfile
    HAS_RARFILE = True
except ImportError:
    HAS_RARFILE = False

# Windows Registry Support
try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

# Local Single-Instance IPC Port
IPC_PORT = 49152

# =============================================================================
# COLOR PALETTE & FONT CONSTANTS
# =============================================================================
COLOR_BG_DARK       = "#0f121d"  # Main window dark navy
COLOR_CARD_BG       = "#181c2b"  # Rounded container cards
COLOR_FIELD_BG      = "#121522"  # Data list / Input fields
COLOR_BLUE_ACCENT   = "#3b82f6"  # Vibrant action blue
COLOR_BLUE_HOVER    = "#2563eb"  # Darker blue hover
COLOR_TEXT_PRIMARY  = "#ffffff"  # Crisp white text
COLOR_TEXT_MUTED    = "#a0a8c4"  # Soft readable gray-blue text
COLOR_TEXT_DISABLED = "#4f5673"  # Disabled text
COLOR_TEXT_ALERT    = "#ef4444"  # Warning red text

FONT_FAMILY         = "Segoe UI"


# =============================================================================
# APPLICATION ICON HELPER FOR MAIN & POPUP WINDOWS
# =============================================================================
def apply_app_icon(window):
    """Locates and applies icon.ico to any main window or popup dialog."""
    icon_paths = []
    if hasattr(sys, '_MEIPASS'):
        icon_paths.append(os.path.join(sys._MEIPASS, "icon.ico"))
    icon_paths.append(os.path.join(os.path.dirname(sys.executable), "icon.ico"))
    icon_paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico"))
    icon_paths.append(os.path.join(os.getcwd(), "icon.ico"))

    for icon_path in icon_paths:
        if os.path.exists(icon_path):
            try:
                window.iconbitmap(icon_path)
                window.after(100, lambda p=icon_path: window.iconbitmap(p))
                return
            except Exception:
                pass


# =============================================================================
# WINDOWS CTYPES DEFINITIONS (64-BIT SAFE)
# =============================================================================
if sys.platform == "win32":
    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32

    shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
    shell32.DragAcceptFiles.restype = None

    shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
    shell32.DragQueryFileW.restype = wintypes.UINT

    shell32.DragFinish.argtypes = [wintypes.HANDLE]
    shell32.DragFinish.restype = None

    if hasattr(user32, "GetWindowLongPtrW"):
        GetWindowLongPtr = user32.GetWindowLongPtrW
        SetWindowLongPtr = user32.SetWindowLongPtrW
    else:
        GetWindowLongPtr = user32.GetWindowLongW
        SetWindowLongPtr = user32.SetWindowLongW

    GetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int]
    GetWindowLongPtr.restype = ctypes.c_void_p

    SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    SetWindowLongPtr.restype = ctypes.c_void_p

    user32.CallWindowProcW.argtypes = [
        ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
    ]
    user32.CallWindowProcW.restype = ctypes.c_void_p


def apply_windows_dark_titlebar(window):
    """Enforces dark mode title bar on Windows 10/11."""
    if sys.platform != "win32":
        return
    try:
        window.update()
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        hwnd = user32.GetParent(window.winfo_id())
        if hwnd == 0:
            hwnd = window.winfo_id()
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:
        pass


def center_window_on_screen(window, width, height):
    """Calculates coordinates to center any window dead-center on screen."""
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = max(0, (screen_width // 2) - (width // 2))
    y = max(0, (screen_height // 2) - (height // 2))
    window.geometry(f"{width}x{height}+{x}+{y}")


def enable_windows_dnd(window, callback):
    """64-bit memory-safe Drag & Drop hook for Windows."""
    if sys.platform != "win32":
        return
    try:
        window.update()
        hwnd = user32.GetParent(window.winfo_id())
        if hwnd == 0:
            hwnd = window.winfo_id()

        shell32.DragAcceptFiles(hwnd, True)
        GWL_WNDPROC = -4
        WM_DROPFILES = 0x0233

        old_wndproc = GetWindowLongPtr(hwnd, GWL_WNDPROC)
        WNDPROC_TYPE = ctypes.WINFUNCTYPE(
            ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
        )

        def py_wndproc(hWnd, msg, wParam, lParam):
            if msg == WM_DROPFILES:
                hDrop = wParam
                count = shell32.DragQueryFileW(hDrop, 0xFFFFFFFF, None, 0)
                files = []
                for i in range(count):
                    buf_len = shell32.DragQueryFileW(hDrop, i, None, 0) + 1
                    buf = ctypes.create_unicode_buffer(buf_len)
                    shell32.DragQueryFileW(hDrop, i, buf, buf_len)
                    files.append(buf.value)
                shell32.DragFinish(hDrop)
                window.after(10, lambda: callback(files))
                return 0
            return user32.CallWindowProcW(old_wndproc, hWnd, msg, wParam, lParam)

        new_wndproc = WNDPROC_TYPE(py_wndproc)
        SetWindowLongPtr(hwnd, GWL_WNDPROC, new_wndproc)
        window._dnd_wndproc = new_wndproc
    except Exception as e:
        print(f"DnD hook error: {e}")


# =============================================================================
# ARCHIVE ENCRYPTION DETECTOR
# =============================================================================
def check_archive_encrypted(archive_path):
    """Returns True ONLY if the archive file requires a password to open or extract."""
    if not os.path.exists(archive_path) or os.path.isdir(archive_path):
        return False

    ext = os.path.splitext(archive_path)[1].lower()
    if ext not in [".zip", ".7z", ".fz", ".fzip", ".rar"]:
        return False

    try:
        if ext in [".7z", ".fz", ".fzip"] and HAS_PY7ZR:
            if not py7zr.is_7zfile(archive_path):
                return False
            try:
                with py7zr.SevenZipFile(archive_path, 'r') as szf:
                    return szf.needs_password
            except py7zr.PasswordRequired:
                return True
            except Exception:
                return False

        elif ext == ".rar" and HAS_RARFILE:
            rf = rarfile.RarFile(archive_path, 'r')
            is_req = rf.needs_password()
            rf.close()
            return is_req

        elif ext in [".zip", ".fz", ".fzip"]:
            zf = pyzipper.AESZipFile(archive_path, 'r') if HAS_PYZIPPER else zipfile.ZipFile(archive_path, 'r')
            is_req = False
            for zinfo in zf.infolist():
                if zinfo.flag_bits & 0x1:
                    is_req = True
                    break
            zf.close()
            return is_req
    except Exception:
        return False
    return False


# =============================================================================
# CONFLICT STATE HELPER & POPUP INTERCEPTOR
# =============================================================================
class ConflictState:
    def __init__(self):
        self.action = None
        self.apply_to_all = False

def prompt_file_conflict(filename, conflict_state):
    """Pops up the Conflict Resolution Dialog whenever a duplicate file or folder is found."""
    if conflict_state.apply_to_all and conflict_state.action:
        return conflict_state.action

    app = ctk.CTk()
    app.withdraw()
    result = [None, False]

    def on_choice(choice, apply_all):
        result[0] = choice
        result[1] = apply_all
        app.destroy()

    dialog = FileConflictDialog(app, filename, on_choice)
    dialog.protocol("WM_DELETE_WINDOW", lambda: app.destroy())
    app.mainloop()

    choice = result[0] or "skip"
    if result[1]:
        conflict_state.apply_to_all = True
        conflict_state.action = choice
    return choice


# =============================================================================
# UPGRADED SLEEK HOVER TOOLTIP MODULE
# =============================================================================
class FloatingTooltip:
    """Creates a modern dark floating description badge matching the app card theme."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.configure(bg=COLOR_BG_DARK)

        frame = tk.Frame(
            tw, background=COLOR_CARD_BG,
            highlightbackground="#2b314d", highlightthickness=1, padx=2, pady=2
        )
        frame.pack()

        label = tk.Label(
            frame, text=self.text, justify=tk.LEFT,
            background=COLOR_CARD_BG, foreground=COLOR_TEXT_PRIMARY,
            relief=tk.FLAT, borderwidth=0,
            font=(FONT_FAMILY, 9), padx=8, pady=4
        )
        label.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# =============================================================================
# TOAST NOTIFICATION POPUP DIALOG
# =============================================================================
class ToastNotification(ctk.CTkToplevel):
    def __init__(self, title, message):
        super().__init__()
        ctk.set_appearance_mode("Dark")
        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient()

        apply_app_icon(self)
        center_window_on_screen(self, 460, 180)
        apply_windows_dark_titlebar(self)

        card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=0)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        hdr_lbl = ctk.CTkLabel(
            card, text=f"✓ {title}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_BLUE_ACCENT
        )
        hdr_lbl.pack(anchor="w", padx=15, pady=(12, 4))

        msg_lbl = ctk.CTkLabel(
            card, text=message,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color="#FFFFFF",
            justify="left", wraplength=410
        )
        msg_lbl.pack(anchor="w", padx=15, pady=(0, 12))

        btn_ok = ctk.CTkButton(
            card, text="OK", fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER,
            text_color="#FFFFFF", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=75, height=28, command=self.destroy
        )
        btn_ok.pack(side="right", padx=15, pady=(0, 10))


def show_toast(title, message):
    app = ctk.CTk()
    app.withdraw()
    toast = ToastNotification(title, message)
    toast.protocol("WM_DELETE_WINDOW", lambda: app.destroy())
    app.mainloop()


# =============================================================================
# FILE CONFLICT RESOLUTION MODAL DIALOG
# =============================================================================
class FileConflictDialog(ctk.CTkToplevel):
    def __init__(self, parent, filename, callback):
        super().__init__(parent)
        ctk.set_appearance_mode("Dark")
        self.filename = filename
        self.callback = callback
        self.choice = None
        self.apply_to_all = False

        self.title("Item Name Collision")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.grab_set()

        apply_app_icon(self)
        center_window_on_screen(self, 440, 240)
        apply_windows_dark_titlebar(self)

        card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=0)
        card.pack(fill="both", expand=True, padx=15, pady=15)

        is_directory = os.path.isdir(filename)
        item_type_str = "Folder" if is_directory else "File"

        hdr_lbl = ctk.CTkLabel(
            card, text=f"⚠️ {item_type_str} Already Exists",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color="#FFFFFF"
        )
        hdr_lbl.pack(anchor="w", padx=15, pady=(12, 2))

        sub_lbl = ctk.CTkLabel(
            card, text=f"The {item_type_str.lower()} '{os.path.basename(filename)[:35]}' already exists.\nSelect how you want to proceed:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color="#A0A8C4", justify="left"
        )
        sub_lbl.pack(anchor="w", padx=15, pady=(0, 10))

        self.chk_all_var = ctk.BooleanVar(value=False)
        chk_all = ctk.CTkCheckBox(
            card, text="Apply to all remaining conflicts", variable=self.chk_all_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color="#A0A8C4",
            fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER
        )
        chk_all.pack(anchor="w", padx=15, pady=(0, 12))

        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=(4, 12))

        btn_replace = ctk.CTkButton(
            btn_box, text="🔄 Replace", fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER,
            text_color="#FFFFFF", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=90, height=32, command=lambda: self._select("replace")
        )
        btn_replace.pack(side="left", padx=(0, 4))

        btn_rename = ctk.CTkButton(
            btn_box, text="📋 Keep Both", fg_color=COLOR_FIELD_BG, hover_color="#24283b",
            text_color="#FFFFFF", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=95, height=32, command=lambda: self._select("keep_both")
        )
        btn_rename.pack(side="left", padx=4)

        btn_skip = ctk.CTkButton(
            btn_box, text="⏭️ Skip", fg_color=COLOR_FIELD_BG, hover_color="#24283b",
            text_color="#A0A8C4", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=80, height=32, command=lambda: self._select("skip")
        )
        btn_skip.pack(side="left", padx=(4, 0))

    def _select(self, action):
        self.choice = action
        self.apply_to_all = self.chk_all_var.get()
        self.destroy()
        if self.callback:
            self.callback(action, self.apply_to_all)


# =============================================================================
# ENCRYPTED ARCHIVE DIALOG
# =============================================================================
class EncryptedArchiveDialog(ctk.CTkToplevel):
    def __init__(self, parent, archive_path, callback):
        super().__init__(parent)
        ctk.set_appearance_mode("Dark")

        self.archive_path = os.path.abspath(archive_path)
        self.callback = callback
        self.unlocked_password = None

        self.title("Encrypted Archive")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.grab_set()

        apply_app_icon(self)
        center_window_on_screen(self, 420, 230)
        apply_windows_dark_titlebar(self)

        card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=0)
        card.pack(fill="both", expand=True, padx=15, pady=15)

        hdr_lbl = ctk.CTkLabel(
            card, text="⚠️ Encrypted Archive Detected",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color="#FFFFFF"
        )
        hdr_lbl.pack(anchor="w", padx=15, pady=(12, 2))

        sub_lbl = ctk.CTkLabel(
            card, text=f"The archive '{os.path.basename(self.archive_path)[:30]}' is password protected.\nEnter password to unlock:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color="#A0A8C4", justify="left"
        )
        sub_lbl.pack(anchor="w", padx=15, pady=(0, 10))

        pwd_row = ctk.CTkFrame(card, fg_color="transparent")
        pwd_row.pack(fill="x", padx=15, pady=5)

        self.pwd_entry = ctk.CTkEntry(
            pwd_row, show="•", fg_color=COLOR_FIELD_BG, text_color="#FFFFFF",
            border_width=0, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            placeholder_text="Enter Password..."
        )
        self.pwd_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.pwd_entry.focus_set()
        self.pwd_entry.bind("<Return>", lambda e: self.attempt_unlock())

        self.btn_toggle = ctk.CTkButton(
            pwd_row, text="👁️", fg_color=COLOR_FIELD_BG, hover_color="#24283b",
            text_color="#A0A8C4", width=32, height=32, font=ctk.CTkFont(size=12),
            command=self.toggle_password
        )
        self.btn_toggle.pack(side="right")

        self.err_lbl = ctk.CTkLabel(
            card, text="", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_ALERT
        )
        self.err_lbl.pack(anchor="w", padx=15, pady=(2, 0))

        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=(8, 12))

        btn_cancel = ctk.CTkButton(
            btn_box, text="Cancel", fg_color=COLOR_FIELD_BG, hover_color="#24283b",
            text_color="#A0A8C4", font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            width=80, height=32, command=self.destroy
        )
        btn_cancel.pack(side="right", padx=(6, 0))

        self.btn_unlock = ctk.CTkButton(
            btn_box, text="🔓 UNLOCK", fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER,
            text_color="#FFFFFF", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            width=100, height=32, command=self.attempt_unlock
        )
        self.btn_unlock.pack(side="right")

    def toggle_password(self):
        if self.pwd_entry.cget("show") == "•":
            self.pwd_entry.configure(show="")
            self.btn_toggle.configure(text="🔒")
        else:
            self.pwd_entry.configure(show="•")
            self.btn_toggle.configure(text="👁️")

    def attempt_unlock(self):
        pwd = self.pwd_entry.get().strip()
        if not pwd:
            self.err_lbl.configure(text="Password cannot be empty.")
            return

        try:
            ext = os.path.splitext(self.archive_path)[1].lower()

            if ext in [".7z", ".fz", ".fzip"]:
                if HAS_PY7ZR:
                    with py7zr.SevenZipFile(self.archive_path, 'r', password=pwd) as szf:
                        szf.getnames()
                else:
                    raise Exception("py7zr required.")
            elif ext == ".rar":
                if HAS_RARFILE:
                    rf = rarfile.RarFile(self.archive_path, 'r')
                    rf.setpassword(pwd)
                    rf.namelist()
                    rf.close()
                else:
                    raise Exception("rarfile required.")
            else:
                zf = pyzipper.AESZipFile(self.archive_path, 'r') if HAS_PYZIPPER else zipfile.ZipFile(self.archive_path, 'r')
                zf.setpassword(pwd.encode('utf-8'))
                bad = zf.testzip()
                zf.close()
                if bad is not None and HAS_PYZIPPER:
                    raise Exception("Incorrect password")

            self.unlocked_password = pwd
            self.destroy()
            if self.callback:
                self.callback(self.archive_path, pwd)
        except Exception:
            self.err_lbl.configure(text="Incorrect password. Please try again.")


# =============================================================================
# ADD TO ARCHIVE CONFIGURATION DIALOG
# =============================================================================
class AddToArchiveDialog(ctk.CTkToplevel):
    def __init__(self, parent, targets, default_target_dir, callback):
        super().__init__(parent)
        ctk.set_appearance_mode("Dark")

        self.targets = targets
        self.default_target_dir = default_target_dir or os.path.dirname(os.path.abspath(targets[0]))
        self.callback = callback

        first_base = os.path.basename(os.path.abspath(targets[0]))
        if len(targets) > 1 and not os.path.isdir(targets[0]):
            default_archive_name = "New_Archive.zip"
        else:
            default_archive_name = f"{os.path.splitext(first_base)[0]}.zip"

        self.title("Add to Archive")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.grab_set()

        apply_app_icon(self)
        center_window_on_screen(self, 500, 350)
        apply_windows_dark_titlebar(self)

        card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=0)
        card.pack(fill="both", expand=True, padx=15, pady=15)

        hdr_lbl = ctk.CTkLabel(
            card, text="🗜️ Create Compressed Archive",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color="#FFFFFF"
        )
        hdr_lbl.pack(anchor="w", padx=15, pady=(12, 2))

        sub_lbl = ctk.CTkLabel(
            card, text="Type a custom name and destination for your new zip file:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color="#A0A8C4", justify="left"
        )
        sub_lbl.pack(anchor="w", padx=15, pady=(0, 10))

        # Archive Name Entry
        ctk.CTkLabel(card, text="Archive Name:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#A0A8C4").pack(anchor="w", padx=15, pady=(2, 0))
        self.name_entry = ctk.CTkEntry(
            card, fg_color=COLOR_FIELD_BG, text_color="#FFFFFF",
            border_width=0, corner_radius=6, font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.name_entry.pack(fill="x", padx=15, pady=(2, 8))
        self.name_entry.insert(0, default_archive_name)

        # Save Location Entry + Browse
        ctk.CTkLabel(card, text="Save Location:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#A0A8C4").pack(anchor="w", padx=15, pady=(2, 0))
        loc_row = ctk.CTkFrame(card, fg_color="transparent")
        loc_row.pack(fill="x", padx=15, pady=(2, 8))

        self.loc_entry = ctk.CTkEntry(
            loc_row, fg_color=COLOR_FIELD_BG, text_color="#FFFFFF",
            border_width=0, corner_radius=6, font=ctk.CTkFont(family=FONT_FAMILY, size=11)
        )
        self.loc_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.loc_entry.insert(0, self.default_target_dir)

        btn_browse = ctk.CTkButton(
            loc_row, text="Browse...", fg_color=COLOR_FIELD_BG, hover_color="#24283b",
            text_color="#A0A8C4", font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=70, height=28, command=self.browse_location
        )
        btn_browse.pack(side="right")

        # Password Entry
        pwd_row = ctk.CTkFrame(card, fg_color="transparent")
        pwd_row.pack(fill="x", padx=15, pady=(2, 10))

        ctk.CTkLabel(pwd_row, text="Password:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#A0A8C4").pack(side="left", padx=(0, 6))
        self.pwd_entry = ctk.CTkEntry(
            pwd_row, show="•", fg_color=COLOR_FIELD_BG, text_color="#FFFFFF",
            border_width=0, corner_radius=6, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            placeholder_text="Optional Password..."
        )
        self.pwd_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_toggle = ctk.CTkButton(
            pwd_row, text="👁️", fg_color=COLOR_FIELD_BG, hover_color="#24283b",
            text_color="#A0A8C4", width=30, height=28, font=ctk.CTkFont(size=12),
            command=self.toggle_pwd
        )
        self.btn_toggle.pack(side="right")

        # Buttons
        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=(12, 15))

        btn_cancel = ctk.CTkButton(
            btn_box, text="Cancel", fg_color=COLOR_FIELD_BG, hover_color="#24283b",
            text_color="#A0A8C4", font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            width=80, height=32, command=self.destroy
        )
        btn_cancel.pack(side="right", padx=(6, 0))

        btn_compress = ctk.CTkButton(
            btn_box, text="🗜️ COMPRESS", fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER,
            text_color="#FFFFFF", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            width=110, height=32, command=self.start_compress
        )
        btn_compress.pack(side="right")

    def toggle_pwd(self):
        if self.pwd_entry.cget("show") == "•":
            self.pwd_entry.configure(show="")
            self.btn_toggle.configure(text="🔒")
        else:
            self.pwd_entry.configure(show="•")
            self.btn_toggle.configure(text="👁️")

    def browse_location(self):
        folder = filedialog.askdirectory(title="Select Save Location", initialdir=self.loc_entry.get())
        if folder:
            self.loc_entry.delete(0, tk.END)
            self.loc_entry.insert(0, folder)

    def start_compress(self):
        archive_name = self.name_entry.get().strip()
        save_dir = self.loc_entry.get().strip()
        password = self.pwd_entry.get().strip()

        if not archive_name:
            return
        if not archive_name.lower().endswith((".zip", ".fzip")):
            archive_name += ".zip"

        self.destroy()
        if self.callback:
            self.callback(archive_name, save_dir, password)


# =============================================================================
# CLI COMPRESSION PROGRESS DIALOG (WITH REAL AES-256 ENCRYPTION & AUTO-CLOSE)
# =============================================================================
class CLICompressionProgressDialog(ctk.CTkToplevel):
    def __init__(self, parent, targets, archive_name, target_dir, password):
        super().__init__(parent)
        ctk.set_appearance_mode("Dark")

        self.targets = targets
        self.archive_name = archive_name
        self.target_dir = target_dir
        self.password = password
        self.is_cancelled = False

        self.title("Compressing Archive...")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.grab_set()

        apply_app_icon(self)
        center_window_on_screen(self, 460, 200)
        apply_windows_dark_titlebar(self)

        card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=0)
        card.pack(fill="both", expand=True, padx=15, pady=15)

        hdr_lbl = ctk.CTkLabel(
            card, text=f"🗜️ Packaging '{archive_name[:30]}'...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color="#FFFFFF"
        )
        hdr_lbl.pack(anchor="w", padx=15, pady=(12, 4))

        self.progress_bar = ctk.CTkProgressBar(
            card, fg_color=COLOR_FIELD_BG, progress_color=COLOR_BLUE_ACCENT, height=10
        )
        self.progress_bar.pack(fill="x", padx=15, pady=(4, 8))
        self.progress_bar.set(0)

        self.lbl_file = ctk.CTkLabel(
            card, text="Processing...", font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color="#A0A8C4", anchor="w"
        )
        self.lbl_file.pack(fill="x", padx=15, pady=(2, 0))

        self.lbl_stats = ctk.CTkLabel(
            card, text="Preparing files...", font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color="#A0A8C4", anchor="w"
        )
        self.lbl_stats.pack(fill="x", padx=15, pady=(0, 10))

        threading.Thread(target=self._run_compress_task, daemon=True).start()

    def _run_compress_task(self):
        os.makedirs(self.target_dir, exist_ok=True)

        if self.password and not self.archive_name.lower().endswith((".fzip", ".7z")):
            if self.archive_name.lower().endswith(".zip"):
                self.archive_name = self.archive_name[:-4] + ".fzip"
            else:
                self.archive_name += ".fzip"

        out_abs = os.path.join(self.target_dir, self.archive_name)

        total_bytes = 0
        valid_files = [x for x in self.targets if os.path.exists(x)]
        for target in valid_files:
            if os.path.isfile(target):
                total_bytes += os.path.getsize(target)
            elif os.path.isdir(target):
                for root, dirs, files in os.walk(target):
                    for f in files:
                        total_bytes += os.path.getsize(os.path.join(root, f))

        processed_bytes = 0
        start_time = time.time()

        try:
            if self.password and HAS_PY7ZR:
                filters = [
                    {'id': py7zr.FILTER_LZMA2},
                    {'id': py7zr.FILTER_CRYPTO_AES256_SHA256}
                ]
                with py7zr.SevenZipFile(out_abs, 'w', password=self.password, header_encryption=True, filters=filters) as szf:
                    for target in valid_files:
                        if self.is_cancelled: break
                        target_abs = os.path.abspath(target)
                        if target_abs == out_abs: continue

                        if os.path.isfile(target_abs):
                            file_size = os.path.getsize(target_abs)
                            processed_bytes += file_size
                            self._update_progress(processed_bytes, total_bytes, start_time, os.path.basename(target_abs))
                            szf.write(target_abs, os.path.basename(target_abs))

                        elif os.path.isdir(target_abs):
                            for root, dirs, files in os.walk(target_abs):
                                if self.is_cancelled: break
                                for file in files:
                                    full_p = os.path.abspath(os.path.join(root, file))
                                    if full_p == out_abs: continue
                                    file_size = os.path.getsize(full_p)
                                    processed_bytes += file_size
                                    rel_p = os.path.relpath(full_p, os.path.dirname(target_abs))
                                    self._update_progress(processed_bytes, total_bytes, start_time, file)
                                    szf.write(full_p, rel_p)
            else:
                zf = zipfile.ZipFile(out_abs, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1)
                for target in valid_files:
                    if self.is_cancelled: break
                    target_abs = os.path.abspath(target)
                    if target_abs == out_abs: continue

                    if os.path.isfile(target_abs):
                        file_size = os.path.getsize(target_abs)
                        processed_bytes += file_size
                        self._update_progress(processed_bytes, total_bytes, start_time, os.path.basename(target_abs))
                        zf.write(target_abs, os.path.basename(target_abs))

                    elif os.path.isdir(target_abs):
                        for root, dirs, files in os.walk(target_abs):
                            if self.is_cancelled: break
                            for file in files:
                                full_p = os.path.abspath(os.path.join(root, file))
                                if full_p == out_abs: continue
                                file_size = os.path.getsize(full_p)
                                processed_bytes += file_size
                                rel_p = os.path.relpath(full_p, os.path.dirname(target_abs))
                                self._update_progress(processed_bytes, total_bytes, start_time, file)
                                zf.write(full_p, rel_p)
                zf.close()

            # Auto-close live progress window cleanly when done
            self.after(0, self.destroy)

        except Exception as e:
            self.after(0, self.destroy)
            show_toast("Error", f"Compression failed: {e}")

    def _update_progress(self, current_b, total_b, start_t, name):
        pct = (current_b / total_b) if total_b > 0 else 0.99
        if pct >= 1.0: pct = 0.99

        elapsed = max(0.001, time.time() - start_t)
        speed = current_b / elapsed
        rem_bytes = max(0, total_b - current_b)
        rem_seconds = int(rem_bytes / speed) if speed > 0 else 0
        mins, secs = divmod(rem_seconds, 60)

        cur_mb = round(current_b / (1024 * 1024), 1)
        tot_mb = round(total_b / (1024 * 1024), 1)
        speed_mb = round(speed / (1024 * 1024), 1)

        self.after(0, lambda: self.progress_bar.set(pct))
        self.after(0, lambda: self.lbl_file.configure(text=f"Processing: {name[:30]} ({int(pct*100)}%)"))
        self.after(0, lambda: self.lbl_stats.configure(
            text=f"Size: {cur_mb} MB / {tot_mb} MB  |  Speed: {speed_mb} MB/s  |  Est: {mins:02d}:{secs:02d}"
        ))


# =============================================================================
# MAIN GUI APPLICATION CLASS
# =============================================================================
class FusionZipApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Fusion Zip")
        self.minsize(780, 500)
        self.resizable(True, True)
        self.configure(fg_color=COLOR_BG_DARK)

        apply_app_icon(self)
        center_window_on_screen(self, 860, 560)
        apply_windows_dark_titlebar(self)

        # Application State
        self.queue_items = []
        self.current_folder_view = None
        self.last_output_dir = None
        self.is_processing = False

        # Build UI Components
        self._build_top_bar()
        self._build_data_grid()
        self._build_linear_control_row()
        self._build_status_and_progress_strip()

        enable_windows_dnd(self, self.on_files_dropped)
        self._refresh_grid()

    def _build_top_bar(self):
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(15, 10))

        self.btn_add = ctk.CTkButton(
            top_frame, text="➕ ADD ITEMS", fg_color="#1f2438", hover_color="#2b314d",
            text_color=COLOR_BLUE_ACCENT, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            corner_radius=8, height=36, command=self.add_items_dialog
        )
        self.btn_add.pack(side="left")
        FloatingTooltip(self.btn_add, "Browse files or folders into your staging queue.")

        self.lbl_location = ctk.CTkLabel(
            top_frame, text="", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED
        )
        self.lbl_location.pack(side="right", padx=10)

    def _build_data_grid(self):
        self.grid_card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=0)
        self.grid_card.pack(fill="both", expand=True, padx=20, pady=5)

        self.hdr_frame = ctk.CTkFrame(self.grid_card, fg_color=COLOR_FIELD_BG, corner_radius=8, height=32, border_width=0)
        self.hdr_frame.pack(fill="x", padx=12, pady=(12, 6))

        hdr_name = ctk.CTkLabel(self.hdr_frame, text="Name 🔼", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED, anchor="w")
        hdr_name.pack(side="left", padx=15, expand=True, fill="x")

        hdr_size = ctk.CTkLabel(self.hdr_frame, text="Size", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED, width=100, anchor="e")
        hdr_size.pack(side="left", padx=10)

        hdr_type = ctk.CTkLabel(self.hdr_frame, text="Type", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED, width=90, anchor="center")
        hdr_type.pack(side="left", padx=10)

        hdr_date = ctk.CTkLabel(self.hdr_frame, text="Date Modified", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED, width=120, anchor="center")
        hdr_date.pack(side="left", padx=10)

        hdr_del = ctk.CTkLabel(self.hdr_frame, text="Remove", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED, width=60, anchor="center")
        hdr_del.pack(side="left", padx=(10, 15))

        self.scroll_frame = ctk.CTkScrollableFrame(
            self.grid_card, fg_color="transparent", corner_radius=0,
            border_width=0, scrollbar_button_color="#282e44", scrollbar_button_hover_color=COLOR_BLUE_ACCENT
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _build_linear_control_row(self):
        ctrl_card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=0)
        ctrl_card.pack(fill="x", padx=20, pady=8)

        inner_row = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        inner_row.pack(fill="x", padx=15, pady=12)

        left_box = ctk.CTkFrame(inner_row, fg_color="transparent")
        left_box.pack(side="left", anchor="w")

        # Archive Name Field
        name_frame = ctk.CTkFrame(left_box, fg_color="transparent")
        name_frame.pack(anchor="w", side="left", padx=(0, 15))

        ctk.CTkLabel(name_frame, text="Archive Name:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 6))

        self.archive_name_entry = ctk.CTkEntry(
            name_frame, fg_color=COLOR_FIELD_BG, text_color=COLOR_TEXT_PRIMARY,
            border_width=0, corner_radius=6, width=160, height=30, placeholder_text="Archive.zip"
        )
        self.archive_name_entry.pack(side="left")
        FloatingTooltip(self.archive_name_entry, "Type a custom name for your compressed zip file.")

        # Password Field
        pwd_frame = ctk.CTkFrame(left_box, fg_color="transparent")
        pwd_frame.pack(anchor="w", side="left")

        ctk.CTkLabel(pwd_frame, text="Password:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 6))

        self.pwd_entry = ctk.CTkEntry(
            pwd_frame, show="•", fg_color=COLOR_FIELD_BG, text_color=COLOR_TEXT_PRIMARY,
            border_width=0, corner_radius=6, width=140, height=30, placeholder_text="Optional Password"
        )
        self.pwd_entry.pack(side="left")
        FloatingTooltip(self.pwd_entry, "Typing a password locks both file contents and file names.")

        self.btn_toggle_pwd = ctk.CTkButton(
            pwd_frame, text="👁️", fg_color="transparent", hover_color=COLOR_FIELD_BG,
            text_color=COLOR_TEXT_MUTED, width=30, height=30, font=ctk.CTkFont(size=12),
            command=self.toggle_password_visibility
        )
        self.btn_toggle_pwd.pack(side="left", padx=(2, 0))

        right_box = ctk.CTkFrame(inner_row, fg_color="transparent")
        right_box.pack(side="right", anchor="e")

        self.btn_compress = ctk.CTkButton(
            right_box, text="COMPRESS", fg_color=COLOR_FIELD_BG, hover_color=COLOR_FIELD_BG,
            text_color=COLOR_TEXT_DISABLED, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            corner_radius=8, height=38, width=120, state="disabled", command=self.start_compression_thread
        )
        self.btn_compress.pack(side="left", padx=6)

        self.btn_extract = ctk.CTkButton(
            right_box, text="EXTRACT", fg_color=COLOR_FIELD_BG, hover_color=COLOR_FIELD_BG,
            text_color=COLOR_TEXT_DISABLED, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            corner_radius=8, height=38, width=120, state="disabled", command=self.start_extraction_thread
        )
        self.btn_extract.pack(side="left", padx=6)

    def _build_status_and_progress_strip(self):
        self.status_strip = ctk.CTkFrame(self, fg_color="transparent")
        self.status_strip.pack(fill="x", padx=20, pady=(0, 10))

        self.lbl_status = ctk.CTkLabel(
            self.status_strip, text="Ready | 0 items queued",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_MUTED
        )
        self.lbl_status.pack(side="left")

        self.btn_open_folder = ctk.CTkButton(
            self.status_strip, text="📁 Open Folder", fg_color=COLOR_CARD_BG, hover_color="#282e44",
            text_color=COLOR_BLUE_ACCENT, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=24, width=90, command=self.open_output_folder
        )

        self.progress_bar = ctk.CTkProgressBar(
            self.status_strip, fg_color=COLOR_CARD_BG, progress_color=COLOR_BLUE_ACCENT, height=8, width=240
        )

    def toggle_password_visibility(self):
        if self.pwd_entry.cget("show") == "•":
            self.pwd_entry.configure(show="")
            self.btn_toggle_pwd.configure(text="🔒")
        else:
            self.pwd_entry.configure(show="•")
            self.btn_toggle_pwd.configure(text="👁️")

    def add_items_dialog(self):
        files = filedialog.askopenfilenames(title="Select Files to Add")
        if files:
            for f in files:
                if not any(x["path"] == f for x in self.queue_items):
                    self.queue_items.append({"path": f})
            self._refresh_grid()

    def on_files_dropped(self, file_paths):
        added = False
        for p in file_paths:
            clean_p = p.strip("{}")
            if os.path.exists(clean_p) and not any(x["path"] == clean_p for x in self.queue_items):
                self.queue_items.append({"path": clean_p})
                added = True
        if added:
            self._refresh_grid()

    def remove_item(self, target_path):
        self.queue_items = [x for x in self.queue_items if x["path"] != target_path]
        self._refresh_grid()

    def open_output_folder(self):
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            os.startfile(self.last_output_dir)

    def inspect_folder(self, folder_path):
        self.current_folder_view = folder_path
        self._refresh_grid()

    def inspect_archive(self, archive_path):
        if check_archive_encrypted(archive_path):
            EncryptedArchiveDialog(self, archive_path, self._on_archive_unlocked)
        else:
            self.current_folder_view = archive_path
            self._refresh_grid()

    def _on_archive_unlocked(self, archive_path, password):
        self.pwd_entry.delete(0, tk.END)
        self.pwd_entry.insert(0, password)
        self.current_folder_view = archive_path
        self._refresh_grid()

    def step_up_folder(self):
        """Fixes GUI navigation: Stepping up from a top-level queued item returns to main staging queue."""
        if self.current_folder_view:
            if any(os.path.abspath(self.current_folder_view) == os.path.abspath(x["path"]) for x in self.queue_items):
                self.current_folder_view = None
            else:
                parent = os.path.dirname(self.current_folder_view)
                if parent and any(os.path.abspath(self.current_folder_view).startswith(os.path.abspath(x["path"])) for x in self.queue_items):
                    self.current_folder_view = parent
                else:
                    self.current_folder_view = None
            self._refresh_grid()

    def _refresh_grid(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if self.current_folder_view:
            self.lbl_location.configure(text=f"📍 Location: {self.current_folder_view}")
            up_row = ctk.CTkFrame(self.scroll_frame, fg_color=COLOR_CARD_BG, corner_radius=6, border_width=0)
            up_row.pack(fill="x", pady=2)

            up_lbl = ctk.CTkLabel(
                up_row, text="📁 [ .. Up One Level ]", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=COLOR_BLUE_ACCENT, anchor="w"
            )
            up_lbl.pack(side="left", padx=12, pady=6)
            up_row.bind("<Double-1>", lambda e: self.step_up_folder())
            up_lbl.bind("<Double-1>", lambda e: self.step_up_folder())

            try:
                pwd = self.pwd_entry.get().strip() or None
                ext = os.path.splitext(self.current_folder_view)[1].lower()

                if ext in [".7z", ".fz", ".fzip"] and HAS_PY7ZR:
                    with py7zr.SevenZipFile(self.current_folder_view, 'r', password=pwd) as szf:
                        for fname in szf.getnames():
                            self._render_generic_member_row(fname)

                elif ext == ".rar" and HAS_RARFILE:
                    rf = rarfile.RarFile(self.current_folder_view, 'r')
                    if pwd: rf.setpassword(pwd)
                    for info in rf.infolist():
                        self._render_generic_member_row(info.filename, info.file_size)
                    rf.close()

                elif ext == ".zip" or os.path.isfile(self.current_folder_view):
                    pwd_b = pwd.encode('utf-8') if pwd else None
                    zf = pyzipper.AESZipFile(self.current_folder_view, 'r') if HAS_PYZIPPER else zipfile.ZipFile(self.current_folder_view, 'r')
                    if pwd_b: zf.setpassword(pwd_b)
                    for info in zf.infolist():
                        self._render_generic_member_row(info.filename, info.file_size)
                    zf.close()

                else:
                    for entry in os.listdir(self.current_folder_view):
                        full_p = os.path.join(self.current_folder_view, entry)
                        self._render_grid_row(full_p, is_inside=True)

            except Exception as e:
                messagebox.showerror("Error", f"Could not inspect archive: {e}")
            return

        self.lbl_location.configure(text="")
        count = len(self.queue_items)

        if count == 0:
            empty_lbl = ctk.CTkLabel(
                self.scroll_frame, text="📥 Drag & Drop Files or Folders Here\nor click '+ ADD ITEMS' above to start",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=COLOR_TEXT_MUTED
            )
            empty_lbl.pack(expand=True, pady=70)

            self.btn_compress.configure(state="disabled", fg_color=COLOR_FIELD_BG, text_color=COLOR_TEXT_DISABLED)
            self.btn_extract.configure(state="disabled", fg_color=COLOR_FIELD_BG, text_color=COLOR_TEXT_DISABLED)
            self.lbl_status.configure(text="Ready | 0 items queued")
            self.btn_open_folder.pack_forget()
            return

        for item in self.queue_items:
            self._render_grid_row(item["path"], is_inside=False)

        if count > 0:
            first_base = os.path.basename(os.path.abspath(self.queue_items[0]["path"]))
            suggested = f"{os.path.splitext(first_base)[0]}.zip"
            if not self.archive_name_entry.get().strip():
                self.archive_name_entry.delete(0, tk.END)
                self.archive_name_entry.insert(0, suggested)

        self.btn_compress.configure(state="normal", fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER, text_color=COLOR_TEXT_PRIMARY)
        self.btn_extract.configure(state="normal", fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER, text_color=COLOR_TEXT_PRIMARY)
        self.lbl_status.configure(text=f"Ready | {count} items queued")

    def _render_grid_row(self, path, is_inside=False):
        row = ctk.CTkFrame(self.scroll_frame, fg_color=COLOR_FIELD_BG, corner_radius=6, border_width=0)
        row.pack(fill="x", pady=2)

        is_dir = os.path.isdir(path)
        ext = os.path.splitext(path)[1].lower()
        is_arch = ext in [".zip", ".7z", ".fz", ".fzip", ".rar", ".tar", ".gz", ".bz2", ".xz"]

        icon = "📁" if is_dir else ("📦" if is_arch else "📄")
        name = os.path.basename(path) or path

        if is_dir:
            size_str = f"{len(os.listdir(path))} items" if os.path.exists(path) else "-"
            ftype = "Folder"
        elif is_arch:
            size_str = f"{round(os.path.getsize(path)/(1024*1024), 2)} MB" if os.path.exists(path) else "-"
            ftype = "Archive"
        else:
            size_str = f"{round(os.path.getsize(path)/1024, 1)} KB" if os.path.exists(path) else "-"
            ftype = Path(path).suffix[1:].upper() or "File"

        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%d/%m/%Y") if os.path.exists(path) else "-"

        name_lbl = ctk.CTkLabel(row, text=f"{icon}  {name}", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=COLOR_TEXT_PRIMARY, anchor="w")
        name_lbl.pack(side="left", padx=12, pady=6, expand=True, fill="x")

        size_lbl = ctk.CTkLabel(row, text=size_str, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_MUTED, width=100, anchor="e")
        size_lbl.pack(side="left", padx=10)

        type_lbl = ctk.CTkLabel(row, text=ftype, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_MUTED, width=90, anchor="center")
        type_lbl.pack(side="left", padx=10)

        date_lbl = ctk.CTkLabel(row, text=mtime, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_MUTED, width=120, anchor="center")
        date_lbl.pack(side="left", padx=10)

        del_btn = ctk.CTkButton(
            row, text="✖", fg_color="transparent", hover_color=COLOR_CARD_BG,
            text_color=COLOR_TEXT_ALERT, width=28, height=26, font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda p=path: self.remove_item(p)
        )
        del_btn.pack(side="left", padx=(10, 15))
        FloatingTooltip(del_btn, "Remove/exclude this item.")

        if is_dir:
            row.bind("<Double-1>", lambda e, p=path: self.inspect_folder(p))
            name_lbl.bind("<Double-1>", lambda e, p=path: self.inspect_folder(p))
        elif is_arch:
            row.bind("<Double-1>", lambda e, p=path: self.inspect_archive(p))
            name_lbl.bind("<Double-1>", lambda e, p=path: self.inspect_archive(p))

    def _render_generic_member_row(self, filename, size_b=0):
        row = ctk.CTkFrame(self.scroll_frame, fg_color=COLOR_FIELD_BG, corner_radius=6, border_width=0)
        row.pack(fill="x", pady=2)

        size_str = f"{round(size_b/1024, 1)} KB" if size_b else "-"
        name_lbl = ctk.CTkLabel(row, text=f"📄  {filename}", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=COLOR_TEXT_PRIMARY, anchor="w")
        name_lbl.pack(side="left", padx=12, pady=6, expand=True, fill="x")

        size_lbl = ctk.CTkLabel(row, text=size_str, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_MUTED, width=100, anchor="e")
        size_lbl.pack(side="left", padx=10)

        type_lbl = ctk.CTkLabel(row, text="Compressed", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_MUTED, width=90, anchor="center")
        type_lbl.pack(side="left", padx=10)

    # -------------------------------------------------------------------------
    # DUAL-MODE COMPRESSION WORKER
    # -------------------------------------------------------------------------
    def start_compression_thread(self):
        if self.is_processing or len(self.queue_items) == 0:
            return

        password = self.pwd_entry.get().strip()
        custom_name = self.archive_name_entry.get().strip()
        first_item = self.queue_items[0]["path"]

        ext = ".fzip" if password else ".zip"

        if password and custom_name.lower().endswith(".zip"):
            custom_name = custom_name[:-4] + ".fzip"
        elif not password and custom_name.lower().endswith(".fzip"):
            custom_name = custom_name[:-5] + ".zip"

        if not custom_name:
            custom_name = f"{os.path.splitext(os.path.basename(first_item))[0]}{ext}"
        elif not custom_name.lower().endswith((".zip", ".fzip")):
            custom_name += ext

        out_archive = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[("Fusion Vault Archive", "*.fzip"), ("ZIP Archive", "*.zip")],
            title="Save Archive As", initialfile=custom_name
        )
        if not out_archive:
            return

        self.last_output_dir = os.path.dirname(os.path.abspath(out_archive))
        self.is_processing = True
        self.btn_open_folder.pack_forget()
        self.progress_bar.set(0)
        self.progress_bar.pack(side="right")

        threading.Thread(target=self._run_compression, args=(out_archive, password), daemon=True).start()

    def _run_compression(self, out_archive_path, password):
        valid_files = [x["path"] for x in self.queue_items if os.path.exists(x["path"])]
        out_abs = os.path.abspath(out_archive_path)

        if os.path.exists(out_abs):
            try:
                os.remove(out_abs)
            except Exception:
                pass

        total_bytes = 0
        for target in valid_files:
            if os.path.isfile(target):
                total_bytes += os.path.getsize(target)
            elif os.path.isdir(target):
                for root, dirs, files in os.walk(target):
                    for f in files:
                        total_bytes += os.path.getsize(os.path.join(root, f))

        try:
            processed_bytes = 0
            start_time = time.time()

            if password and HAS_PY7ZR:
                filters = [
                    {'id': py7zr.FILTER_LZMA2},
                    {'id': py7zr.FILTER_CRYPTO_AES256_SHA256}
                ]
                with py7zr.SevenZipFile(out_abs, 'w', password=password, header_encryption=True, filters=filters) as szf:
                    for target in valid_files:
                        target_abs = os.path.abspath(target)
                        if target_abs == out_abs: continue

                        if os.path.isfile(target_abs):
                            file_size = os.path.getsize(target_abs)
                            processed_bytes += file_size
                            self._update_byte_progress(processed_bytes, total_bytes, start_time, os.path.basename(target_abs))
                            szf.write(target_abs, os.path.basename(target_abs))

                        elif os.path.isdir(target_abs):
                            for root, dirs, files in os.walk(target_abs):
                                for file in files:
                                    full_p = os.path.abspath(os.path.join(root, file))
                                    if full_p == out_abs: continue
                                    processed_bytes += os.path.getsize(full_p)
                                    rel_p = os.path.relpath(full_p, os.path.dirname(target_abs))
                                    self._update_byte_progress(processed_bytes, total_bytes, start_time, file)
                                    szf.write(full_p, rel_p)

            else:
                zf = zipfile.ZipFile(out_abs, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1)
                for target in valid_files:
                    target_abs = os.path.abspath(target)
                    if target_abs == out_abs: continue

                    if os.path.isfile(target_abs):
                        file_size = os.path.getsize(target_abs)
                        processed_bytes += file_size
                        self._update_byte_progress(processed_bytes, total_bytes, start_time, os.path.basename(target_abs))
                        zf.write(target_abs, os.path.basename(target_abs))

                    elif os.path.isdir(target_abs):
                        for root, dirs, files in os.walk(target_abs):
                            for file in files:
                                full_p = os.path.abspath(os.path.join(root, file))
                                if full_p == out_abs: continue
                                processed_bytes += os.path.getsize(full_p)
                                rel_p = os.path.relpath(full_p, os.path.dirname(target_abs))
                                self._update_byte_progress(processed_bytes, total_bytes, start_time, file)
                                zf.write(full_p, rel_p)
                zf.close()

            self.after(0, lambda: self.pwd_entry.delete(0, tk.END))
            self._finish_processing(f"Successfully packaged into {os.path.basename(out_archive_path)}!")

        except Exception as e:
            self._finish_processing(f"Compression failed: {e}")

    # -------------------------------------------------------------------------
    # UNIVERSAL EXTRACTION WORKER
    # -------------------------------------------------------------------------
    def start_extraction_thread(self):
        if self.is_processing:
            return

        archives = [x["path"] for x in self.queue_items if x.get("path", "").lower().endswith(
            (".zip", ".7z", ".fz", ".fzip", ".rar", ".tar", ".gz", ".bz2", ".xz")
        )]

        if not archives:
            messagebox.showinfo("Extraction", "No archive files queued for extraction.")
            return

        target_archive = archives[0]

        if check_archive_encrypted(target_archive):
            EncryptedArchiveDialog(self, target_archive, self._start_extraction_with_password)
        else:
            self._start_extraction_with_password(target_archive, None)

    def _start_extraction_with_password(self, target_archive, password):
        target_dir = filedialog.askdirectory(title="Select Extraction Directory")
        if not target_dir:
            return

        self.last_output_dir = target_dir
        self.is_processing = True
        self.btn_open_folder.pack_forget()
        self.progress_bar.set(0)
        self.progress_bar.pack(side="right")

        threading.Thread(target=self._run_extraction, args=(target_archive, target_dir, password), daemon=True).start()

    def _run_extraction(self, archive_path, extract_dir, password):
        try:
            ext = os.path.splitext(archive_path)[1].lower()

            if ext in [".7z", ".fz", ".fzip"] and HAS_PY7ZR:
                with py7zr.SevenZipFile(archive_path, 'r', password=password or None) as szf:
                    szf.extractall(path=extract_dir)

            elif ext == ".rar" and HAS_RARFILE:
                rf = rarfile.RarFile(archive_path, 'r')
                if password: rf.setpassword(password)
                rf.extractall(path=extract_dir)
                rf.close()

            elif ext in [".tar", ".gz", ".bz2", ".xz"]:
                with tarfile.open(archive_path, 'r:*') as tf:
                    tf.extractall(path=extract_dir)

            else:
                zf = pyzipper.AESZipFile(archive_path, 'r') if HAS_PYZIPPER else zipfile.ZipFile(archive_path, 'r')
                if password:
                    zf.setpassword(password.encode('utf-8'))
                zf.extractall(path=extract_dir)
                zf.close()

            try:
                base_name = os.path.basename(os.path.abspath(extract_dir))
                items = os.listdir(extract_dir)
                if len(items) == 1:
                    single_item = os.path.join(extract_dir, items[0])
                    if os.path.isdir(single_item) and items[0].lower() == base_name.lower():
                        for sub in os.listdir(single_item):
                            src_p = os.path.join(single_item, sub)
                            dst_p = os.path.join(extract_dir, sub)
                            if not os.path.exists(dst_p):
                                shutil.move(src_p, dst_p)
                        try:
                            if not os.listdir(single_item):
                                os.rmdir(single_item)
                        except Exception:
                            pass
            except Exception:
                pass

            self._finish_processing("Extraction finished successfully!")
        except Exception as e:
            self._finish_processing(f"Extraction failed: {e}")
            self.after(0, lambda: messagebox.showerror("Error", "Incorrect Password or Corrupted Archive."))

    def _update_byte_progress(self, current_b, total_b, start_t, name):
        pct = (current_b / total_b) if total_b > 0 else 0.99
        if pct >= 1.0: pct = 0.99

        elapsed = max(0.001, time.time() - start_t)
        speed = current_b / elapsed
        rem_bytes = max(0, total_b - current_b)
        rem_seconds = int(rem_bytes / speed) if speed > 0 else 0
        mins, secs = divmod(rem_seconds, 60)

        cur_mb = round(current_b / (1024 * 1024), 1)
        tot_mb = round(total_b / (1024 * 1024), 1)

        self.after(0, lambda: self.progress_bar.set(pct))
        self.after(0, lambda: self.lbl_status.configure(
            text=f"Processing: {name[:16]} | {cur_mb} MB / {tot_mb} MB ({int(pct*100)}%) | Est. Time: {mins:02d}:{secs:02d} Left"
        ))

    def _finish_processing(self, status_msg):
        self.is_processing = False
        self.after(0, lambda: self.progress_bar.set(1.0))
        self.after(0, lambda: self.progress_bar.pack_forget())
        self.after(0, lambda: self.lbl_status.configure(text=status_msg, text_color=COLOR_TEXT_PRIMARY))
        if self.last_output_dir:
            self.after(0, lambda: self.btn_open_folder.pack(side="right", padx=10))


# =============================================================================
# CLI INTERACTIVE COMPRESSION WITH CONFIG DIALOG & PROGRESS WINDOW
# =============================================================================
def run_cli_compress_interactive(targets, default_target_dir=None):
    """Pops up AddToArchiveDialog and then streams live compression in CLICompressionProgressDialog."""
    if not targets: return

    app = ctk.CTk()
    app.withdraw()

    def on_confirm(archive_name, save_dir, password):
        app.destroy()
        progress_app = ctk.CTk()
        progress_app.withdraw()
        dlg = CLICompressionProgressDialog(progress_app, targets, archive_name, save_dir, password)
        dlg.protocol("WM_DELETE_WINDOW", lambda: progress_app.destroy())
        progress_app.mainloop()

    dialog = AddToArchiveDialog(app, targets, default_target_dir, on_confirm)
    dialog.protocol("WM_DELETE_WINDOW", lambda: app.destroy())
    app.mainloop()


# =============================================================================
# CLI HANDLERS & INTERACTIVE RIGHT-CLICK CONTEXT MENU ACTIONS (BATCH SUPPORT)
# =============================================================================
def run_cli_extract_interactive(archive_path, target_dir):
    """Handles right-click extraction for both archives and regular uncompressed folders."""
    if not os.path.exists(archive_path): return

    if os.path.isdir(archive_path):
        folder_name = os.path.basename(os.path.abspath(archive_path))
        dest_folder = os.path.join(target_dir, folder_name)
        conflict_state = ConflictState()

        if os.path.abspath(archive_path) == os.path.abspath(dest_folder):
            dest_folder = os.path.join(target_dir, f"{folder_name}_Extracted")

        if os.path.exists(dest_folder):
            choice = prompt_file_conflict(dest_folder, conflict_state)
            if choice == "replace":
                try:
                    shutil.rmtree(dest_folder)
                except Exception:
                    pass
            elif choice == "keep_both":
                counter = 1
                new_dest = os.path.join(target_dir, f"{folder_name}_{counter}")
                while os.path.exists(new_dest):
                    counter += 1
                    new_dest = os.path.join(target_dir, f"{folder_name}_{counter}")
                dest_folder = new_dest
            elif choice == "skip":
                return

        try:
            shutil.copytree(archive_path, dest_folder, dirs_exist_ok=True)
            show_toast("Extraction Complete!", f"Extracted folder '{folder_name}' to '{os.path.basename(target_dir)}'.")
        except Exception as e:
            print(f"Error copying folder: {e}")
        return

    password = None
    if check_archive_encrypted(archive_path):
        app = ctk.CTk()
        app.withdraw()

        unlocked_pwd = [None]

        def on_unlocked(path, pwd):
            unlocked_pwd[0] = pwd
            app.destroy()

        dialog = EncryptedArchiveDialog(app, archive_path, on_unlocked)
        dialog.protocol("WM_DELETE_WINDOW", lambda: app.destroy())
        app.mainloop()

        if unlocked_pwd[0] is None:
            return
        password = unlocked_pwd[0]

    _extract_contents_cli(archive_path, target_dir, password)


def _extract_contents_cli(archive_path, extract_dir, password=None):
    try:
        ext = os.path.splitext(archive_path)[1].lower()

        if ext in [".7z", ".fz", ".fzip"] and HAS_PY7ZR:
            with py7zr.SevenZipFile(archive_path, 'r', password=password or None) as szf:
                szf.extractall(path=extract_dir)

        elif ext == ".rar" and HAS_RARFILE:
            with rarfile.RarFile(archive_path, 'r') as rf:
                if password: rf.setpassword(password)
                rf.extractall(path=extract_dir)

        elif ext in [".tar", ".gz", ".bz2", ".xz"]:
            with tarfile.open(archive_path, 'r:*') as tf:
                tf.extractall(path=extract_dir)

        elif ext in [".zip", ".fz", ".fzip"] or os.path.isfile(archive_path):
            zf = pyzipper.AESZipFile(archive_path, 'r') if HAS_PYZIPPER else zipfile.ZipFile(archive_path, 'r')
            if password:
                zf.setpassword(password.encode('utf-8'))
            zf.extractall(path=extract_dir)
            zf.close()

        # Prevent duplicate top-level Folder/Folder/files
        try:
            base_name = os.path.basename(os.path.abspath(extract_dir))
            items = os.listdir(extract_dir)
            if len(items) == 1:
                single_item = os.path.join(extract_dir, items[0])
                if os.path.isdir(single_item) and items[0].lower() == base_name.lower():
                    for sub in os.listdir(single_item):
                        src_p = os.path.join(single_item, sub)
                        dst_p = os.path.join(extract_dir, sub)
                        if not os.path.exists(dst_p):
                            shutil.move(src_p, dst_p)
                    try:
                        if not os.listdir(single_item):
                            os.rmdir(single_item)
                    except Exception:
                        pass
        except Exception:
            pass

    except Exception as e:
        print(f"Error extracting: {e}")


def run_cli_unpack_batch(targets):
    """Fusion Unpack (1-Level Move) Batch Processing into original parent folders."""
    if not targets: return

    files_moved_total = 0
    processed_count = 0
    conflict_state = ConflictState()

    for target in targets:
        if not os.path.exists(target): continue
        target_abs = os.path.abspath(target)
        parent_dir = os.path.dirname(target_abs)

        if os.path.isfile(target_abs):
            ext = os.path.splitext(target_abs)[1].lower()
            if ext in [".zip", ".7z", ".fz", ".fzip", ".rar", ".tar", ".gz", ".bz2", ".xz"]:
                run_cli_extract_interactive(target_abs, parent_dir)
                try:
                    os.remove(target_abs)
                    processed_count += 1
                except Exception:
                    pass

        elif os.path.isdir(target_abs):
            try:
                items = os.listdir(target_abs)
                for item in items:
                    src = os.path.join(target_abs, item)
                    dst = os.path.join(parent_dir, item)

                    if os.path.exists(dst):
                        choice = prompt_file_conflict(dst, conflict_state)
                        if choice == "replace":
                            try:
                                if os.path.isdir(dst):
                                    shutil.rmtree(dst)
                                else:
                                    os.remove(dst)
                            except Exception:
                                pass
                        elif choice == "keep_both":
                            base, ext_n = os.path.splitext(item)
                            counter = 1
                            new_dst = os.path.join(parent_dir, f"{base}_{counter}{ext_n}")
                            while os.path.exists(new_dst):
                                counter += 1
                                new_dst = os.path.join(parent_dir, f"{base}_{counter}{ext_n}")
                            dst = new_dst
                        elif choice == "skip":
                            continue

                    try:
                        shutil.move(src, dst)
                        files_moved_total += 1
                    except Exception:
                        pass

                try:
                    if not os.listdir(target_abs):
                        os.rmdir(target_abs)
                        processed_count += 1
                except Exception:
                    pass
            except Exception as e:
                print(f"Error unpacking {target_abs}: {e}")

    if len(targets) == 1:
        show_toast("Fusion Unpack Complete!", f"Unpacked '{os.path.basename(targets[0])}' ({files_moved_total} items moved).")
    else:
        show_toast("Batch Unpack Complete!", f"Successfully processed {len(targets)} selected items ({files_moved_total} total files moved).")


def run_cli_unpack_to_batch(targets, destination_dir):
    """Unpacks targets directly into destination_dir across open Explorer windows or drop targets."""
    if not targets or not destination_dir: return

    os.makedirs(destination_dir, exist_ok=True)
    files_moved_total = 0
    conflict_state = ConflictState()

    for target in targets:
        if not os.path.exists(target): continue
        target_abs = os.path.abspath(target)

        if os.path.isfile(target_abs):
            ext = os.path.splitext(target_abs)[1].lower()
            if ext in [".zip", ".7z", ".fz", ".fzip", ".rar", ".tar", ".gz", ".bz2", ".xz"]:
                run_cli_extract_interactive(target_abs, destination_dir)
                try:
                    os.remove(target_abs)
                    files_moved_total += 1
                except Exception:
                    pass

        elif os.path.isdir(target_abs):
            try:
                items = os.listdir(target_abs)
                for item in items:
                    src = os.path.join(target_abs, item)
                    dst = os.path.join(destination_dir, item)

                    if os.path.exists(dst):
                        choice = prompt_file_conflict(dst, conflict_state)
                        if choice == "replace":
                            try:
                                if os.path.isdir(dst):
                                    shutil.rmtree(dst)
                                else:
                                    os.remove(dst)
                            except Exception:
                                pass
                        elif choice == "keep_both":
                            base, ext_n = os.path.splitext(item)
                            counter = 1
                            new_dst = os.path.join(destination_dir, f"{base}_{counter}{ext_n}")
                            while os.path.exists(new_dst):
                                counter += 1
                                new_dst = os.path.join(destination_dir, f"{base}_{counter}{ext_n}")
                            dst = new_dst
                        elif choice == "skip":
                            continue

                    try:
                        shutil.move(src, dst)
                        files_moved_total += 1
                    except Exception:
                        pass

                try:
                    if not os.listdir(target_abs):
                        os.rmdir(target_abs)
                except Exception:
                    pass
            except Exception as e:
                print(f"Error unpacking to destination: {e}")

    if len(targets) == 1:
        show_toast("Fusion Unpack Complete!", f"Unpacked '{os.path.basename(targets[0])}' into '{os.path.basename(destination_dir)}' ({files_moved_total} items moved).")
    else:
        show_toast("Batch Unpack Complete!", f"Unpacked {len(targets)} selected items into '{os.path.basename(destination_dir)}' ({files_moved_total} total files moved).")


def run_cli_unpack_all_to_batch(targets, destination_dir=None):
    """Fusion Unpack All (Deep Cleanup) Batch Processing directly into destination_dir."""
    if not targets: return

    files_moved_total = 0
    dirs_removed_total = 0
    archives_unpacked_total = 0
    conflict_state = ConflictState()

    for target in targets:
        if not os.path.exists(target): continue
        target_abs = os.path.abspath(target)
        dest_dir = os.path.abspath(destination_dir) if destination_dir else (target_abs if os.path.isdir(target_abs) else os.path.dirname(target_abs))

        os.makedirs(dest_dir, exist_ok=True)

        try:
            if os.path.isdir(target_abs):
                for root, dirs, files in os.walk(target_abs):
                    for f in files:
                        f_path = os.path.join(root, f)
                        ext = os.path.splitext(f)[1].lower()
                        if ext in [".zip", ".7z", ".fz", ".fzip", ".rar", ".tar", ".gz", ".bz2", ".xz"]:
                            try:
                                run_cli_extract_interactive(f_path, root)
                                os.remove(f_path)
                                archives_unpacked_total += 1
                            except Exception:
                                pass

                for root, dirs, files in os.walk(target_abs, topdown=False):
                    for file in files:
                        src = os.path.join(root, file)
                        dst = os.path.join(dest_dir, file)
                        if src != dst:
                            if os.path.exists(dst):
                                choice = prompt_file_conflict(dst, conflict_state)
                                if choice == "replace":
                                    try:
                                        os.remove(dst)
                                    except Exception:
                                        pass
                                elif choice == "keep_both":
                                    base, ext_n = os.path.splitext(file)
                                    counter = 1
                                    new_dst = os.path.join(dest_dir, f"{base}_{counter}{ext_n}")
                                    while os.path.exists(new_dst):
                                        counter += 1
                                        new_dst = os.path.join(dest_dir, f"{base}_{counter}{ext_n}")
                                    dst = new_dst
                                elif choice == "skip":
                                    continue

                            try:
                                shutil.move(src, dst)
                                files_moved_total += 1
                            except Exception:
                                pass
                    for d in dirs:
                        dir_p = os.path.join(root, d)
                        try:
                            if not os.listdir(dir_p):
                                os.rmdir(dir_p)
                                dirs_removed_total += 1
                        except Exception:
                            pass

                try:
                    if not os.listdir(target_abs):
                        os.rmdir(target_abs)
                        dirs_removed_total += 1
                except Exception:
                    pass

            elif os.path.isfile(target_abs):
                ext = os.path.splitext(target_abs)[1].lower()
                if ext in [".zip", ".7z", ".fz", ".fzip", ".rar", ".tar", ".gz", ".bz2", ".xz"]:
                    run_cli_extract_interactive(target_abs, dest_dir)
                    try:
                        os.remove(target_abs)
                        archives_unpacked_total += 1
                    except Exception:
                        pass

        except Exception as e:
            print(f"Error during unpack all: {e}")

    out_folder_str = f" to '{os.path.basename(dest_dir)}'" if dest_dir else ""
    show_toast(
        "Batch Unpack All Complete!",
        f"{files_moved_total} files moved{out_folder_str}.\n{archives_unpacked_total} archives unpacked.\n{dirs_removed_total} empty folders removed."
    )


def install_windows_shell_context_menu():
    """Registers right-click context menu under 'Fusion Zip >' in Windows Explorer."""
    if not HAS_WINREG:
        print("[!] Windows Registry module unavailable.")
        return

    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
        cmd_prefix = f'"{exe_path}"'
    else:
        python_exe = sys.executable
        if python_exe.endswith("python.exe"):
            pythonw_exe = python_exe[:-10] + "pythonw.exe"
            if os.path.exists(pythonw_exe):
                python_exe = pythonw_exe
        script_path = os.path.abspath(__file__)
        cmd_prefix = f'"{python_exe}" "{script_path}"'

    registry_targets = [
        r"Software\Classes\Directory\shell\FusionZip",
        r"Software\Classes\Directory\Background\shell\FusionZip",
        r"Software\Classes\*\shell\FusionZip"
    ]

    for target_key_path in registry_targets:
        for old_cmd in ["01_Compress", "02_Extract", "02_ExtractFolder", "03_ExtractHere", "04_Unpack", "04_UnpackAll", "05_Open"]:
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{target_key_path}\\shell\\{old_cmd}\\command")
            except Exception:
                pass
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{target_key_path}\\shell\\{old_cmd}")
            except Exception:
                pass

    icon_lightning = r"%SystemRoot%\System32\shell32.dll,238"
    icon_zip       = r"%SystemRoot%\System32\zipfldr.dll,0"
    icon_folder_new= r"%SystemRoot%\System32\shell32.dll,4"
    icon_extract   = r"%SystemRoot%\System32\shell32.dll,3"
    icon_vacuum    = r"%SystemRoot%\System32\shell32.dll,238"
    icon_pc        = r"%SystemRoot%\System32\imageres.dll,109"

    for target_key_path in registry_targets:
        try:
            parent_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, target_key_path)
            winreg.SetValueEx(parent_key, "MUIVerb", 0, winreg.REG_SZ, "Fusion Zip")
            winreg.SetValueEx(parent_key, "SubCommands", 0, winreg.REG_SZ, "")
            winreg.SetValueEx(parent_key, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
            winreg.SetValueEx(parent_key, "Icon", 0, winreg.REG_SZ, icon_lightning)

            sub_shell = winreg.CreateKey(parent_key, "shell")

            k1 = winreg.CreateKey(sub_shell, "01_Compress")
            winreg.SetValueEx(k1, "MUIVerb", 0, winreg.REG_SZ, "Compress with Fusion Zip")
            winreg.SetValueEx(k1, "Icon", 0, winreg.REG_SZ, icon_zip)
            c1 = winreg.CreateKey(k1, "command")
            winreg.SetValue(c1, "", winreg.REG_SZ, f'{cmd_prefix} --compress "%1"')

            k2 = winreg.CreateKey(sub_shell, "02_ExtractFolder")
            winreg.SetValueEx(k2, "MUIVerb", 0, winreg.REG_SZ, "Extract to Folder")
            winreg.SetValueEx(k2, "Icon", 0, winreg.REG_SZ, icon_folder_new)
            c2 = winreg.CreateKey(k2, "command")
            winreg.SetValue(c2, "", winreg.REG_SZ, f'{cmd_prefix} --extract-folder "%1"')

            k3 = winreg.CreateKey(sub_shell, "03_ExtractHere")
            winreg.SetValueEx(k3, "MUIVerb", 0, winreg.REG_SZ, "Extract Here")
            winreg.SetValueEx(k3, "Icon", 0, winreg.REG_SZ, icon_extract)
            c3 = winreg.CreateKey(k3, "command")
            winreg.SetValue(c3, "", winreg.REG_SZ, f'{cmd_prefix} --extract-here "%1"')

            k4 = winreg.CreateKey(sub_shell, "04_Unpack")
            winreg.SetValueEx(k4, "MUIVerb", 0, winreg.REG_SZ, "Fusion Unpack")
            winreg.SetValueEx(k4, "Icon", 0, winreg.REG_SZ, icon_vacuum)
            c4 = winreg.CreateKey(k4, "command")
            winreg.SetValue(c4, "", winreg.REG_SZ, f'{cmd_prefix} --unpack "%1"')

            k4b = winreg.CreateKey(sub_shell, "04_UnpackAll")
            winreg.SetValueEx(k4b, "MUIVerb", 0, winreg.REG_SZ, "Fusion Unpack All")
            winreg.SetValueEx(k4b, "Icon", 0, winreg.REG_SZ, icon_vacuum)
            c4b = winreg.CreateKey(k4b, "command")
            winreg.SetValue(c4b, "", winreg.REG_SZ, f'{cmd_prefix} --unpack-all "%1"')

            k5 = winreg.CreateKey(sub_shell, "05_Open")
            winreg.SetValueEx(k5, "MUIVerb", 0, winreg.REG_SZ, "Open in Fusion Zip")
            winreg.SetValueEx(k5, "Icon", 0, winreg.REG_SZ, icon_pc)
            c5 = winreg.CreateKey(k5, "command")
            winreg.SetValue(c5, "", winreg.REG_SZ, f'{cmd_prefix} --gui "%1"')

        except Exception as e:
            print(f"[!] Registry setup warning ({target_key_path}): {e}")

    drag_drop_targets = [
        r"Software\Classes\Directory\shellex\DragDropHandlers\FusionZip",
        r"Software\Classes\*\shellex\DragDropHandlers\FusionZip"
    ]
    for dd_path in drag_drop_targets:
        try:
            dd_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, dd_path)
            winreg.SetValue(dd_key, "", winreg.REG_SZ, f'{cmd_prefix} --extract-here "%1"')
        except Exception:
            pass

    print("[✓] Right-click context menu 'Fusion Zip >' updated successfully!")


def uninstall_windows_shell_context_menu():
    """Wipes Fusion Zip keys from the Windows Registry."""
    if not HAS_WINREG:
        print("[!] Windows Registry module unavailable.")
        return

    registry_targets = [
        r"Software\Classes\Directory\shell\FusionZip",
        r"Software\Classes\Directory\Background\shell\FusionZip",
        r"Software\Classes\*\shell\FusionZip",
        r"Software\Classes\Directory\shellex\DragDropHandlers\FusionZip",
        r"Software\Classes\*\shellex\DragDropHandlers\FusionZip"
    ]

    for target_key_path in registry_targets:
        for old_cmd in ["01_Compress", "02_Extract", "02_ExtractFolder", "03_ExtractHere", "04_Unpack", "04_UnpackAll", "05_Open"]:
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{target_key_path}\\shell\\{old_cmd}\\command")
            except Exception:
                pass
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{target_key_path}\\shell\\{old_cmd}")
            except Exception:
                pass
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{target_key_path}\\shell")
        except Exception:
            pass
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, target_key_path)
        except Exception:
            pass

    print("[✓] Fusion Zip right-click context menu successfully removed from Windows Registry!")


def try_send_ipc_gui(args):
    """Sends command line arguments to an already-running Fusion Zip window via local socket."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        s.connect(('127.0.0.1', IPC_PORT))
        s.sendall(json.dumps(args).encode('utf-8'))
        s.close()
        return True
    except Exception:
        return False


def start_ipc_server_thread(app):
    """Listens for new multi-select files opened while Fusion Zip is running and appends them to the queue."""
    def server_loop():
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('127.0.0.1', IPC_PORT))
            server.listen(5)
            while True:
                conn, addr = server.accept()
                data = conn.recv(4096)
                if data:
                    paths = json.loads(data.decode('utf-8'))
                    for p in paths:
                        clean_p = p.strip("{}")
                        if os.path.exists(clean_p) and not any(x["path"] == clean_p for x in app.queue_items):
                            app.queue_items.append({"path": clean_p})
                    app.after(0, app._refresh_grid)
                conn.close()
        except Exception:
            pass

    threading.Thread(target=server_loop, daemon=True).start()


# =============================================================================
# MAIN ENTRY POINT (SINGLE-INSTANCE MUTEX LOCK FOR MULTI-SELECT)
# =============================================================================
if __name__ == "__main__":
    if len(sys.argv) > 1:
        flag = sys.argv[1]
        args = sys.argv[2:]

        if sys.platform == "win32" and flag == "--gui" and args:
            MUTEX_NAME = "Global\\FusionZip_SingleInstance_Mutex_1.0"
            kernel32 = ctypes.windll.kernel32
            mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
            last_error = kernel32.GetLastError()
            ERROR_ALREADY_EXISTS = 183

            if last_error == ERROR_ALREADY_EXISTS or try_send_ipc_gui(args):
                try_send_ipc_gui(args)
                sys.exit(0)

        if flag == "--install-shell":
            install_windows_shell_context_menu()
            sys.exit(0)
        elif flag in ["--uninstall-shell", "--remove-shell"]:
            uninstall_windows_shell_context_menu()
            sys.exit(0)
        elif flag == "--compress" and args:
            run_cli_compress_interactive(args, default_target_dir=os.path.dirname(os.path.abspath(args[0])))
            sys.exit(0)
        elif flag == "--compress-to" and len(args) >= 2:
            target_dir = args[0]
            targets = args[1:]
            run_cli_compress_interactive(targets, default_target_dir=target_dir)
            sys.exit(0)
        elif flag == "--extract-folder" and args:
            for target in args:
                extract_dir = os.path.splitext(target)[0]
                run_cli_extract_interactive(target, extract_dir)
            sys.exit(0)
        elif flag == "--extract-folder-to" and len(args) >= 2:
            target_dir = args[0]
            targets = args[1:]
            for target in targets:
                base = os.path.splitext(os.path.basename(target))[0]
                extract_dir = os.path.join(target_dir, base)
                run_cli_extract_interactive(target, extract_dir)
            sys.exit(0)
        elif flag == "--extract-here" and args:
            for target in args:
                extract_dir = os.path.dirname(os.path.abspath(target))
                run_cli_extract_interactive(target, extract_dir)
            sys.exit(0)
        elif flag == "--extract-to" and len(args) >= 2:
            target_dir = args[0]
            archive_paths = args[1:]
            for archive_path in archive_paths:
                run_cli_extract_interactive(archive_path, target_dir)
            sys.exit(0)
        elif flag == "--unpack" and args:
            run_cli_unpack_batch(args)
            sys.exit(0)
        elif flag == "--unpack-to" and len(args) >= 2:
            target_dir = args[0]
            archive_paths = args[1:]
            run_cli_unpack_to_batch(archive_paths, target_dir)
            sys.exit(0)
        elif flag == "--unpack-all" and args:
            run_cli_unpack_all_to_batch(args)
            sys.exit(0)
        elif flag == "--unpack-all-to" and len(args) >= 2:
            target_dir = args[0]
            archive_paths = args[1:]
            run_cli_unpack_all_to_batch(archive_paths, target_dir)
            sys.exit(0)
        elif flag == "--gui" and args:
            app = FusionZipApp()
            start_ipc_server_thread(app)
            for arg in args:
                if os.path.exists(arg):
                    app.queue_items.append({"path": arg})
            app._refresh_grid()
            app.mainloop()
            sys.exit(0)

    app = FusionZipApp()
    start_ipc_server_thread(app)
    app.mainloop()