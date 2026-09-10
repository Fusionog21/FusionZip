# 🗜️ Fusion Zip v2.0 — Windows 11 Fluent Edition

**Fusion Zip** is a modern, dark-themed Windows archive manager and custom C++ COM shell extension engine built with Python (CustomTkinter) and C++ (Win32 API). 

It features native Windows 11 context menus, 7-Zip style right-click drag-and-drop actions, real-time chunked progress tracking, AES-256 vault encryption with custom file branding, smart password detection, safe conflict resolution, and automated installer packaging.

---

## ✨ Features

- **🎨 Windows 11 Fluent Dark UI:** Clean, deep-slate canvas matching modern File Explorer with native system icons (yellow folders, zipper archives, and registered application badges).
- **🔒 AES-256 Vault Encryption (`.fzip`):** Strong WinZip AES-256 and 7z header encryption. Files are branded with a custom vault icon and can be opened or extracted with one click.
- **🖱️ Native C++ Shell Extension:** Right-click and right-click drag-and-drop context menus with transparent 32-bit icons.
- **📦 3-Tier Unpacking Engine:**
  - ⚡ **Unpack Folder:** 1-level move up to parent directory.
  - 📂 **Unpack All Subfolders:** Recursively flattens subdirectories to the top level while **keeping `.zip` archives intact**.
  - 🧹 **Unpack & Extract All:** Full deep clean that recursively flattens subfolders **and** unzips all nested archives.
- **⚠️ 7-Zip Style Conflict Resolution:** Generous 520x370 inspection card showing exact file sizes (down to the byte), modification timestamps, and smart tags (`[ Larger ]`, `[ Smaller ]`). Safe non-destructive merging.
- **⚡ High-Speed Chunked Streaming:** 8MB buffer streams multi-gigabyte ISOs and ROMs smoothly without freezing or locking the progress bar.
- **🚫 Zero Ghost Folders:** Destination folders are created *only* after passwords are verified and conflict prompts are answered.

---

## 📁 Project Structure

```text
├── fusion_zip.py          # Master Python GUI, CLI engine & live progress worker
├── FusionZipShell.cpp     # C++ COM Shell Extension for Right-Click Drag-and-Drop
├── FusionZipShell.dll     # Compiled 64-bit COM Shell Extension DLL
├── setup_script.iss       # Inno Setup 64-bit installer packaging script
├── icon.ico               # Main application & parent context menu icon
├── unpack_icon.ico        # Custom wrench & crate unpack actions icon
├── vault_icon.ico         # Custom white document "F" vault file icon
├── requirements.txt       # Python dependencies
├── README.md              # Project documentation
└── LICENSE.txt            # Open-source license