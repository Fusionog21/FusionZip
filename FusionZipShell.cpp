#include <windows.h>
#include <shlobj.h>
#include <shlwapi.h>
#include <strsafe.h>
#include <vector>
#include <string>

#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "shlwapi.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")

static const GUID CLSID_FusionZipShell = 
{ 0x8F3E9C1D, 0x4B2A, 0x4E7F, { 0x9C, 0x12, 0x3D, 0x5E, 0x7A, 0x8B, 0x9C, 0x0D } };

static LONG g_cRefModule = 0;
static HINSTANCE g_hInst = NULL;

static HBITMAP IconToBitmapPARGB32(HICON hIcon)
{
    if (!hIcon) return NULL;

    ICONINFO ii = {0};
    if (!GetIconInfo(hIcon, &ii)) return NULL;

    HDC hdcScreen = GetDC(NULL);
    HDC hdcMem = CreateCompatibleDC(hdcScreen);

    BITMAPINFO bi = {0};
    bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bi.bmiHeader.biWidth = 16;
    bi.bmiHeader.biHeight = -16;
    bi.bmiHeader.biPlanes = 1;
    bi.bmiHeader.biBitCount = 32;
    bi.bmiHeader.biCompression = BI_RGB;

    void* pBits = NULL;
    HBITMAP hBmp = CreateDIBSection(hdcMem, &bi, DIB_RGB_COLORS, &pBits, NULL, 0);
    if (!hBmp)
    {
        DeleteDC(hdcMem);
        ReleaseDC(NULL, hdcScreen);
        if (ii.hbmColor) DeleteObject(ii.hbmColor);
        if (ii.hbmMask) DeleteObject(ii.hbmMask);
        DestroyIcon(hIcon);
        return NULL;
    }

    HBITMAP hBmpOld = (HBITMAP)SelectObject(hdcMem, hBmp);

    ZeroMemory(pBits, 16 * 16 * 4);

    DrawIconEx(hdcMem, 0, 0, hIcon, 16, 16, 0, NULL, DI_NORMAL);

    DWORD* pPixels = (DWORD*)pBits;
    bool hasAlpha = false;
    for (int i = 0; i < 16 * 16; ++i)
    {
        if ((pPixels[i] & 0xFF000000) != 0)
        {
            hasAlpha = true;
            break;
        }
    }

    if (!hasAlpha && ii.hbmMask)
    {
        HDC hdcMask = CreateCompatibleDC(hdcScreen);
        HBITMAP hbmMaskOld = (HBITMAP)SelectObject(hdcMask, ii.hbmMask);
        for (int y = 0; y < 16; ++y)
        {
            for (int x = 0; x < 16; ++x)
            {
                COLORREF maskCol = GetPixel(hdcMask, x, y);
                int idx = y * 16 + x;
                if (maskCol == RGB(0, 0, 0))
                {
                    pPixels[idx] |= 0xFF000000;
                }
                else
                {
                    pPixels[idx] = 0x00000000;
                }
            }
        }
        SelectObject(hdcMask, hbmMaskOld);
        DeleteDC(hdcMask);
    }

    SelectObject(hdcMem, hBmpOld);
    DeleteDC(hdcMem);
    ReleaseDC(NULL, hdcScreen);

    if (ii.hbmColor) DeleteObject(ii.hbmColor);
    if (ii.hbmMask) DeleteObject(ii.hbmMask);
    DestroyIcon(hIcon);

    return hBmp;
}

static HBITMAP GetSystemIconBitmap(LPCWSTR szDllPath, int iconIndex)
{
    HICON hIcon = NULL;
    ExtractIconExW(szDllPath, iconIndex, NULL, &hIcon, 1);
    if (!hIcon)
    {
        ExtractIconExW(L"shell32.dll", 3, NULL, &hIcon, 1);
    }
    return IconToBitmapPARGB32(hIcon);
}

