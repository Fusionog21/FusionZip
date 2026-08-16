"""
===============================================================================
FUSION ZIP — Windows 11 Fluent Dark Edition (Master Engine)
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

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

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
        "CustomTkinter and Pillow are required.\nPlease run: pip install customtkinter pyzipper py7zr rarfile pillow"
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
# WINDOWS 11 FLUENT DARK COLOR PALETTE & DESIGN CONSTANTS
# =============================================================================
COLOR_BG_DARK       = "#12141d"  # Deep slate/mica canvas background
COLOR_TOP_CHROME    = "#181b27"  # Top command bar / Title chrome
COLOR_CARD_BG       = "#181b27"  # Elevated container cards
COLOR_FIELD_BG      = "#202434"  # Input fields, table header, and row background
COLOR_ROW_HOVER     = "#282e42"  # Smooth ambient glow on hover
COLOR_BORDER        = "#2b3147"  # Fluent subtle 1px border stroke
COLOR_BLUE_ACCENT   = "#0078d4"  # Windows 11 primary accent blue
COLOR_BLUE_HOVER    = "#1084d8"  # Windows 11 accent hover
COLOR_ACCENT_TEXT   = "#60cdff"  # Windows 11 fluent cyan text
COLOR_TEXT_PRIMARY  = "#ffffff"  # Pure crisp white text
COLOR_TEXT_MUTED    = "#9ea7c2"  # Windows 11 secondary text gray
COLOR_TEXT_DISABLED = "#535a73"  # Disabled element text
COLOR_TEXT_ALERT    = "#ff7b89"  # Fluent warning soft red
COLOR_BADGE_BG      = "#252a3d"  # Pill badge container background

FONT_FAMILY         = "Segoe UI Variable Text" if sys.platform == "win32" else "Segoe UI"


# =============================================================================
# 64-BIT WIN32 & GDI+ DYNAMIC ICON RESOLUTION
# =============================================================================
if sys.platform == "win32":
    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32
    gdi32 = ctypes.windll.gdi32
    gdiplus = ctypes.windll.gdiplus
    kernel32 = ctypes.windll.kernel32

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

    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND

    user32.DestroyIcon.argtypes = [wintypes.HICON]
    user32.DestroyIcon.restype = wintypes.BOOL

    user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SendMessageW.restype = wintypes.LPARAM

    user32.LoadImageW.argtypes = [
        wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
        ctypes.c_int, ctypes.c_int, wintypes.UINT
    ]
    user32.LoadImageW.restype = wintypes.HANDLE

    class SHFILEINFOW(ctypes.Structure):
        _fields_ = [
            ("hIcon", wintypes.HICON),
            ("iIcon", ctypes.c_int),
            ("dwAttributes", wintypes.DWORD),
            ("szDisplayName", wintypes.WCHAR * 260),
            ("szTypeName", wintypes.WCHAR * 80)
        ]

    shell32.SHGetFileInfoW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(SHFILEINFOW), wintypes.UINT, wintypes.UINT
    ]
    shell32.SHGetFileInfoW.restype = ctypes.c_ulonglong

    SHGFI_ICON = 0x000000100
    SHGFI_SMALLICON = 0x000000001
    SHGFI_USEFILEATTRIBUTES = 0x000000010
    FILE_ATTRIBUTE_DIRECTORY = 0x00000010
    FILE_ATTRIBUTE_NORMAL = 0x00000080

    class GdiplusStartupInput(ctypes.Structure):
        _fields_ = [
            ("GdiplusVersion", wintypes.UINT),
            ("DebugEventCallback", ctypes.c_void_p),
            ("SuppressBackgroundThread", wintypes.BOOL),
            ("SuppressExternalCodecs", wintypes.BOOL)
        ]

    class GdiplusRect(ctypes.Structure):
        _fields_ = [
            ("X", ctypes.c_int),
            ("Y", ctypes.c_int),
            ("Width", ctypes.c_int),
            ("Height", ctypes.c_int)
        ]

    class GdiplusBitmapData(ctypes.Structure):
        _fields_ = [
            ("Width", wintypes.UINT),
            ("Height", wintypes.UINT),
            ("Stride", ctypes.c_int),
            ("PixelFormat", ctypes.c_int),
            ("Scan0", ctypes.c_void_p),
            ("Reserved", ctypes.c_void_p)
        ]

    gdiplus_token = ctypes.c_ulonglong(0)
    gdiplus_input = GdiplusStartupInput(1, None, False, False)
    gdiplus.GdiplusStartup(ctypes.byref(gdiplus_token), ctypes.byref(gdiplus_input), None)

    gdiplus.GdipCreateBitmapFromHICON.argtypes = [wintypes.HICON, ctypes.POINTER(ctypes.c_void_p)]
    gdiplus.GdipCreateBitmapFromHICON.restype = ctypes.c_int

    gdiplus.GdipGetImageWidth.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.UINT)]
    gdiplus.GdipGetImageWidth.restype = ctypes.c_int

    gdiplus.GdipGetImageHeight.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.UINT)]
    gdiplus.GdipGetImageHeight.restype = ctypes.c_int

    gdiplus.GdipBitmapLockBits.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(GdiplusRect), wintypes.UINT,
        ctypes.c_int, ctypes.POINTER(GdiplusBitmapData)
    ]
    gdiplus.GdipBitmapLockBits.restype = ctypes.c_int

    gdiplus.GdipBitmapUnlockBits.argtypes = [ctypes.c_void_p, ctypes.POINTER(GdiplusBitmapData)]
    gdiplus.GdipBitmapUnlockBits.restype = ctypes.c_int

    gdiplus.GdipDisposeImage.argtypes = [ctypes.c_void_p]
    gdiplus.GdipDisposeImage.restype = ctypes.c_int


# =============================================================================
# APPLICATION ICON HELPER (WIN32 WM_SETICON)
# =============================================================================
def apply_app_icon(window):
    """Applies icon.ico directly to Window Titlebar (WM_SETICON) and Taskbar."""
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))

    icon_paths = [
        os.path.join(app_dir, "icon.ico"),
        os.path.join(os.getcwd(), "icon.ico")
    ]
    if hasattr(sys, '_MEIPASS'):
        icon_paths.insert(0, os.path.join(sys._MEIPASS, "icon.ico"))

    found_path = None
    for p in icon_paths:
        if os.path.exists(p):
            found_path = os.path.abspath(p)
            break

    if not found_path:
        return

    try:
        window.iconbitmap(found_path)
    except Exception:
        pass

    if sys.platform == "win32":
        def _set_win32_icon():
            try:
                window.update_idletasks()
                raw_id = window.winfo_id()
                hwnd = user32.GetAncestor(wintypes.HWND(raw_id), 2) or raw_id

                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1

                hSmallIcon = user32.LoadImageW(None, found_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                if hSmallIcon:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hSmallIcon)

                hBigIcon = user32.LoadImageW(None, found_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                if hBigIcon:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hBigIcon)
            except Exception:
                pass

        window.after(60, _set_win32_icon)
        window.after(300, _set_win32_icon)


# =============================================================================
# GDI+ WINDOWS 11 DYNAMIC ICON EXTRACTOR
# =============================================================================
_ICON_CACHE = {}

def get_native_windows_icon(path, size=20):
    """Extracts Windows 11 system icons preserving full 32-bit ARGB alpha transparency."""
    if sys.platform != "win32" or not HAS_PIL:
        return None

    is_dir = False
    if os.path.exists(path):
        is_dir = os.path.isdir(path)
    else:
        ext_check = os.path.splitext(path)[1].lower()
        if not ext_check or path.endswith(("\\", "/")):
            is_dir = True

    ext = "" if is_dir else os.path.splitext(path)[1].lower()
    cache_key = f"DIR_{size}" if is_dir else f"EXT_{ext}_{size}"

    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]

    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))

    # Custom .fzip vault icon
    if ext in [".fzip", ".fz"]:
        vault_ico_paths = [
            os.path.join(app_dir, "vault_icon.ico"),
            os.path.join(os.getcwd(), "vault_icon.ico"),
            os.path.join(app_dir, "icon.ico")
        ]
        for vip in vault_ico_paths:
            if os.path.exists(vip):
                try:
                    img = Image.open(vip).convert("RGBA")
                    img = img.resize((size, size), Image.Resampling.LANCZOS)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
                    _ICON_CACHE[cache_key] = ctk_img
                    return ctk_img
                except Exception:
                    pass

    shfi = SHFILEINFOW()
    flags = SHGFI_ICON | SHGFI_SMALLICON

    if not os.path.exists(path):
        flags |= SHGFI_USEFILEATTRIBUTES
        attr = FILE_ATTRIBUTE_DIRECTORY if is_dir else FILE_ATTRIBUTE_NORMAL
        query_path = path if is_dir else f"dummy{ext}"
        shell32.SHGetFileInfoW(query_path, attr, ctypes.byref(shfi), ctypes.sizeof(shfi), flags)
    else:
        shell32.SHGetFileInfoW(path, 0, ctypes.byref(shfi), ctypes.sizeof(shfi), flags)

    hIcon = shfi.hIcon
    if not hIcon:
        return None

    try:
        pBitmap = ctypes.c_void_p()
        if gdiplus.GdipCreateBitmapFromHICON(hIcon, ctypes.byref(pBitmap)) != 0:
            user32.DestroyIcon(hIcon)
            return None

        w = wintypes.UINT(0)
        h = wintypes.UINT(0)
        gdiplus.GdipGetImageWidth(pBitmap, ctypes.byref(w))
        gdiplus.GdipGetImageHeight(pBitmap, ctypes.byref(h))
        native_w = w.value or 32
        native_h = h.value or 32

        rect = GdiplusRect(0, 0, native_w, native_h)
        bmData = GdiplusBitmapData()
        PixelFormat32bppARGB = 0x26200A
        ImageLockModeRead = 1

        if gdiplus.GdipBitmapLockBits(pBitmap, ctypes.byref(rect), ImageLockModeRead, PixelFormat32bppARGB, ctypes.byref(bmData)) != 0:
            gdiplus.GdipDisposeImage(pBitmap)
            user32.DestroyIcon(hIcon)
            return None

        stride = bmData.Stride
        raw_size = abs(stride) * native_h
        buf = (ctypes.c_ubyte * raw_size).from_address(bmData.Scan0)
        raw_bytes = bytes(buf)

        img = Image.frombuffer("RGBA", (native_w, native_h), raw_bytes, "raw", "BGRA", stride, 1)

        gdiplus.GdipBitmapUnlockBits(pBitmap, ctypes.byref(bmData))
        gdiplus.GdipDisposeImage(pBitmap)
        user32.DestroyIcon(hIcon)

        if (native_w, native_h) != (size, size):
            img = img.resize((size, size), Image.Resampling.LANCZOS)

        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        _ICON_CACHE[cache_key] = ctk_img
        return ctk_img

    except Exception:
        if hIcon:
            user32.DestroyIcon(hIcon)
        return None


def apply_windows_dark_titlebar(window):
    """Enforces dark mode title bar on Windows 10/11."""
    if sys.platform != "win32":
        return
    try:
        window.update()
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        raw_id = window.winfo_id()
        hwnd = user32.GetAncestor(wintypes.HWND(raw_id), 2) or raw_id
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


def enable_windows_dnd_and_mouse(window, dnd_callback, nav_callback=None):
    """64-bit Drag-and-Drop & Crash-Proof Navigation Hook."""
    if sys.platform != "win32":
        return
    try:
        window.update()
        raw_id = window.winfo_id()
        hwnd_root = user32.GetAncestor(wintypes.HWND(raw_id), 2) or raw_id

        shell32.DragAcceptFiles(hwnd_root, True)
        GWL_WNDPROC = -4
        WM_DROPFILES = 0x0233
        WM_XBUTTONDOWN = 0x020B
        WM_NCXBUTTONDOWN = 0x00AB
        WM_APPCOMMAND = 0x0319

        old_wndproc = GetWindowLongPtr(hwnd_root, GWL_WNDPROC)
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
                if dnd_callback:
                    window.after(10, lambda: dnd_callback(files))
                return 0

            elif msg == WM_XBUTTONDOWN or msg == WM_NCXBUTTONDOWN:
                button = (wParam >> 16) & 0xFFFF
                if nav_callback:
                    if button == 1:
                        window.after(0, lambda: nav_callback("back"))
                        return 1
                    elif button == 2:
                        window.after(0, lambda: nav_callback("forward"))
                        return 1

            elif msg == WM_APPCOMMAND:
                cmd = (lParam >> 16) & 0xFFF
                if nav_callback:
                    if cmd == 1:
                        window.after(0, lambda: nav_callback("back"))
                        return 1
                    elif cmd == 2:
                        window.after(0, lambda: nav_callback("forward"))
                        return 1

            return user32.CallWindowProcW(old_wndproc, hWnd, msg, wParam, lParam)

        new_wndproc = WNDPROC_TYPE(py_wndproc)
        SetWindowLongPtr(hwnd_root, GWL_WNDPROC, new_wndproc)
        window._dnd_wndproc = new_wndproc

        if raw_id != hwnd_root:
            try:
                old_raw = GetWindowLongPtr(raw_id, GWL_WNDPROC)
                def py_raw_wndproc(hWnd, msg, wParam, lParam):
                    if msg == WM_XBUTTONDOWN or msg == WM_NCXBUTTONDOWN:
                        b = (wParam >> 16) & 0xFFFF
                        if nav_callback:
                            if b == 1: window.after(0, lambda: nav_callback("back"))
                            elif b == 2: window.after(0, lambda: nav_callback("forward"))
                        return 1
                    return user32.CallWindowProcW(old_raw, hWnd, msg, wParam, lParam)
                new_raw = WNDPROC_TYPE(py_raw_wndproc)
                SetWindowLongPtr(raw_id, GWL_WNDPROC, new_raw)
                window._raw_wndproc = new_raw
            except Exception:
                pass

    except Exception as e:
        print(f"Hook error: {e}")


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
# CONFLICT STATE HELPER & 7-ZIP STYLE COMPACT RESOLUTION DIALOG
# =============================================================================
class ConflictState:
    def __init__(self):
        self.action = None
        self.apply_to_all = False

def prompt_file_conflict(existing_path, incoming_info, conflict_state):
    """Pops up the 7-Zip style rich Conflict Resolution Dialog comparing both items."""
    if conflict_state.apply_to_all and conflict_state.action:
        return conflict_state.action

    app = ctk.CTk()
    app.withdraw()
    result = [None, False]

    def on_choice(choice, apply_all):
        result[0] = choice
        result[1] = apply_all
        app.destroy()

    dialog = FileConflictDialog(app, existing_path, incoming_info, on_choice)
    dialog.protocol("WM_DELETE_WINDOW", lambda: app.destroy())
    app.mainloop()

    choice = result[0] or "skip"
    if result[1]:
        conflict_state.apply_to_all = True
        conflict_state.action = choice
    return choice


def resolve_collision_path(dest_path, incoming_info, conflict_state):
    """Checks collision and resolves path with safe non-destructive Replace/Keep Both/Skip."""
    if not os.path.exists(dest_path):
        return dest_path, "write"

    choice = prompt_file_conflict(dest_path, incoming_info, conflict_state)
    if choice == "replace":
        return dest_path, "write"

    elif choice == "keep_both":
        parent = os.path.dirname(dest_path)
        base, ext = os.path.splitext(os.path.basename(dest_path))
        counter = 1
        new_path = os.path.join(parent, f"{base} ({counter}){ext}")
        while os.path.exists(new_path):
            counter += 1
            new_path = os.path.join(parent, f"{base} ({counter}){ext}")
        return new_path, "write"

    return dest_path, "skip"


# =============================================================================
# 7-ZIP STYLE COMPACT CONFLICT INSPECTION DIALOG (520x370)
# =============================================================================
class FileConflictDialog(ctk.CTkToplevel):
    def __init__(self, parent, existing_path, incoming_info, callback):
        super().__init__(parent)
        ctk.set_appearance_mode("Dark")
        self.existing_path = existing_path
        self.incoming_info = incoming_info or {}
        self.callback = callback
        self.choice = None
        self.apply_to_all = False

        self.title("Confirm File Replace")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.grab_set()

        apply_app_icon(self)
        center_window_on_screen(self, 520, 370)
        apply_windows_dark_titlebar(self)

        card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        hdr_lbl = ctk.CTkLabel(
            card, text="Confirm File / Folder Replace",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_TEXT_PRIMARY
        )
        hdr_lbl.pack(anchor="w", padx=14, pady=(10, 2))

        sub_lbl = ctk.CTkLabel(
            card, text="The destination already has an item with this name:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_MUTED, justify="left"
        )
        sub_lbl.pack(anchor="w", padx=14, pady=(0, 8))

        # Existing Item Card
        exist_card = ctk.CTkFrame(card, fg_color=COLOR_FIELD_BG, corner_radius=6, border_width=1, border_color=COLOR_BORDER)
        exist_card.pack(fill="x", padx=14, pady=4)

        is_folder = os.path.isdir(existing_path) if os.path.exists(existing_path) else False
        exist_size_b = os.path.getsize(existing_path) if os.path.exists(existing_path) and not is_folder else 0
        if is_folder:
            item_count = len(os.listdir(existing_path)) if os.path.exists(existing_path) else 0
            exist_size_str = f"Folder ({item_count} items inside)"
        else:
            exist_size_str = f"{round(exist_size_b/(1024*1024), 2)} MB ({exist_size_b:,} bytes)"

        exist_time = datetime.datetime.fromtimestamp(os.path.getmtime(existing_path)).strftime("%b %d, %Y - %I:%M:%S %p") if os.path.exists(existing_path) else "-"

        ctk.CTkLabel(
            exist_card, text=f"EXISTING: {os.path.basename(existing_path)}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_PRIMARY, anchor="w"
        ).pack(anchor="w", padx=12, pady=(8, 2))

        ctk.CTkLabel(
            exist_card, text=f"Size: {exist_size_str}   |   Modified: {exist_time}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=COLOR_TEXT_MUTED, anchor="w"
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Incoming Item Card
        in_card = ctk.CTkFrame(card, fg_color=COLOR_FIELD_BG, corner_radius=6, border_width=1, border_color=COLOR_BORDER)
        in_card.pack(fill="x", padx=14, pady=4)

        in_size_b = self.incoming_info.get("size", 0)
        in_is_folder = self.incoming_info.get("is_folder", False)
        if in_is_folder:
            in_size_str = "Incoming Folder"
        elif in_size_b:
            in_size_str = f"{round(in_size_b/(1024*1024), 2)} MB ({in_size_b:,} bytes)"
        else:
            in_size_str = "Incoming Item"

        in_time = self.incoming_info.get("time", "Current Operation")

        tag = ""
        if in_size_b and exist_size_b:
            if in_size_b > exist_size_b: tag = "  [ Larger ]"
            elif in_size_b < exist_size_b: tag = "  [ Smaller ]"

        ctk.CTkLabel(
            in_card, text=f"INCOMING: {os.path.basename(existing_path)}{tag}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_ACCENT_TEXT, anchor="w"
        ).pack(anchor="w", padx=12, pady=(8, 2))

        ctk.CTkLabel(
            in_card, text=f"Size: {in_size_str}   |   Date: {in_time}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=COLOR_TEXT_MUTED, anchor="w"
        ).pack(anchor="w", padx=12, pady=(0, 8))

        self.chk_all_var = ctk.BooleanVar(value=False)
        chk_all = ctk.CTkCheckBox(
            card, text="Apply to all remaining conflicts", variable=self.chk_all_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER, corner_radius=4, height=20
        )
        chk_all.pack(anchor="w", padx=14, pady=(10, 10))

        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.pack(fill="x", padx=14, pady=(0, 10))

        btn_replace = ctk.CTkButton(
            btn_box, text="Replace", fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER,
            text_color="#FFFFFF", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=100, height=32, corner_radius=6, command=lambda: self._select("replace")
        )
        btn_replace.pack(side="left", padx=(0, 6))

        btn_rename = ctk.CTkButton(
            btn_box, text="Keep Both", fg_color=COLOR_FIELD_BG, hover_color=COLOR_ROW_HOVER,
            border_width=1, border_color=COLOR_BORDER,
            text_color="#FFFFFF", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=110, height=32, corner_radius=6, command=lambda: self._select("keep_both")
        )
        btn_rename.pack(side="left", padx=4)

        btn_skip = ctk.CTkButton(
            btn_box, text="Skip", fg_color=COLOR_FIELD_BG, hover_color=COLOR_ROW_HOVER,
            border_width=1, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=85, height=32, corner_radius=6, command=lambda: self._select("skip")
        )
        btn_skip.pack(side="left", padx=(4, 0))

    def _select(self, action):
        self.choice = action
        self.apply_to_all = self.chk_all_var.get()
        self.destroy()
        if self.callback:
            self.callback(action, self.apply_to_all)


# =============================================================================
# WINDOWS 11 FLUENT HOVER TOOLTIP MODULE
# =============================================================================
class FloatingTooltip:
    """Creates a Windows 11 style fluent dark tooltip."""
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
            tw, background=COLOR_TOP_CHROME,
            highlightbackground=COLOR_BORDER, highlightthickness=1, padx=2, pady=2
        )
        frame.pack()

        label = tk.Label(
            frame, text=self.text, justify=tk.LEFT,
            background=COLOR_TOP_CHROME, foreground=COLOR_TEXT_PRIMARY,
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

        card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        hdr_lbl = ctk.CTkLabel(
            card, text=f"{title}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_ACCENT_TEXT
        )
        hdr_lbl.pack(anchor="w", padx=15, pady=(12, 4))

        msg_lbl = ctk.CTkLabel(
            card, text=message,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_PRIMARY,
            justify="left", wraplength=410
        )
        msg_lbl.pack(anchor="w", padx=15, pady=(0, 12))

        btn_ok = ctk.CTkButton(
            card, text="OK", fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER,
            text_color="#FFFFFF", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=75, height=28, corner_radius=6, command=self.destroy
        )
        btn_ok.pack(side="right", padx=15, pady=(0, 10))


def show_toast(title, message):
    app = ctk.CTk()
    app.withdraw()
    toast = ToastNotification(title, message)
    toast.protocol("WM_DELETE_WINDOW", lambda: app.destroy())
    app.mainloop()


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

        self.title("Unlock Vault")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.grab_set()

        apply_app_icon(self)
        center_window_on_screen(self, 420, 230)
        apply_windows_dark_titlebar(self)

        card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        card.pack(fill="both", expand=True, padx=15, pady=15)

        hdr_lbl = ctk.CTkLabel(
            card, text="Encrypted Vault Detected",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_TEXT_PRIMARY
        )
        hdr_lbl.pack(anchor="w", padx=15, pady=(12, 2))

        sub_lbl = ctk.CTkLabel(
            card, text=f"The archive '{os.path.basename(self.archive_path)[:30]}' is password protected.\nEnter password to unlock:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_MUTED, justify="left"
        )
        sub_lbl.pack(anchor="w", padx=15, pady=(0, 10))

        pwd_row = ctk.CTkFrame(card, fg_color="transparent")
        pwd_row.pack(fill="x", padx=15, pady=5)

        self.pwd_entry = ctk.CTkEntry(
            pwd_row, show="•", fg_color=COLOR_FIELD_BG, text_color=COLOR_TEXT_PRIMARY,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6, font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            placeholder_text="Enter Password..."
        )
        self.pwd_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.pwd_entry.focus_set()
        self.pwd_entry.bind("<Return>", lambda e: self.attempt_unlock())

        self.btn_toggle = ctk.CTkButton(
            pwd_row, text="👁️", fg_color=COLOR_FIELD_BG, hover_color=COLOR_ROW_HOVER,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6,
            text_color=COLOR_TEXT_MUTED, width=32, height=32, font=ctk.CTkFont(size=12),
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
            btn_box, text="Cancel", fg_color=COLOR_FIELD_BG, hover_color=COLOR_ROW_HOVER,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6,
            text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=80, height=30, command=self.destroy
        )
        btn_cancel.pack(side="right", padx=(6, 0))

        self.btn_unlock = ctk.CTkButton(
            btn_box, text="UNLOCK", fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER,
            text_color="#FFFFFF", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=100, height=30, corner_radius=6, command=self.attempt_unlock
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

        card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        card.pack(fill="both", expand=True, padx=15, pady=15)

        hdr_lbl = ctk.CTkLabel(
            card, text="Create Compressed Archive",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_TEXT_PRIMARY
        )
        hdr_lbl.pack(anchor="w", padx=15, pady=(12, 2))

        sub_lbl = ctk.CTkLabel(
            card, text="Type a custom name and destination for your new zip file:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_MUTED, justify="left"
        )
        sub_lbl.pack(anchor="w", padx=15, pady=(0, 10))

        # Archive Name Entry
        ctk.CTkLabel(card, text="Archive Name:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=15, pady=(2, 0))
        self.name_entry = ctk.CTkEntry(
            card, fg_color=COLOR_FIELD_BG, text_color=COLOR_TEXT_PRIMARY,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6, font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.name_entry.pack(fill="x", padx=15, pady=(2, 8))
        self.name_entry.insert(0, default_archive_name)

        # Save Location Entry + Browse
        ctk.CTkLabel(card, text="Save Location:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=15, pady=(2, 0))
        loc_row = ctk.CTkFrame(card, fg_color="transparent")
        loc_row.pack(fill="x", padx=15, pady=(2, 8))

        self.loc_entry = ctk.CTkEntry(
            loc_row, fg_color=COLOR_FIELD_BG, text_color=COLOR_TEXT_PRIMARY,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6, font=ctk.CTkFont(family=FONT_FAMILY, size=11)
        )
        self.loc_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.loc_entry.insert(0, self.default_target_dir)

        btn_browse = ctk.CTkButton(
            loc_row, text="Browse...", fg_color=COLOR_FIELD_BG, hover_color=COLOR_ROW_HOVER,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6,
            text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=70, height=28, command=self.browse_location
        )
        btn_browse.pack(side="right")

        # Password Entry
        pwd_row = ctk.CTkFrame(card, fg_color="transparent")
        pwd_row.pack(fill="x", padx=15, pady=(2, 10))

        ctk.CTkLabel(pwd_row, text="Password:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 6))
        self.pwd_entry = ctk.CTkEntry(
            pwd_row, show="•", fg_color=COLOR_FIELD_BG, text_color=COLOR_TEXT_PRIMARY,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            placeholder_text="Optional Password..."
        )
        self.pwd_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_toggle = ctk.CTkButton(
            pwd_row, text="👁️", fg_color=COLOR_FIELD_BG, hover_color=COLOR_ROW_HOVER,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6,
            text_color=COLOR_TEXT_MUTED, width=30, height=28, font=ctk.CTkFont(size=12),
            command=self.toggle_pwd
        )
        self.btn_toggle.pack(side="right")

        # Buttons
        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=(12, 15))

        btn_cancel = ctk.CTkButton(
            btn_box, text="Cancel", fg_color=COLOR_FIELD_BG, hover_color=COLOR_ROW_HOVER,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6,
            text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=80, height=30, command=self.destroy
        )
        btn_cancel.pack(side="right", padx=(6, 0))

        btn_compress = ctk.CTkButton(
            btn_box, text="COMPRESS", fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER,
            text_color="#FFFFFF", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=110, height=30, corner_radius=6, command=self.start_compress
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
        if password and not archive_name.lower().endswith((".fzip", ".7z")):
            if archive_name.lower().endswith(".zip"):
                archive_name = archive_name[:-4] + ".fzip"
            else:
                archive_name += ".fzip"
        elif not password and not archive_name.lower().endswith((".zip", ".fzip")):
            archive_name += ".zip"

        self.destroy()
        if self.callback:
            self.callback(archive_name, save_dir, password)


# =============================================================================
# UNIVERSAL LIVE FLUENT PROGRESS POPUP (WITH CHUNK STREAMING & AUTO-CLOSE)
# =============================================================================
class UniversalLiveProgressDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, task_fn):
        super().__init__(parent)
        ctk.set_appearance_mode("Dark")

        self.title(title)
        self.task_fn = task_fn
        self.is_cancelled = False
        self.last_update_t = 0

        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.grab_set()

        apply_app_icon(self)
        center_window_on_screen(self, 460, 190)
        apply_windows_dark_titlebar(self)

        card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        card.pack(fill="both", expand=True, padx=15, pady=15)

        self.hdr_lbl = ctk.CTkLabel(
            card, text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_TEXT_PRIMARY
        )
        self.hdr_lbl.pack(anchor="w", padx=15, pady=(12, 4))

        self.progress_bar = ctk.CTkProgressBar(
            card, fg_color=COLOR_FIELD_BG, progress_color=COLOR_BLUE_ACCENT, height=8, corner_radius=4
        )
        self.progress_bar.pack(fill="x", padx=15, pady=(4, 8))
        self.progress_bar.set(0)

        self.lbl_file = ctk.CTkLabel(
            card, text="Starting task...", font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED, anchor="w"
        )
        self.lbl_file.pack(fill="x", padx=15, pady=(2, 0))

        self.lbl_stats = ctk.CTkLabel(
            card, text="Preparing...", font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED, anchor="w"
        )
        self.lbl_stats.pack(fill="x", padx=15, pady=(0, 10))

        threading.Thread(target=self._worker_wrapper, daemon=True).start()

    def update_status(self, current_b, total_b, start_t, item_name):
        now = time.time()
        if (now - self.last_update_t) < 0.035 and current_b < total_b:
            return
        self.last_update_t = now

        pct = (current_b / total_b) if total_b > 0 else 1.0
        if pct >= 1.0: pct = 1.0

        elapsed = max(0.001, now - start_t)
        speed = current_b / elapsed
        rem_bytes = max(0, total_b - current_b)
        rem_seconds = int(rem_bytes / speed) if speed > 0 else 0
        mins, secs = divmod(rem_seconds, 60)

        cur_mb = round(current_b / (1024 * 1024), 1)
        tot_mb = round(total_b / (1024 * 1024), 1)
        speed_mb = round(speed / (1024 * 1024), 1)

        self.after(0, lambda: self.progress_bar.set(pct))
        self.after(0, lambda: self.lbl_file.configure(text=f"Processing: {item_name[:32]} ({int(pct*100)}%)"))
        self.after(0, lambda: self.lbl_stats.configure(
            text=f"Size: {cur_mb} MB / {tot_mb} MB  |  Speed: {speed_mb} MB/s  |  Est: {mins:02d}:{secs:02d}"
        ))

    def _worker_wrapper(self):
        try:
            self.task_fn(self.update_status, lambda: self.is_cancelled)
        except Exception as e:
            print(f"Task error: {e}")
        finally:
            self.after(0, self._cleanup_and_close)

    def _cleanup_and_close(self):
        try:
            self.progress_bar.set(1.0)
            self.destroy()
            if self.master:
                self.master.destroy()
        except Exception:
            pass


# =============================================================================
# MAIN GUI APPLICATION CLASS (WINDOWS 11 FLUENT DARK)
# =============================================================================
class FusionZipApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Fusion Zip")
        self.minsize(800, 520)
        self.resizable(True, True)
        self.configure(fg_color=COLOR_BG_DARK)

        apply_app_icon(self)
        center_window_on_screen(self, 880, 580)
        apply_windows_dark_titlebar(self)

        # Application Navigation State
        self.queue_items = []
        self.current_folder_view = None
        self.history_back = []
        self.history_forward = []
        self.last_output_dir = None
        self.is_processing = False

        # Build Fluent UI Components
        self._build_top_command_bar()
        self._build_data_grid()
        self._build_linear_control_row()
        self._build_status_and_progress_strip()

        enable_windows_dnd_and_mouse(self, self.on_files_dropped, self.handle_mouse_nav)
        self._refresh_grid()

    def _build_top_command_bar(self):
        """Windows 11 Command Bar and Breadcrumb Capsule."""
        top_command_card = ctk.CTkFrame(
            self, fg_color=COLOR_TOP_CHROME, corner_radius=0, height=48,
            border_width=1, border_color=COLOR_BORDER
        )
        top_command_card.pack(fill="x", padx=0, pady=(0, 6))

        inner_command = ctk.CTkFrame(top_command_card, fg_color="transparent")
        inner_command.pack(fill="x", padx=16, pady=8)

        self.btn_add = ctk.CTkButton(
            inner_command, text="➕ Add Items", fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER,
            text_color="#FFFFFF", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            corner_radius=6, height=32, width=110, command=self.add_items_dialog
        )
        self.btn_add.pack(side="left", padx=(0, 12))
        FloatingTooltip(self.btn_add, "Browse files or folders into your staging queue.")

        self.address_bar = ctk.CTkFrame(
            inner_command, fg_color=COLOR_FIELD_BG, corner_radius=6, height=32,
            border_width=1, border_color=COLOR_BORDER
        )
        self.address_bar.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.lbl_location = ctk.CTkLabel(
            self.address_bar, text="📁 Staging Queue",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_MUTED, anchor="w"
        )
        self.lbl_location.pack(side="left", padx=12, fill="x", expand=True)

    def _build_data_grid(self):
        """Windows 11 Elevated List View Container."""
        self.grid_card = ctk.CTkFrame(
            self, fg_color=COLOR_CARD_BG, corner_radius=10,
            border_width=1, border_color=COLOR_BORDER
        )
        self.grid_card.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        self.hdr_frame = ctk.CTkFrame(
            self.grid_card, fg_color=COLOR_FIELD_BG, corner_radius=6, height=30,
            border_width=1, border_color=COLOR_BORDER
        )
        self.hdr_frame.pack(fill="x", padx=8, pady=(8, 4))

        hdr_name = ctk.CTkLabel(self.hdr_frame, text="Name 🔼", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED, anchor="w")
        hdr_name.pack(side="left", padx=15, expand=True, fill="x")

        hdr_size = ctk.CTkLabel(self.hdr_frame, text="Size", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED, width=95, anchor="e")
        hdr_size.pack(side="left", padx=10)

        hdr_type = ctk.CTkLabel(self.hdr_frame, text="Type", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED, width=105, anchor="center")
        hdr_type.pack(side="left", padx=10)

        hdr_date = ctk.CTkLabel(self.hdr_frame, text="Date Modified", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED, width=135, anchor="center")
        hdr_date.pack(side="left", padx=10)

        hdr_del = ctk.CTkLabel(self.hdr_frame, text="Remove", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED, width=50, anchor="center")
        hdr_del.pack(side="left", padx=(10, 15))

        self.scroll_frame = ctk.CTkScrollableFrame(
            self.grid_card, fg_color="transparent", corner_radius=0,
            border_width=0, scrollbar_button_color="#30374e", scrollbar_button_hover_color=COLOR_BLUE_ACCENT
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _build_linear_control_row(self):
        """Windows 11 Bottom Control Panel."""
        ctrl_card = ctk.CTkFrame(
            self, fg_color=COLOR_CARD_BG, corner_radius=10,
            border_width=1, border_color=COLOR_BORDER
        )
        ctrl_card.pack(fill="x", padx=16, pady=(0, 6))

        inner_row = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        inner_row.pack(fill="x", padx=12, pady=10)

        left_box = ctk.CTkFrame(inner_row, fg_color="transparent")
        left_box.pack(side="left", anchor="w")

        # Archive Name Field
        name_frame = ctk.CTkFrame(left_box, fg_color="transparent")
        name_frame.pack(anchor="w", side="left", padx=(0, 15))

        ctk.CTkLabel(name_frame, text="Archive Name:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 6))

        self.archive_name_entry = ctk.CTkEntry(
            name_frame, fg_color=COLOR_FIELD_BG, text_color=COLOR_TEXT_PRIMARY,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6, width=160, height=32, placeholder_text="Archive.zip"
        )
        self.archive_name_entry.pack(side="left")
        FloatingTooltip(self.archive_name_entry, "Type a custom name for your compressed zip file.")

        # Password Field
        pwd_frame = ctk.CTkFrame(left_box, fg_color="transparent")
        pwd_frame.pack(anchor="w", side="left")

        ctk.CTkLabel(pwd_frame, text="Password:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 6))

        self.pwd_entry = ctk.CTkEntry(
            pwd_frame, show="•", fg_color=COLOR_FIELD_BG, text_color=COLOR_TEXT_PRIMARY,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6, width=140, height=32, placeholder_text="Optional Password"
        )
        self.pwd_entry.pack(side="left")
        FloatingTooltip(self.pwd_entry, "Typing a password locks both file contents and file names.")

        self.btn_toggle_pwd = ctk.CTkButton(
            pwd_frame, text="👁️", fg_color=COLOR_FIELD_BG, hover_color=COLOR_ROW_HOVER,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6,
            text_color=COLOR_TEXT_MUTED, width=32, height=32, font=ctk.CTkFont(size=12),
            command=self.toggle_password_visibility
        )
        self.btn_toggle_pwd.pack(side="left", padx=(4, 0))

        right_box = ctk.CTkFrame(inner_row, fg_color="transparent")
        right_box.pack(side="right", anchor="e")

        self.btn_compress = ctk.CTkButton(
            right_box, text="COMPRESS", fg_color=COLOR_FIELD_BG, hover_color=COLOR_FIELD_BG,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6,
            text_color=COLOR_TEXT_DISABLED, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=34, width=115, state="disabled", command=self.start_compression_thread
        )
        self.btn_compress.pack(side="left", padx=4)

        self.btn_extract = ctk.CTkButton(
            right_box, text="EXTRACT", fg_color=COLOR_FIELD_BG, hover_color=COLOR_FIELD_BG,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6,
            text_color=COLOR_TEXT_DISABLED, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=34, width=115, state="disabled", command=self.start_extraction_thread
        )
        self.btn_extract.pack(side="left", padx=4)

    def _build_status_and_progress_strip(self):
        """Windows 11 Explorer Status Bar."""
        self.status_strip = ctk.CTkFrame(self, fg_color="transparent")
        self.status_strip.pack(fill="x", padx=16, pady=(0, 6))

        self.lbl_status = ctk.CTkLabel(
            self.status_strip, text="Ready | 0 items queued",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_MUTED
        )
        self.lbl_status.pack(side="left")

        self.btn_open_folder = ctk.CTkButton(
            self.status_strip, text="📁 Open Folder", fg_color=COLOR_FIELD_BG, hover_color=COLOR_ROW_HOVER,
            border_width=1, border_color=COLOR_BORDER, corner_radius=6,
            text_color=COLOR_ACCENT_TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=24, width=95, command=self.open_output_folder
        )

        self.progress_bar = ctk.CTkProgressBar(
            self.status_strip, fg_color=COLOR_FIELD_BG, progress_color=COLOR_BLUE_ACCENT, height=6, width=240, corner_radius=3
        )

    def toggle_password_visibility(self):
        if self.pwd_entry.cget("show") == "•":
            self.pwd_entry.configure(show="")
            self.btn_toggle_pwd.configure(text="🔒")
        else:
            self.pwd_entry.configure(show="•")
            self.btn_toggle_pwd.configure(text="👁️")

    def handle_mouse_nav(self, direction):
        """Processes hardware side mouse button clicks (Thumb 1: Back, Thumb 2: Forward)."""
        try:
            if direction == "back":
                if self.history_back:
                    prev_loc = self.history_back.pop()
                    self.history_forward.append(self.current_folder_view)
                    self.current_folder_view = prev_loc
                    self._refresh_grid()
                elif self.current_folder_view:
                    self.history_forward.append(self.current_folder_view)
                    self.current_folder_view = None
                    self._refresh_grid()

            elif direction == "forward":
                if self.history_forward:
                    next_loc = self.history_forward.pop()
                    self.history_back.append(self.current_folder_view)
                    self.current_folder_view = next_loc
                    self._refresh_grid()
        except Exception as e:
            print(f"Nav error: {e}")

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
        if self.current_folder_view:
            messagebox.showinfo("Queue Notice", "Items inside subfolders are part of the active folder structure.")
            return
        self.queue_items = [x for x in self.queue_items if x["path"] != target_path]
        self._refresh_grid()

    def open_output_folder(self):
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            os.startfile(self.last_output_dir)

    def inspect_folder(self, folder_path):
        if self.current_folder_view != folder_path:
            self.history_back.append(self.current_folder_view)
            self.history_forward.clear()
            self.current_folder_view = folder_path
            self._refresh_grid()

    def inspect_archive(self, archive_path):
        if check_archive_encrypted(archive_path):
            EncryptedArchiveDialog(self, archive_path, self._on_archive_unlocked)
        else:
            self.inspect_folder(archive_path)

    def _on_archive_unlocked(self, archive_path, password):
        self.pwd_entry.delete(0, tk.END)
        self.pwd_entry.insert(0, password)
        self.inspect_folder(archive_path)

    def step_up_folder(self):
        """Returns to main staging queue when stepping up from a top-level queued item."""
        if self.current_folder_view:
            self.history_back.append(self.current_folder_view)
            self.history_forward.clear()
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
            self.lbl_location.configure(text=f"📁 {self.current_folder_view}")
            up_row = ctk.CTkFrame(
                self.scroll_frame, fg_color=COLOR_FIELD_BG, corner_radius=6,
                border_width=1, border_color=COLOR_BORDER
            )
            up_row.pack(fill="x", pady=2)

            up_lbl = ctk.CTkLabel(
                up_row, text="📁 [ .. Up One Level ]", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=COLOR_ACCENT_TEXT, anchor="w"
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

                elif ext == ".zip" or (os.path.isfile(self.current_folder_view) and ext != ""):
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

        self.lbl_location.configure(text="📁 Staging Queue")
        count = len(self.queue_items)

        if count == 0:
            empty_card = ctk.CTkFrame(
                self.scroll_frame, fg_color=COLOR_FIELD_BG, corner_radius=12,
                border_width=2, border_color="#2b3858"
            )
            empty_card.pack(fill="x", expand=True, padx=40, pady=50)

            ctk.CTkLabel(
                empty_card, text="📥", font=ctk.CTkFont(size=36)
            ).pack(pady=(28, 4))

            ctk.CTkLabel(
                empty_card, text="Drag & Drop Files or Folders Here",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=COLOR_TEXT_PRIMARY
            ).pack(pady=(0, 2))

            ctk.CTkLabel(
                empty_card, text="or click '+ Add Items' above to stage files for compression & extraction",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLOR_TEXT_MUTED
            ).pack(pady=(0, 28))

            self.btn_compress.configure(
                state="disabled", fg_color=COLOR_FIELD_BG,
                border_color=COLOR_BORDER, text_color=COLOR_TEXT_DISABLED
            )
            self.btn_extract.configure(
                state="disabled", fg_color=COLOR_FIELD_BG,
                border_color=COLOR_BORDER, text_color=COLOR_TEXT_DISABLED
            )
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

        self.btn_compress.configure(
            state="normal", fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER,
            border_color=COLOR_BLUE_ACCENT, text_color=COLOR_TEXT_PRIMARY
        )
        self.btn_extract.configure(
            state="normal", fg_color=COLOR_BLUE_ACCENT, hover_color=COLOR_BLUE_HOVER,
            border_color=COLOR_BLUE_ACCENT, text_color=COLOR_TEXT_PRIMARY
        )
        self.lbl_status.configure(text=f"Ready | {count} items queued")

    def _render_grid_row(self, path, is_inside=False):
        row = ctk.CTkFrame(
            self.scroll_frame, fg_color=COLOR_FIELD_BG, corner_radius=6,
            border_width=1, border_color=COLOR_BORDER
        )
        row.pack(fill="x", pady=2)

        is_dir = os.path.isdir(path) if os.path.exists(path) else not os.path.splitext(path)[1]
        ext = os.path.splitext(path)[1].lower()
        is_arch = ext in [".zip", ".7z", ".fz", ".fzip", ".rar", ".tar", ".gz", ".bz2", ".xz"]
        name = os.path.basename(path) or path

        native_icon = get_native_windows_icon(path, size=20)

        if is_dir:
            size_str = f"{len(os.listdir(path))} items" if os.path.exists(path) else "-"
            ftype = "File folder"
        elif is_arch:
            size_str = f"{round(os.path.getsize(path)/(1024*1024), 2)} MB" if os.path.exists(path) else "-"
            ftype = "Vault" if ext in [".fzip", ".fz"] else "Archive"
        else:
            size_str = f"{round(os.path.getsize(path)/1024, 1)} KB" if os.path.exists(path) else "-"
            ftype = Path(path).suffix[1:].upper() + " File" if Path(path).suffix else "File"

        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%m/%d/%Y %I:%M %p") if os.path.exists(path) else "-"

        name_box = ctk.CTkFrame(row, fg_color="transparent")
        name_box.pack(side="left", padx=(10, 5), pady=5, expand=True, fill="x")

        if native_icon:
            icon_lbl = ctk.CTkLabel(name_box, text="", image=native_icon, width=24)
            icon_lbl.pack(side="left", padx=(0, 8))
        else:
            icon_txt = "📁" if is_dir else ("📦" if is_arch else "📄")
            icon_lbl = ctk.CTkLabel(name_box, text=icon_txt, font=ctk.CTkFont(family=FONT_FAMILY, size=12))
            icon_lbl.pack(side="left", padx=(0, 8))

        name_lbl = ctk.CTkLabel(
            name_box, text=name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY, anchor="w"
        )
        name_lbl.pack(side="left", fill="x", expand=True)

        size_lbl = ctk.CTkLabel(
            row, text=size_str, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED, width=95, anchor="e"
        )
        size_lbl.pack(side="left", padx=10)

        badge_fg = "#1e3a5f" if is_arch else ("#3b2d18" if is_dir else COLOR_BADGE_BG)
        badge_txt_c = COLOR_ACCENT_TEXT if is_arch else ("#fcd34d" if is_dir else COLOR_TEXT_MUTED)

        type_badge = ctk.CTkFrame(row, fg_color=badge_fg, corner_radius=4, width=105, height=22)
        type_badge.pack(side="left", padx=10)
        type_badge.pack_propagate(False)

        type_lbl = ctk.CTkLabel(
            type_badge, text=ftype, font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=badge_txt_c, anchor="center"
        )
        type_lbl.pack(fill="both", expand=True)

        date_lbl = ctk.CTkLabel(
            row, text=mtime, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED, width=135, anchor="center"
        )
        date_lbl.pack(side="left", padx=10)

        del_btn = ctk.CTkButton(
            row, text="✖", fg_color="transparent", hover_color=COLOR_ROW_HOVER,
            text_color=COLOR_TEXT_ALERT, width=26, height=26, font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda p=path: self.remove_item(p)
        )
        del_btn.pack(side="left", padx=(5, 12))
        FloatingTooltip(del_btn, "Remove from queue.")

        def on_enter(e): row.configure(fg_color=COLOR_ROW_HOVER)
        def on_leave(e): row.configure(fg_color=COLOR_FIELD_BG)
        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)

        if is_dir:
            row.bind("<Double-1>", lambda e, p=path: self.inspect_folder(p))
            name_lbl.bind("<Double-1>", lambda e, p=path: self.inspect_folder(p))
            name_box.bind("<Double-1>", lambda e, p=path: self.inspect_folder(p))
        elif is_arch:
            row.bind("<Double-1>", lambda e, p=path: self.inspect_archive(p))
            name_lbl.bind("<Double-1>", lambda e, p=path: self.inspect_archive(p))
            name_box.bind("<Double-1>", lambda e, p=path: self.inspect_archive(p))

    def _render_generic_member_row(self, filename, size_b=0):
        row = ctk.CTkFrame(
            self.scroll_frame, fg_color=COLOR_FIELD_BG, corner_radius=6,
            border_width=1, border_color=COLOR_BORDER
        )
        row.pack(fill="x", pady=2)

        native_icon = get_native_windows_icon(filename, size=20)
        size_str = f"{round(size_b/1024, 1)} KB" if size_b else "-"

        name_box = ctk.CTkFrame(row, fg_color="transparent")
        name_box.pack(side="left", padx=(10, 5), pady=5, expand=True, fill="x")

        if native_icon:
            ctk.CTkLabel(name_box, text="", image=native_icon, width=24).pack(side="left", padx=(0, 8))
        else:
            ctk.CTkLabel(name_box, text="📄", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))

        name_lbl = ctk.CTkLabel(
            name_box, text=filename,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY, anchor="w"
        )
        name_lbl.pack(side="left", fill="x", expand=True)

        size_lbl = ctk.CTkLabel(
            row, text=size_str, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED, width=95, anchor="e"
        )
        size_lbl.pack(side="left", padx=10)

        type_badge = ctk.CTkFrame(row, fg_color=COLOR_BADGE_BG, corner_radius=4, width=105, height=22)
        type_badge.pack(side="left", padx=10)
        type_badge.pack_propagate(False)

        type_lbl = ctk.CTkLabel(
            type_badge, text="Compressed", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=COLOR_TEXT_MUTED, anchor="center"
        )
        type_lbl.pack(fill="both", expand=True)

        date_lbl = ctk.CTkLabel(
            row, text="-", font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLOR_TEXT_MUTED, width=135, anchor="center"
        )
        date_lbl.pack(side="left", padx=10)

    # -------------------------------------------------------------------------
    # DUAL-MODE COMPRESSION WORKER (MAIN GUI)
    # -------------------------------------------------------------------------
    def start_compression_thread(self):
        if self.is_processing:
            return

        if self.current_folder_view and os.path.exists(self.current_folder_view):
            targets = [os.path.join(self.current_folder_view, x) for x in os.listdir(self.current_folder_view)]
            default_name = f"{os.path.basename(self.current_folder_view)}.zip"
        elif len(self.queue_items) > 0:
            targets = [x["path"] for x in self.queue_items if os.path.exists(x["path"])]
            first_item = targets[0]
            default_name = f"{os.path.splitext(os.path.basename(first_item))[0]}.zip"
        else:
            return

        if not targets:
            return

        password = self.pwd_entry.get().strip()
        custom_name = self.archive_name_entry.get().strip() or default_name

        ext = ".fzip" if password else ".zip"

        if password and custom_name.lower().endswith(".zip"):
            custom_name = custom_name[:-4] + ".fzip"
        elif not password and custom_name.lower().endswith(".fzip"):
            custom_name = custom_name[:-5] + ".zip"

        if not custom_name.lower().endswith((".zip", ".fzip")):
            custom_name += ext

        out_archive = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[("Fusion Vault Archive", "*.fzip"), ("ZIP Archive", "*.zip")],
            title="Save Archive As", initialfile=custom_name
        )
        if not out_archive:
            return

        self.last_output_dir = os.path.dirname(os.path.abspath(out_archive))
        run_live_compress(targets, os.path.basename(out_archive), self.last_output_dir, password)
        self.lbl_status.configure(text=f"Ready | Created {os.path.basename(out_archive)}")
        self.btn_open_folder.pack(side="right", padx=10)

    # -------------------------------------------------------------------------
    # UNIVERSAL EXTRACTION WORKER (MAIN GUI)
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
        run_live_extract_folder(target_archive, target_dir, password)
        self.lbl_status.configure(text="Extraction complete!")
        self.btn_open_folder.pack(side="right", padx=10)


# =============================================================================
# LIVE WORKERS (COMPRESS, EXTRACT, UNPACK) WITH CHUNK STREAMING
# =============================================================================
def run_live_compress(targets, archive_name, target_dir, password=None):
    """Executes compression with chunked byte streaming."""
    def task(update_fn, is_cancelled_fn):
        os.makedirs(target_dir, exist_ok=True)
        out_abs = os.path.join(target_dir, archive_name)

        total_bytes = 0
        valid_files = [x for x in targets if os.path.exists(x)]
        for target in valid_files:
            if os.path.isfile(target):
                total_bytes += os.path.getsize(target)
            elif os.path.isdir(target):
                for root, dirs, files in os.walk(target):
                    for f in files:
                        total_bytes += os.path.getsize(os.path.join(root, f))

        processed_bytes = 0
        start_time = time.time()

        if password and HAS_PY7ZR:
            filters = [{'id': py7zr.FILTER_LZMA2}, {'id': py7zr.FILTER_CRYPTO_AES256_SHA256}]
            with py7zr.SevenZipFile(out_abs, 'w', password=password, header_encryption=True, filters=filters) as szf:
                for target in valid_files:
                    if is_cancelled_fn(): break
                    target_abs = os.path.abspath(target)
                    if target_abs == out_abs: continue

                    if os.path.isfile(target_abs):
                        file_size = os.path.getsize(target_abs)
                        processed_bytes += file_size
                        update_fn(processed_bytes, total_bytes, start_time, os.path.basename(target_abs))
                        szf.write(target_abs, os.path.basename(target_abs))

                    elif os.path.isdir(target_abs):
                        for root, dirs, files in os.walk(target_abs):
                            if is_cancelled_fn(): break
                            for file in files:
                                full_p = os.path.abspath(os.path.join(root, file))
                                if full_p == out_abs: continue
                                processed_bytes += os.path.getsize(full_p)
                                rel_p = os.path.relpath(full_p, os.path.dirname(target_abs))
                                update_fn(processed_bytes, total_bytes, start_time, file)
                                szf.write(full_p, rel_p)
        else:
            zf = zipfile.ZipFile(out_abs, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1)
            for target in valid_files:
                if is_cancelled_fn(): break
                target_abs = os.path.abspath(target)
                if target_abs == out_abs: continue

                if os.path.isfile(target_abs):
                    file_size = os.path.getsize(target_abs)
                    processed_bytes += file_size
                    update_fn(processed_bytes, total_bytes, start_time, os.path.basename(target_abs))
                    zf.write(target_abs, os.path.basename(target_abs))

                elif os.path.isdir(target_abs):
                    for root, dirs, files in os.walk(target_abs):
                        if is_cancelled_fn(): break
                        for file in files:
                            full_p = os.path.abspath(os.path.join(root, file))
                            if full_p == out_abs: continue
                            processed_bytes += os.path.getsize(full_p)
                            rel_p = os.path.relpath(full_p, os.path.dirname(target_abs))
                            update_fn(processed_bytes, total_bytes, start_time, file)
                            zf.write(full_p, rel_p)
            zf.close()

    app = ctk.CTk()
    app.withdraw()
    dlg = UniversalLiveProgressDialog(app, f"Packaging '{archive_name[:30]}'...", task)
    dlg.protocol("WM_DELETE_WINDOW", lambda: app.destroy())
    app.mainloop()


def run_live_extract_folder(archive_path, destination_dir, password=None):
    """Extracts archive directly with live chunked streaming, file collisions, and lazy folder creation."""
    if not os.path.exists(archive_path): return

    conflict_state = ConflictState()

    # Pre-flight Root Destination Conflict Check
    if os.path.exists(destination_dir) and os.path.isdir(destination_dir) and os.listdir(destination_dir):
        choice = prompt_file_conflict(destination_dir, {"size": 0, "is_folder": True, "time": "Existing Directory"}, conflict_state)
        if choice == "skip":
            return
        elif choice == "keep_both":
            parent = os.path.dirname(destination_dir)
            base = os.path.basename(destination_dir)
            c = 1
            new_dest = os.path.join(parent, f"{base} ({c})")
            while os.path.exists(new_dest):
                c += 1
                new_dest = os.path.join(parent, f"{base} ({c})")
            destination_dir = new_dest

    def task(update_fn, is_cancelled_fn):
        ext = os.path.splitext(archive_path)[1].lower()
        start_time = time.time()
        CHUNK_SIZE = 8 * 1024 * 1024

        if os.path.isdir(archive_path):
            folder_name = os.path.basename(os.path.abspath(archive_path))
            dest_folder = os.path.join(destination_dir, folder_name)
            final_folder, status = resolve_collision_path(dest_folder, {"size": 0, "is_folder": True, "time": "Folder"}, conflict_state)
            if status == "write":
                total_bytes = sum(os.path.getsize(os.path.join(r, f)) for r, d, files in os.walk(archive_path) for f in files)
                processed = 0
                for root, dirs, files in os.walk(archive_path):
                    if is_cancelled_fn(): break
                    for f in files:
                        src_f = os.path.join(root, f)
                        rel_f = os.path.relpath(src_f, archive_path)
                        dst_f = os.path.join(final_folder, rel_f)
                        os.makedirs(os.path.dirname(dst_f), exist_ok=True)
                        with open(src_f, 'rb') as sf, open(dst_f, 'wb') as df:
                            while True:
                                if is_cancelled_fn(): break
                                chunk = sf.read(CHUNK_SIZE)
                                if not chunk: break
                                df.write(chunk)
                                processed += len(chunk)
                                update_fn(processed, total_bytes, start_time, f)
            return

        # Archive formats with fast chunked extraction
        if ext in [".7z", ".fz", ".fzip"] and HAS_PY7ZR:
            with py7zr.SevenZipFile(archive_path, 'r', password=password or None) as szf:
                infos = szf.list()
                total_bytes = sum(i.uncompressed for i in infos if not i.is_directory) or 1
                szf.extractall(path=destination_dir)
                update_fn(total_bytes, total_bytes, start_time, os.path.basename(archive_path))

        elif ext == ".rar" and HAS_RARFILE:
            with rarfile.RarFile(archive_path, 'r') as rf:
                if password: rf.setpassword(password)
                infos = rf.infolist()
                total_bytes = sum(i.file_size for i in infos if not i.isdir()) or 1
                processed = 0
                for info in infos:
                    if is_cancelled_fn(): break
                    if info.isdir(): continue
                    out_path = os.path.join(destination_dir, info.filename)
                    in_info = {"size": info.file_size, "time": str(info.date_time)}
                    final_path, status = resolve_collision_path(out_path, in_info, conflict_state)
                    if status == "write":
                        os.makedirs(os.path.dirname(final_path), exist_ok=True)
                        with rf.open(info) as src, open(final_path, 'wb') as dst:
                            while True:
                                if is_cancelled_fn(): break
                                chunk = src.read(CHUNK_SIZE)
                                if not chunk: break
                                dst.write(chunk)
                                processed += len(chunk)
                                update_fn(processed, total_bytes, start_time, os.path.basename(info.filename))
                    else:
                        processed += info.file_size
                        update_fn(processed, total_bytes, start_time, os.path.basename(info.filename))

        elif ext in [".tar", ".gz", ".bz2", ".xz"]:
            with tarfile.open(archive_path, 'r:*') as tf:
                members = tf.getmembers()
                total_bytes = sum(m.size for m in members if m.isfile()) or 1
                processed = 0
                for member in members:
                    if is_cancelled_fn(): break
                    if not member.isfile(): continue
                    out_path = os.path.join(destination_dir, member.name)
                    in_info = {"size": member.size, "time": str(member.mtime)}
                    final_path, status = resolve_collision_path(out_path, in_info, conflict_state)
                    if status == "write":
                        os.makedirs(os.path.dirname(final_path), exist_ok=True)
                        f_src = tf.extractfile(member)
                        if f_src:
                            with open(final_path, 'wb') as dst:
                                while True:
                                    if is_cancelled_fn(): break
                                    chunk = f_src.read(CHUNK_SIZE)
                                    if not chunk: break
                                    dst.write(chunk)
                                    processed += len(chunk)
                                    update_fn(processed, total_bytes, start_time, os.path.basename(member.name))
                    else:
                        processed += member.size
                        update_fn(processed, total_bytes, start_time, os.path.basename(member.name))

        else:
            zf = pyzipper.AESZipFile(archive_path, 'r') if HAS_PYZIPPER else zipfile.ZipFile(archive_path, 'r')
            if password: zf.setpassword(password.encode('utf-8'))
            infos = zf.infolist()
            total_bytes = sum(i.file_size for i in infos if not i.is_dir()) or 1
            processed = 0
            for info in infos:
                if is_cancelled_fn(): break
                if info.is_dir(): continue
                out_path = os.path.join(destination_dir, info.filename)
                in_info = {"size": info.file_size, "time": str(info.date_time)}
                final_path, status = resolve_collision_path(out_path, in_info, conflict_state)
                if status == "write":
                    os.makedirs(os.path.dirname(final_path), exist_ok=True)
                    with zf.open(info) as src, open(final_path, 'wb') as dst:
                        while True:
                            if is_cancelled_fn(): break
                            chunk = src.read(CHUNK_SIZE)
                            if not chunk: break
                            dst.write(chunk)
                            processed += len(chunk)
                            update_fn(processed, total_bytes, start_time, os.path.basename(info.filename))
                else:
                    processed += info.file_size
                    update_fn(processed, total_bytes, start_time, os.path.basename(info.filename))
            zf.close()

    app = ctk.CTk()
    app.withdraw()
    dlg = UniversalLiveProgressDialog(app, f"Extracting '{os.path.basename(archive_path)[:28]}'...", task)
    dlg.protocol("WM_DELETE_WINDOW", lambda: app.destroy())
    app.mainloop()


def run_live_unpack_folder_batch(targets, destination_dir=None):
    """1-Level Move Unpack with live progress and retry backoff."""
    if not targets: return

    conflict_state = ConflictState()

    def task(update_fn, is_cancelled_fn):
        moves = []
        total_bytes = 0

        for target in targets:
            if not os.path.exists(target): continue
            target_abs = os.path.abspath(target)
            target_parent = destination_dir or os.path.dirname(target_abs)

            if os.path.isfile(target_abs):
                moves.append(("extract", target_abs, target_parent))
                total_bytes += os.path.getsize(target_abs)
            elif os.path.isdir(target_abs):
                for item in os.listdir(target_abs):
                    src_p = os.path.join(target_abs, item)
                    dst_p = os.path.join(target_parent, item)
                    size = os.path.getsize(src_p) if os.path.isfile(src_p) else 1024*1024
                    moves.append(("move", src_p, dst_p, target_abs))
                    total_bytes += size

        total_bytes = total_bytes or 1
        processed_bytes = 0
        start_time = time.time()

        for move_info in moves:
            if is_cancelled_fn(): break

            if move_info[0] == "extract":
                _, arch_path, out_dir = move_info
                ext = os.path.splitext(arch_path)[1].lower()
                if ext == ".zip" or os.path.isfile(arch_path):
                    try:
                        with zipfile.ZipFile(arch_path, 'r') as zf:
                            for m in zf.infolist():
                                if is_cancelled_fn(): break
                                if not m.is_dir():
                                    out_p = os.path.join(out_dir, m.filename)
                                    final_p, st = resolve_collision_path(out_p, {"size": m.file_size, "time": str(m.date_time)}, conflict_state)
                                    if st == "write":
                                        os.makedirs(os.path.dirname(final_p), exist_ok=True)
                                        with zf.open(m) as s, open(final_p, 'wb') as d:
                                            shutil.copyfileobj(s, d)
                                processed_bytes += m.file_size
                                update_fn(processed_bytes, total_bytes, start_time, os.path.basename(m.filename))
                        os.remove(arch_path)
                    except Exception: pass

            elif move_info[0] == "move":
                _, src_p, dst_p, parent_folder = move_info
                in_info = {"size": os.path.getsize(src_p) if os.path.isfile(src_p) else 0, "time": "Move"}
                final_dst, status = resolve_collision_path(dst_p, in_info, conflict_state)
                if status == "write":
                    for attempt in range(4):
                        try:
                            shutil.move(src_p, final_dst)
                            break
                        except Exception:
                            time.sleep(0.15)
                processed_bytes += os.path.getsize(final_dst) if os.path.exists(final_dst) and os.path.isfile(final_dst) else 1024*1024
                update_fn(processed_bytes, total_bytes, start_time, os.path.basename(src_p))

                try:
                    if os.path.exists(parent_folder) and not os.listdir(parent_folder):
                        os.rmdir(parent_folder)
                except Exception:
                    pass

        update_fn(total_bytes, total_bytes, start_time, "Complete")

    app = ctk.CTk()
    app.withdraw()
    dlg = UniversalLiveProgressDialog(app, "Unpack Folder...", task)
    dlg.protocol("WM_DELETE_WINDOW", lambda: app.destroy())
    app.mainloop()


def run_live_unpack_all_folders_only(targets, destination_dir=None):
    """Unpack All (Flattens all subfolders to top-level, keeping all ZIP archives intact)."""
    if not targets: return

    conflict_state = ConflictState()

    def task(update_fn, is_cancelled_fn):
        start_time = time.time()

        for target in targets:
            if is_cancelled_fn(): break
            if not os.path.exists(target): continue
            target_abs = os.path.abspath(target)
            dest_dir = os.path.abspath(destination_dir) if destination_dir else (target_abs if os.path.isdir(target_abs) else os.path.dirname(target_abs))

            if os.path.isdir(target_abs):
                all_files = []
                for root, dirs, files in os.walk(target_abs):
                    for file in files:
                        all_files.append((os.path.join(root, file), file))

                total_b = sum(os.path.getsize(fp[0]) for fp in all_files if os.path.exists(fp[0])) or 1
                proc_b = 0

                for src_file, file_name in all_files:
                    if is_cancelled_fn(): break
                    dst_file = os.path.join(dest_dir, file_name)
                    if src_file != dst_file:
                        in_info = {"size": os.path.getsize(src_file) if os.path.isfile(src_file) else 0, "time": "Move"}
                        final_dst, status = resolve_collision_path(dst_file, in_info, conflict_state)
                        if status == "write":
                            for _ in range(4):
                                try:
                                    shutil.move(src_file, final_dst)
                                    break
                                except Exception:
                                    time.sleep(0.15)
                    proc_b += os.path.getsize(dst_file) if os.path.exists(dst_file) else 0
                    update_fn(proc_b, total_b, start_time, file_name)

                for root, dirs, files in os.walk(target_abs, topdown=False):
                    for d in dirs:
                        dp = os.path.join(root, d)
                        try:
                            if not os.listdir(dp): os.rmdir(dp)
                        except Exception: pass
                try:
                    if not os.listdir(target_abs): os.rmdir(target_abs)
                except Exception: pass

            elif os.path.isfile(target_abs):
                run_live_extract_folder(target_abs, dest_dir)
                try: os.remove(target_abs)
                except Exception: pass

    app = ctk.CTk()
    app.withdraw()
    dlg = UniversalLiveProgressDialog(app, "Unpack All Subfolders...", task)
    dlg.protocol("WM_DELETE_WINDOW", lambda: app.destroy())
    app.mainloop()


def run_live_unpack_and_extract_all_batch(targets, destination_dir=None):
    """Unpack & Extract All (Full Deep Clean: unzips all nested archives and flattens all folders)."""
    if not targets: return

    conflict_state = ConflictState()

    def task(update_fn, is_cancelled_fn):
        start_time = time.time()

        for target in targets:
            if is_cancelled_fn(): break
            if not os.path.exists(target): continue
            target_abs = os.path.abspath(target)
            dest_dir = os.path.abspath(destination_dir) if destination_dir else (target_abs if os.path.isdir(target_abs) else os.path.dirname(target_abs))

            if os.path.isdir(target_abs):
                for root, dirs, files in list(os.walk(target_abs)):
                    for f in files:
                        if is_cancelled_fn(): break
                        f_path = os.path.join(root, f)
                        ext = os.path.splitext(f)[1].lower()
                        if ext == ".zip":
                            try:
                                with zipfile.ZipFile(f_path, 'r') as zf:
                                    for m in zf.infolist():
                                        if not m.is_dir():
                                            out_p = os.path.join(root, m.filename)
                                            fp, st = resolve_collision_path(out_p, {"size": m.file_size, "time": str(m.date_time)}, conflict_state)
                                            if st == "write":
                                                os.makedirs(os.path.dirname(fp), exist_ok=True)
                                                with zf.open(m) as s, open(fp, 'wb') as d:
                                                    shutil.copyfileobj(s, d)
                                os.remove(f_path)
                            except Exception: pass
                        elif ext in [".7z", ".fz", ".fzip"] and HAS_PY7ZR:
                            try:
                                with py7zr.SevenZipFile(f_path, 'r') as szf:
                                    szf.extractall(path=root)
                                os.remove(f_path)
                            except Exception: pass

                all_files = []
                for root, dirs, files in os.walk(target_abs):
                    for file in files:
                        all_files.append((os.path.join(root, file), file))

                total_b = sum(os.path.getsize(fp[0]) for fp in all_files if os.path.exists(fp[0])) or 1
                proc_b = 0

                for src_file, file_name in all_files:
                    if is_cancelled_fn(): break
                    dst_file = os.path.join(dest_dir, file_name)
                    if src_file != dst_file:
                        in_info = {"size": os.path.getsize(src_file) if os.path.isfile(src_file) else 0, "time": "Deep Move"}
                        final_dst, status = resolve_collision_path(dst_file, in_info, conflict_state)
                        if status == "write":
                            for _ in range(4):
                                try:
                                    shutil.move(src_file, final_dst)
                                    break
                                except Exception:
                                    time.sleep(0.15)
                    proc_b += os.path.getsize(dst_file) if os.path.exists(dst_file) else 0
                    update_fn(proc_b, total_b, start_time, file_name)

                for root, dirs, files in os.walk(target_abs, topdown=False):
                    for d in dirs:
                        dp = os.path.join(root, d)
                        try:
                            if not os.listdir(dp): os.rmdir(dp)
                        except Exception: pass
                try:
                    if not os.listdir(target_abs): os.rmdir(target_abs)
                except Exception: pass

            elif os.path.isfile(target_abs):
                run_live_extract_folder(target_abs, dest_dir)
                try: os.remove(target_abs)
                except Exception: pass

    app = ctk.CTk()
    app.withdraw()
    dlg = UniversalLiveProgressDialog(app, "Unpack & Extract All...", task)
    dlg.protocol("WM_DELETE_WINDOW", lambda: app.destroy())
    app.mainloop()


# =============================================================================
# CLI INTERACTIVE HANDLERS & STANDALONE VAULT EXTRACTOR
# =============================================================================
def run_cli_open_vault(vault_path):
    """Directly unlocks and extracts .fzip vault files without opening the heavy app."""
    if not os.path.exists(vault_path): return

    app = ctk.CTk()
    app.withdraw()
    unlocked = [None]

    def on_pwd(path, pwd):
        unlocked[0] = pwd
        app.destroy()

    dialog = EncryptedArchiveDialog(app, vault_path, on_pwd)
    dialog.protocol("WM_DELETE_WINDOW", lambda: app.destroy())
    app.mainloop()

    if unlocked[0] is not None:
        target_dir = os.path.splitext(os.path.abspath(vault_path))[0]
        run_live_extract_folder(vault_path, target_dir, unlocked[0])


def run_cli_compress_interactive(targets, default_target_dir=None):
    """Prompts AddToArchiveDialog and then launches live compression."""
    if not targets: return

    app = ctk.CTk()
    app.withdraw()

    def on_confirm(archive_name, save_dir, password):
        app.destroy()
        run_live_compress(targets, archive_name, save_dir, password)

    dialog = AddToArchiveDialog(app, targets, default_target_dir, on_confirm)
    dialog.protocol("WM_DELETE_WINDOW", lambda: app.destroy())
    app.mainloop()


def run_cli_extract_interactive(archive_path, target_dir):
    """Interactive extraction with password check and live progress."""
    if not os.path.exists(archive_path): return

    password = None
    if check_archive_encrypted(archive_path):
        app = ctk.CTk()
        app.withdraw()
        unlocked = [None]

        def on_pwd(path, pwd):
            unlocked[0] = pwd
            app.destroy()

        dialog = EncryptedArchiveDialog(app, archive_path, on_pwd)
        dialog.protocol("WM_DELETE_WINDOW", lambda: app.destroy())
        app.mainloop()

        if unlocked[0] is None:
            return
        password = unlocked[0]

    run_live_extract_folder(archive_path, target_dir, password)


# =============================================================================
# SHELL REGISTRATION & FILE ASSOCIATION MODULE
# =============================================================================
def install_windows_shell_context_menu():
    """Registers right-click context menus and associates .fzip with vault_icon.ico."""
    if not HAS_WINREG:
        print("[!] Windows Registry module unavailable.")
        return

    # Use permanent program directory for registry icons
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
        cmd_prefix = f'"{sys.executable}"'
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        python_exe = sys.executable
        if python_exe.endswith("python.exe"):
            pythonw_exe = python_exe[:-10] + "pythonw.exe"
            if os.path.exists(pythonw_exe):
                python_exe = pythonw_exe
        script_path = os.path.abspath(__file__)
        cmd_prefix = f'"{python_exe}" "{script_path}"'

    icon_main   = os.path.join(app_dir, "icon.ico") if os.path.exists(os.path.join(app_dir, "icon.ico")) else r"%SystemRoot%\System32\shell32.dll,238"
    icon_unpack = os.path.join(app_dir, "unpack_icon.ico") if os.path.exists(os.path.join(app_dir, "unpack_icon.ico")) else icon_main
    icon_vault  = os.path.join(app_dir, "vault_icon.ico") if os.path.exists(os.path.join(app_dir, "vault_icon.ico")) else icon_main

    icon_zip        = r"%SystemRoot%\System32\zipfldr.dll,0"
    icon_folder_cls = r"%SystemRoot%\System32\imageres.dll,3"
    icon_folder_opn = r"%SystemRoot%\System32\imageres.dll,4"

    registry_targets = [
        r"Software\Classes\Directory\shell\FusionZip",
        r"Software\Classes\Directory\Background\shell\FusionZip",
        r"Software\Classes\*\shell\FusionZip"
    ]

    for target_key_path in registry_targets:
        for old_cmd in ["01_Compress", "02_ExtractFolder", "03_ExtractHere", "04_Unpack", "04_UnpackAll", "04b_UnpackExtractAll", "05_Open"]:
            try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{target_key_path}\\shell\\{old_cmd}\\command")
            except Exception: pass
            try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{target_key_path}\\shell\\{old_cmd}")
            except Exception: pass

    for target_key_path in registry_targets:
        try:
            parent_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, target_key_path)
            winreg.SetValueEx(parent_key, "MUIVerb", 0, winreg.REG_SZ, "Fusion Zip")
            winreg.SetValueEx(parent_key, "SubCommands", 0, winreg.REG_SZ, "")
            winreg.SetValueEx(parent_key, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
            winreg.SetValueEx(parent_key, "Icon", 0, winreg.REG_SZ, icon_main)

            sub_shell = winreg.CreateKey(parent_key, "shell")

            # 1. Compress
            k1 = winreg.CreateKey(sub_shell, "01_Compress")
            winreg.SetValueEx(k1, "MUIVerb", 0, winreg.REG_SZ, "Compress with Fusion Zip")
            winreg.SetValueEx(k1, "Icon", 0, winreg.REG_SZ, icon_zip)
            c1 = winreg.CreateKey(k1, "command")
            winreg.SetValue(c1, "", winreg.REG_SZ, f'{cmd_prefix} --compress "%1"')

            # 2. Extract to Folder
            k2 = winreg.CreateKey(sub_shell, "02_ExtractFolder")
            winreg.SetValueEx(k2, "MUIVerb", 0, winreg.REG_SZ, "Extract to Folder")
            winreg.SetValueEx(k2, "Icon", 0, winreg.REG_SZ, icon_folder_cls)
            c2 = winreg.CreateKey(k2, "command")
            winreg.SetValue(c2, "", winreg.REG_SZ, f'{cmd_prefix} --extract-folder "%1"')

            # 3. Extract Here
            k3 = winreg.CreateKey(sub_shell, "03_ExtractHere")
            winreg.SetValueEx(k3, "MUIVerb", 0, winreg.REG_SZ, "Extract Here")
            winreg.SetValueEx(k3, "Icon", 0, winreg.REG_SZ, icon_folder_opn)
            c3 = winreg.CreateKey(k3, "command")
            winreg.SetValue(c3, "", winreg.REG_SZ, f'{cmd_prefix} --extract-here "%1"')

            # 4. Unpack Folder (1-Level)
            k4 = winreg.CreateKey(sub_shell, "04_Unpack")
            winreg.SetValueEx(k4, "MUIVerb", 0, winreg.REG_SZ, "Unpack Folder")
            winreg.SetValueEx(k4, "Icon", 0, winreg.REG_SZ, icon_unpack)
            c4 = winreg.CreateKey(k4, "command")
            winreg.SetValue(c4, "", winreg.REG_SZ, f'{cmd_prefix} --unpack "%1"')

            # 5. Unpack All Subfolders (Keeps Zips Intact)
            k4b = winreg.CreateKey(sub_shell, "04_UnpackAll")
            winreg.SetValueEx(k4b, "MUIVerb", 0, winreg.REG_SZ, "Unpack All Subfolders")
            winreg.SetValueEx(k4b, "Icon", 0, winreg.REG_SZ, icon_unpack)
            c4b = winreg.CreateKey(k4b, "command")
            winreg.SetValue(c4b, "", winreg.REG_SZ, f'{cmd_prefix} --unpack-all "%1"')

            # 6. Unpack & Extract All (Deep Clean)
            k4c = winreg.CreateKey(sub_shell, "04b_UnpackExtractAll")
            winreg.SetValueEx(k4c, "MUIVerb", 0, winreg.REG_SZ, "Unpack && Extract All")
            winreg.SetValueEx(k4c, "Icon", 0, winreg.REG_SZ, icon_unpack)
            c4c = winreg.CreateKey(k4c, "command")
            winreg.SetValue(c4c, "", winreg.REG_SZ, f'{cmd_prefix} --unpack-extract-all "%1"')

            # 7. Open in Fusion Zip
            k5 = winreg.CreateKey(sub_shell, "05_Open")
            winreg.SetValueEx(k5, "MUIVerb", 0, winreg.REG_SZ, "Open in Fusion Zip")
            winreg.SetValueEx(k5, "Icon", 0, winreg.REG_SZ, icon_main)
            c5 = winreg.CreateKey(k5, "command")
            winreg.SetValue(c5, "", winreg.REG_SZ, f'{cmd_prefix} --gui "%1"')

        except Exception as e:
            print(f"[!] Registry warning: {e}")

    # Register .fzip File Association with custom vault_icon.ico
    try:
        fzip_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.fzip")
        winreg.SetValue(fzip_key, "", winreg.REG_SZ, "FusionZip.Vault")

        prog_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\FusionZip.Vault")
        winreg.SetValue(prog_key, "", winreg.REG_SZ, "Fusion Vault Archive")

        def_icon_key = winreg.CreateKey(prog_key, "DefaultIcon")
        winreg.SetValue(def_icon_key, "", winreg.REG_SZ, icon_vault)

        shell_open_key = winreg.CreateKey(prog_key, r"shell\open\command")
        winreg.SetValue(shell_open_key, "", winreg.REG_SZ, f'{cmd_prefix} --open-vault "%1"')
    except Exception as e:
        print(f"[!] .fzip Association warning: {e}")

    if sys.platform == "win32":
        shell32.SHChangeNotify(0x08000000, 0, None, None)

    print("[✓] Context menus & .fzip vault file icons registered successfully!")


def uninstall_windows_shell_context_menu():
    """Wipes Fusion Zip keys and .fzip associations from the Windows Registry."""
    if not HAS_WINREG: return
    registry_targets = [
        r"Software\Classes\Directory\shell\FusionZip",
        r"Software\Classes\Directory\Background\shell\FusionZip",
        r"Software\Classes\*\shell\FusionZip",
        r"Software\Classes\.fzip",
        r"Software\Classes\FusionZip.Vault"
    ]
    for target_key_path in registry_targets:
        for old_cmd in ["01_Compress", "02_ExtractFolder", "03_ExtractHere", "04_Unpack", "04_UnpackAll", "04b_UnpackExtractAll", "05_Open"]:
            try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{target_key_path}\\shell\\{old_cmd}\\command")
            except Exception: pass
            try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{target_key_path}\\shell\\{old_cmd}")
            except Exception: pass
        try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{target_key_path}\\shell")
        except Exception: pass
        try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER, target_key_path)
        except Exception: pass
    if sys.platform == "win32":
        shell32.SHChangeNotify(0x08000000, 0, None, None)
    print("[✓] Context menus & associations removed from Registry.")


def try_send_ipc_gui(args):
    """Sends paths to running Fusion Zip window via local socket."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.05)
        s.connect(('127.0.0.1', IPC_PORT))
        s.sendall(json.dumps(args).encode('utf-8'))
        s.close()
        return True
    except Exception:
        return False


def start_ipc_server_thread(app):
    """Listens for new multi-select files and appends them to the running window queue."""
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
# MAIN ENTRY POINT
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
        elif flag == "--open-vault" and args:
            run_cli_open_vault(args[0])
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
            run_live_unpack_folder_batch(args)
            sys.exit(0)
        elif flag == "--unpack-to" and len(args) >= 2:
            target_dir = args[0]
            archive_paths = args[1:]
            run_live_unpack_folder_batch(archive_paths, destination_dir=target_dir)
            sys.exit(0)
        elif flag == "--unpack-all" and args:
            run_live_unpack_all_folders_only(args)
            sys.exit(0)
        elif flag == "--unpack-all-to" and len(args) >= 2:
            target_dir = args[0]
            archive_paths = args[1:]
            run_live_unpack_all_folders_only(archive_paths, destination_dir=target_dir)
            sys.exit(0)
        elif flag == "--unpack-extract-all" and args:
            run_live_unpack_and_extract_all_batch(args)
            sys.exit(0)
        elif flag == "--unpack-extract-all-to" and len(args) >= 2:
            target_dir = args[0]
            archive_paths = args[1:]
            run_live_unpack_and_extract_all_batch(archive_paths, destination_dir=target_dir)
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