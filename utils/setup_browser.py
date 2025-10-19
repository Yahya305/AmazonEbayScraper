import os
from tkinter import Tk, filedialog, messagebox
from .config_manager import load_config, save_config
import glob

def find_playwright_chromium():
    """
    Try to automatically find the Chromium binary installed by Playwright.
    """
    base_path = os.path.join(os.getenv("USERPROFILE") or "", "AppData", "Local", "ms-playwright")
    if not os.path.exists(base_path):
        return None

    # Search for chrome.exe inside ms-playwright folders
    pattern = os.path.join(base_path, "chromium-*", "chrome-win", "chrome.exe")
    matches = glob.glob(pattern)
    if matches:
        return matches[0]
    return None


def get_chromium_path():
    """
    Ensures a valid Chromium path exists.  
    - Checks config.json first  
    - Tries auto-detect  
    - Prompts user if not found
    """
    config = load_config()
    chromium_path = config.get("chromium_path")

    # If path is saved and valid
    if chromium_path and os.path.exists(chromium_path):
        return chromium_path

    # Try auto-detecting Playwright Chromium
    auto_path = find_playwright_chromium()
    if auto_path:
        save_config({"chromium_path": auto_path})
        print(f"✅ Found Playwright Chromium at: {auto_path}")
        return auto_path

    # Ask user manually if not found
    Tk().withdraw()  # hide main window
    messagebox.showinfo("Chromium Setup", "Please select your Chromium or Chrome executable file.")
    chromium_path = filedialog.askopenfilename(
        title="Select Chromium/Chrome Executable",
        filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
    )

    if not chromium_path:
        messagebox.showerror("Error", "No Chromium path selected. Exiting.")
        raise FileNotFoundError("Chromium executable not selected")

    # Save for future use
    save_config({"chromium_path": chromium_path})
    messagebox.showinfo("Saved", f"Chromium path saved: {chromium_path}")

    return chromium_path