static HBITMAP GetCustomIconBitmap(LPCWSTR szIcoFilename)
{
    wchar_t szDllPath[MAX_PATH];
    GetModuleFileNameW(g_hInst, szDllPath, MAX_PATH);
    PathRemoveFileSpecW(szDllPath);

    wchar_t szIcoPath[MAX_PATH];
    PathCombineW(szIcoPath, szDllPath, szIcoFilename);

    HICON hIcon = (HICON)LoadImageW(NULL, szIcoPath, IMAGE_ICON, 16, 16, LR_LOADFROMFILE);
    if (!hIcon)
    {
        return GetSystemIconBitmap(L"imageres.dll", 238);
    }
    return IconToBitmapPARGB32(hIcon);
}

class FusionZipShell : public IShellExtInit, public IContextMenu
{
private:
    LONG m_cRef;
    std::vector<std::wstring> m_selectedFiles;
    wchar_t m_szDropTargetFolder[MAX_PATH];

public:
    FusionZipShell() : m_cRef(1)
    {
        InterlockedIncrement(&g_cRefModule);
        m_szDropTargetFolder[0] = L'\0';
    }

    ~FusionZipShell()
    {
        InterlockedDecrement(&g_cRefModule);
    }

    IFACEMETHODIMP QueryInterface(REFIID riid, void **ppv)
    {
        static const QITAB qit[] = {
            QITABENT(FusionZipShell, IShellExtInit),
            QITABENT(FusionZipShell, IContextMenu),
            { 0 },
        };
        return QISearch(this, qit, riid, ppv);
    }

    IFACEMETHODIMP_(ULONG) AddRef() { return InterlockedIncrement(&m_cRef); }
    IFACEMETHODIMP_(ULONG) Release()
    {
        ULONG cRef = InterlockedDecrement(&m_cRef);
        if (cRef == 0) delete this;
        return cRef;
    }

    IFACEMETHODIMP Initialize(LPCITEMIDLIST pidlFolder, IDataObject *pdtobj, HKEY hkeyProgID)
    {
        m_selectedFiles.clear();
        m_szDropTargetFolder[0] = L'\0';

        if (pidlFolder)
        {
            SHGetPathFromIDListW(pidlFolder, m_szDropTargetFolder);
        }

        if (!pdtobj) return E_INVALIDARG;

        FORMATETC fmt = { CF_HDROP, NULL, DVASPECT_CONTENT, -1, TYMED_HGLOBAL };
        STGMEDIUM stg;

        if (SUCCEEDED(pdtobj->GetData(&fmt, &stg)))
        {
            HDROP hDrop = (HDROP)GlobalLock(stg.hGlobal);
            if (hDrop)
            {
                UINT uNumFiles = DragQueryFileW(hDrop, 0xFFFFFFFF, NULL, 0);
                for (UINT i = 0; i < uNumFiles; i++)
                {
                    wchar_t szPath[MAX_PATH];
                    if (DragQueryFileW(hDrop, i, szPath, MAX_PATH))
                    {
                        m_selectedFiles.push_back(szPath);
                    }
                }
                GlobalUnlock(stg.hGlobal);
            }
            ReleaseStgMedium(&stg);
        }
        return m_selectedFiles.empty() ? E_FAIL : S_OK;
    }

