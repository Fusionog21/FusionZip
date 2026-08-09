# Fusion Zip 🗜️

**Fusion Zip** is a modern, dark-themed, ultra-fast Windows desktop archive manager and custom shell engine. Built for power users and casual compression needs alike, Fusion Zip seamlessly integrates into Windows Explorer with native context menus, smart password detection, deep folder cleanup, and real-time progress tracking.

---

## ✨ Key Features

### ⚡ **1. Native Windows Shell Integration (7-Zip Style)**
* **Right-Click Drag-and-Drop Menu:** Right-click and drag any file, archive, or folder anywhere in Windows Explorer to reveal the **Fusion Zip >** submenu.
* **Native System DLL Icons:** Context menu entries display authentic Windows icons (`zipfldr.dll`, `shell32.dll`, `imageres.dll`) matching native Explorer aesthetics.
* **True Drop-Target Extraction:** Dropping items onto open File Explorer windows, Desktop, or folder icons extracts or unpacks files directly into the target drop folder.

### 📦 **2. Fusion Unpack & Fusion Unpack All**
* **Fusion Unpack (1-Level Move):** Empties a folder or archive directly into the drop destination and automatically deletes the empty container folder or archive file.
* **Fusion Unpack All (Deep Cleanup):** Recursively digs through nested sub-folders and hidden zip archives, pulls every file up to the top destination level, and vaporizes empty leftover directories.

### 🔒 **3. Smart Password Protection & AES-256 Vault**
* **Smart Detection:** Normal unencrypted zips and regular folders extract/unpack instantly without prompting for a password.
* **AES-256 Header Encryption:** Password-protected archives (`.fzip` / `.7z`) lock both file contents and file names with 256-bit AES encryption.
* **Dark Password Modal:** Encrypted archives pop up a dark-mode password window featuring the app logo in the title bar.

### 🔄 **4. Interactive File Name Collision Resolution**
* **Item Already Exists Interceptor:** When extracting or moving files to a location with matching names, Fusion Zip pauses and prompts you with:
  * 🔄 **Replace:** Overwrites existing items.
  * 📋 **Keep Both:** Safely renames containing folders or files (e.g., `Folder_1`), leaving internal executable filenames (`App.exe`) untouched.
  * ⏭️ **Skip:** Leaves existing items untouched.
  * ☑️ **Apply to all remaining conflicts:** Applies choice to the entire batch.

### 📊 **5. Live Compression Progress & Auto-Closing Window**
* **Blazing Fast Compression:** Uses Level-1 DEFLATE fast compression for up to **10x faster zipping**.
* **Live Progress Bar:** Displays real-time MB processed, speed (MB/s), and estimated time remaining.
* **Clean Auto-Close:** The progress window automatically closes as soon as compression hits 100%—zero extra clicks required!
* **Multi-File Bundling:** Compressing multiple selected loose files automatically packages them into **ONE single `.zip` archive**.

### 🖥️ **6. Modern Dark UI Desktop Application**
* **CustomTkinter Engine:** Sleek dark navy interface with hover tooltips, staging queue grid, location tracking, and double-click archive/folder inspection.
* **Single-Instance Multi-Select:** Right-clicking multiple files opens **one single window** and queues all items into the grid.
* **Titlebar & Taskbar Logo:** Native `AppUserModelID` binding displays your custom logo on the taskbar and title bar of all windows.

---

## 🚀 How to Install

### **Option 1: Quick Installer (Recommended)**
1. Go to the **Releases** tab on the right side of this repository page.
2. Download **`FusionZip_Setup.exe`**.
3. Double-click **`FusionZip_Setup.exe`** and complete the quick installation wizard.

### **Option 2: Build from Source**
1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/FusionZip.git
   cd FusionZip