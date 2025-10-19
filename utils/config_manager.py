import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox

# ✅ Persistent config folder inside user's home directory
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".ebay_scraper")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def ensure_config_dir():
    """Ensure config directory exists."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config():
    """Load existing configuration from persistent config file, if available."""
    ensure_config_dir()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_config(config):
    """Save configuration dictionary to persistent file."""
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def setup_chromium_path():
    """
    Open a window to let the user select the Chromium executable.
    Saves the selected path into config.json (in ~/.ebay_scraper).
    """
    root = tk.Tk()
    root.withdraw()

    messagebox.showinfo(
        "Setup",
        "Please select the Chromium executable file (chrome.exe or chromium.exe)."
    )

    chromium_path = filedialog.askopenfilename(
        title="Select Chromium executable",
        filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
    )

    if not chromium_path:
        messagebox.showwarning("Setup Cancelled", "No file selected. Setup aborted.")
        return None

    config = load_config()
    config["chromium_path"] = chromium_path
    save_config(config)

    messagebox.showinfo("Setup Complete", f"Chromium path saved:\n{chromium_path}")
    return chromium_path


def get_chromium_path():
    """
    Retrieve Chromium path from config.
    If not found or invalid, trigger setup window.
    """
    config = load_config()
    path = config.get("chromium_path")

    if not path or not os.path.exists(path):
        return setup_chromium_path()

    return path