    IFACEMETHODIMP QueryContextMenu(HMENU hMenu, UINT indexMenu, UINT idCmdFirst, UINT idCmdLast, UINT uFlags)
    {
        HMENU hSubMenu = CreatePopupMenu();
        if (!hSubMenu) return E_FAIL;

        HBITMAP hBmpMain    = GetCustomIconBitmap(L"icon.ico");
        HBITMAP hBmpZip     = GetSystemIconBitmap(L"zipfldr.dll", 0);
        HBITMAP hBmpFoldCls = GetSystemIconBitmap(L"imageres.dll", 3);
        HBITMAP hBmpFoldOpn = GetSystemIconBitmap(L"imageres.dll", 4);
        HBITMAP hBmpUnpack  = GetCustomIconBitmap(L"unpack_icon.ico");

        UINT idCmd = idCmdFirst;

        struct MenuItemData {
            LPCWSTR text;
            HBITMAP hbmp;
        } items[] = {
            { L"Compress with Fusion Zip", hBmpZip },
            { L"Extract to Folder", hBmpFoldCls },
            { L"Extract Here", hBmpFoldOpn },
            { L"Unpack Folder", hBmpUnpack },
            { L"Unpack All Subfolders", hBmpUnpack },
            { L"Unpack && Extract All", hBmpUnpack },
            { L"Open in Fusion Zip", hBmpMain }
        };

        for (int i = 0; i < 7; i++)
        {
            MENUITEMINFOW miiSub = { sizeof(miiSub) };
            miiSub.fMask = MIIM_STRING | MIIM_ID | (items[i].hbmp ? MIIM_BITMAP : 0);
            miiSub.wID = idCmd++;
            miiSub.dwTypeData = (LPWSTR)items[i].text;
            miiSub.hbmpItem = items[i].hbmp;
            InsertMenuItemW(hSubMenu, i, TRUE, &miiSub);
        }

        MENUITEMINFOW mii = { sizeof(mii) };
        mii.fMask = MIIM_SUBMENU | MIIM_STRING | MIIM_ID | (hBmpMain ? MIIM_BITMAP : 0);
        mii.wID = idCmdFirst;
        mii.hSubMenu = hSubMenu;
        mii.dwTypeData = (LPWSTR)L"Fusion Zip";
        mii.hbmpItem = hBmpMain;

        InsertMenuItemW(hMenu, indexMenu, TRUE, &mii);

        return MAKE_HRESULT(SEVERITY_SUCCESS, 0, (idCmd - idCmdFirst));
    }

    IFACEMETHODIMP InvokeCommand(LPCMINVOKECOMMANDINFO pici)
    {
        if (HIWORD(pici->lpVerb) != 0) return E_INVALIDARG;

        UINT id = LOWORD(pici->lpVerb);
        if (m_selectedFiles.empty()) return E_FAIL;

        wchar_t szDllPath[MAX_PATH];
        GetModuleFileNameW(g_hInst, szDllPath, MAX_PATH);
        PathRemoveFileSpecW(szDllPath);

        wchar_t szExePath[MAX_PATH];
        PathCombineW(szExePath, szDllPath, L"FusionZip.exe");

        std::wstring szCmd;
        if (PathFileExistsW(szExePath))
        {
            szCmd = L"\"" + std::wstring(szExePath) + L"\" ";
        }
        else
        {
            wchar_t szPywPath[MAX_PATH];
            PathCombineW(szPywPath, szDllPath, L"venv\\Scripts\\pythonw.exe");
            if (!PathFileExistsW(szPywPath))
            {
                PathCombineW(szPywPath, szDllPath, L"venv\\Scripts\\python.exe");
            }
            wchar_t szScriptPath[MAX_PATH];
            PathCombineW(szScriptPath, szDllPath, L"fusion_zip.py");

            if (PathFileExistsW(szPywPath))
            {
                szCmd = L"\"" + std::wstring(szPywPath) + L"\" \"" + std::wstring(szScriptPath) + L"\" ";
            }
            else
            {
                szCmd = L"pythonw.exe \"" + std::wstring(szScriptPath) + L"\" ";
            }
        }

        bool hasDropTarget = (m_szDropTargetFolder[0] != L'\0');

        switch (id)
        {
            case 0:
                if (hasDropTarget)
                    szCmd += L"--compress-to \"" + std::wstring(m_szDropTargetFolder) + L"\"";
                else
                    szCmd += L"--compress";
                break;
            case 1:
                if (hasDropTarget)
                    szCmd += L"--extract-folder-to \"" + std::wstring(m_szDropTargetFolder) + L"\"";
                else
                    szCmd += L"--extract-folder";
                break;
            case 2:
                if (hasDropTarget)
                    szCmd += L"--extract-to \"" + std::wstring(m_szDropTargetFolder) + L"\"";
                else
                    szCmd += L"--extract-here";
                break;
            case 3:
                if (hasDropTarget)
                    szCmd += L"--unpack-to \"" + std::wstring(m_szDropTargetFolder) + L"\"";
                else
                    szCmd += L"--unpack";
                break;
            case 4:
                if (hasDropTarget)
                    szCmd += L"--unpack-all-to \"" + std::wstring(m_szDropTargetFolder) + L"\"";
                else
                    szCmd += L"--unpack-all";
                break;
            case 5:
                if (hasDropTarget)
                    szCmd += L"--unpack-extract-all-to \"" + std::wstring(m_szDropTargetFolder) + L"\"";
                else
                    szCmd += L"--unpack-extract-all";
                break;
            case 6:
                szCmd += L"--gui";
                break;
            default:
                return E_INVALIDARG;
        }

        for (const auto& file : m_selectedFiles)
        {
            szCmd += L" \"" + file + L"\"";
        }

        STARTUPINFOW si = { sizeof(si) };
        PROCESS_INFORMATION pi;
        if (CreateProcessW(NULL, (LPWSTR)szCmd.c_str(), NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi))
        {
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
        }
        return S_OK;
    }

