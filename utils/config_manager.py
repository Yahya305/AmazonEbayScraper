import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox

CONFIG_FILE = "config.json"


def get_config_path():
    """Return the absolute path of the config.json file."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE)


def load_config():
    """Load existing configuration from file, if available."""
    config_path = get_config_path()
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}


def save_config(config):
    """Save configuration dictionary to file."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)


def setup_chromium_path():
    """
    Open a window to let the user select the Chromium executable.
    Saves the selected path into config.json.
    """
    root = tk.Tk()
    root.withdraw()

    messagebox.showinfo("Setup", "Please select the Chromium executable file (chrome.exe or chromium.exe).")

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
    If not found, trigger setup.
    """
    config = load_config()
    path = config.get("chromium_path")

    if not path or not os.path.exists(path):
        return setup_chromium_path()

    return path