    IFACEMETHODIMP GetCommandString(UINT_PTR idCmd, UINT uType, UINT *pReserved, LPSTR pszName, UINT cchMax)
    {
        return E_NOTIMPL;
    }
};

class ClassFactory : public IClassFactory
{
private:
    LONG m_cRef;

public:
    ClassFactory() : m_cRef(1) {}

    IFACEMETHODIMP QueryInterface(REFIID riid, void **ppv)
    {
        static const QITAB qit[] = {
            QITABENT(ClassFactory, IClassFactory),
            { 0 },
        };
        return QISearch(this, qit, riid, ppv);
    }

    IFACEMETHODIMP_(ULONG) AddRef() { return InterlockedIncrement(&m_cRef); }
    IFACEMETHODIMP_(ULONG) Release()
    {
        ULONG cRef = InterlockedDecrement(&m_cRef);
        if (cRef == 0) delete this;
        return cRef;
    }

    IFACEMETHODIMP CreateInstance(IUnknown *pUnkOuter, REFIID riid, void **ppv)
    {
        if (pUnkOuter) return CLASS_E_NOAGGREGATION;
        FusionZipShell *pExt = new FusionZipShell();
        if (!pExt) return E_OUTOFMEMORY;
        HRESULT hr = pExt->QueryInterface(riid, ppv);
        pExt->Release();
        return hr;
    }

    IFACEMETHODIMP LockServer(BOOL fLock)
    {
        if (fLock) InterlockedIncrement(&g_cRefModule);
        else InterlockedDecrement(&g_cRefModule);
        return S_OK;
    }
};

STDAPI DllGetClassObject(REFCLSID rclsid, REFIID riid, void **ppv)
{
    if (IsEqualCLSID(rclsid, CLSID_FusionZipShell))
    {
        ClassFactory *pFactory = new ClassFactory();
        if (!pFactory) return E_OUTOFMEMORY;
        HRESULT hr = pFactory->QueryInterface(riid, ppv);
        pFactory->Release();
        return hr;
    }
    return CLASS_E_CLASSNOTAVAILABLE;
}

STDAPI DllCanUnloadNow()
{
    return g_cRefModule == 0 ? S_OK : S_FALSE;
}

STDAPI DllRegisterServer()
{
    wchar_t szModule[MAX_PATH];
    GetModuleFileNameW(g_hInst, szModule, MAX_PATH);

    const wchar_t* clsidStr = L"{8F3E9C1D-4B2A-4E7F-9C12-3D5E7A8B9C0D}";
    wchar_t szKey[256];

    StringCchPrintfW(szKey, ARRAYSIZE(szKey), L"CLSID\\%s", clsidStr);
    HKEY hKey;
    RegCreateKeyExW(HKEY_CLASSES_ROOT, szKey, 0, NULL, 0, KEY_WRITE, NULL, &hKey, NULL);
    RegSetValueExW(hKey, NULL, 0, REG_SZ, (BYTE*)L"FusionZipShell", sizeof(L"FusionZipShell"));
    RegCloseKey(hKey);

    StringCchPrintfW(szKey, ARRAYSIZE(szKey), L"CLSID\\%s\\InprocServer32", clsidStr);
    RegCreateKeyExW(HKEY_CLASSES_ROOT, szKey, 0, NULL, 0, KEY_WRITE, NULL, &hKey, NULL);
    RegSetValueExW(hKey, NULL, 0, REG_SZ, (BYTE*)szModule, (lstrlenW(szModule) + 1) * sizeof(wchar_t));
    RegSetValueExW(hKey, L"ThreadingModel", 0, REG_SZ, (BYTE*)L"Apartment", sizeof(L"Apartment"));
    RegCloseKey(hKey);

    HKEY hKeyApproved;
    if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Shell Extensions\\Approved", 0, KEY_WRITE, &hKeyApproved) == ERROR_SUCCESS)
    {
        RegSetValueExW(hKeyApproved, clsidStr, 0, REG_SZ, (BYTE*)L"FusionZipShell", sizeof(L"FusionZipShell"));
        RegCloseKey(hKeyApproved);
    }

    const wchar_t* targets[] = {
        L"*\\shellex\\DragDropHandlers\\FusionZip",
        L"Directory\\shellex\\DragDropHandlers\\FusionZip",
        L"Directory\\Background\\shellex\\DragDropHandlers\\FusionZip",
        L"Folder\\shellex\\DragDropHandlers\\FusionZip"
    };

    for (const auto& target : targets)
    {
        RegCreateKeyExW(HKEY_CLASSES_ROOT, target, 0, NULL, 0, KEY_WRITE, NULL, &hKey, NULL);
        RegSetValueExW(hKey, NULL, 0, REG_SZ, (BYTE*)clsidStr, (lstrlenW(clsidStr) + 1) * sizeof(wchar_t));
        RegCloseKey(hKey);
    }

    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);
    return S_OK;
}

STDAPI DllUnregisterServer()
{
    const wchar_t* clsidStr = L"{8F3E9C1D-4B2A-4E7F-9C12-3D5E7A8B9C0D}";
    wchar_t szKey[256];

    StringCchPrintfW(szKey, ARRAYSIZE(szKey), L"CLSID\\%s\\InprocServer32", clsidStr);
    RegDeleteKeyW(HKEY_CLASSES_ROOT, szKey);
    StringCchPrintfW(szKey, ARRAYSIZE(szKey), L"CLSID\\%s", clsidStr);
    RegDeleteKeyW(HKEY_CLASSES_ROOT, szKey);

    RegDeleteKeyW(HKEY_CLASSES_ROOT, L"*\\shellex\\DragDropHandlers\\FusionZip");
    RegDeleteKeyW(HKEY_CLASSES_ROOT, L"Directory\\shellex\\DragDropHandlers\\FusionZip");
    RegDeleteKeyW(HKEY_CLASSES_ROOT, L"Directory\\Background\\shellex\\DragDropHandlers\\FusionZip");
    RegDeleteKeyW(HKEY_CLASSES_ROOT, L"Folder\\shellex\\DragDropHandlers\\FusionZip");

    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);
    return S_OK;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved)
{
    if (ul_reason_for_call == DLL_PROCESS_ATTACH)
    {
        g_hInst = hModule;
        DisableThreadLibraryCalls(hModule);
    }
    return TRUE;
}