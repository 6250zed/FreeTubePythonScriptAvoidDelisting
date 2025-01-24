import os
import shutil
import time
import subprocess
import pyautogui
import logging
import argparse
import random
from PIL import Image
import pytesseract

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def clear_cache(cache_dir):
    """Clears the specified cache directory."""
    if os.path.exists(cache_dir):
        try:
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir)
            logging.info("Cache cleared.")
        except Exception as e:
            logging.error(f"Error clearing cache: {e}")
    else:
        logging.warning(f"Cache directory {cache_dir} does not exist.")

def get_focused_window():
    """Returns the title of the currently focused window."""
    try:
        result = subprocess.run(["xdotool", "getwindowfocus", "getwindowname"], stdout=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logging.error("Failed to retrieve focused window.")
            return None
        focused_window = result.stdout.strip()
        logging.debug(f"Focused window: {focused_window}")
        return focused_window
    except Exception as e:
        logging.error(f"Unable to get focused window: {e}")
        return None

def is_target_window(focused_window, app_name):
    """Checks if the focused window belongs to the target application."""
    is_focused = focused_window and app_name.lower() in focused_window.lower()
    logging.debug(f"Is {app_name} window focused: {is_focused}")
    return is_focused

def is_youtube_tcp_session_active():
    """Checks for active TCP sessions to youtube.com."""
    try:
        result = subprocess.run(
            ["lsof", "-i", "@youtube.com"], stdout=subprocess.PIPE, text=True
        )
        active = bool(result.stdout.strip())
        logging.debug(f"Active TCP session to youtube.com: {active}")
        return active
    except Exception as e:
        logging.error(f"Error checking for active TCP sessions: {e}")
        return False

def refresh_application():
    """Simulates Ctrl+Shift+R to refresh the application using pyautogui."""
    try:
        pyautogui.hotkey('ctrl', 'shift', 'r')
        logging.info("Application refreshed.")
    except Exception as e:
        logging.error(f"Failed to refresh application: {e}")

def get_toast_messages():
    """Extracts text from the FreeTube application for toast messages."""
    try:
        screenshot = pyautogui.screenshot()
        text = pytesseract.image_to_string(screenshot)  # Perform OCR
        logging.debug(f"Extracted text: {text}")
        return text
    except Exception as e:
        logging.error(f"Error capturing toast messages: {e}")
        return ""

def change_vpn_server(last_connected):
    """Changes the VPN connection to a random US-FL server without repeating the last one."""
    try:
        server_range = list(range(1, 219))
        server_range.remove(last_connected)  # Exclude the last connected server
        new_server = random.choice(server_range)
        server_name = f"US-FL#{new_server}"

        # Disconnect the current VPN session
        subprocess.run(["protonvpn-app", "disconnect"], check=True)
        time.sleep(2)  # Wait before reconnecting

        # Connect to the new server
        subprocess.run(["protonvpn-app", "connect", server_name], check=True)
        logging.info(f"VPN connected to {server_name}.")
        return new_server
    except Exception as e:
        logging.error(f"Failed to change VPN server: {e}")
        return last_connected

def monitor_toast_messages(last_connected):
    """Monitors toast messages for specific keywords and changes VPN server if needed."""
    toast_text = get_toast_messages().lower()
    if "block" in toast_text or "legacy" in toast_text:
        logging.info("Detected toast message with keywords 'block' or 'legacy'. Changing VPN server...")
        return change_vpn_server(last_connected)
    return last_connected

def refresh_periodically(cache_dir, app_name, interval):
    """Refreshes the target application and clears its cache periodically."""
    last_connected = 0  # Keep track of the last connected VPN server
    while True:
        logging.info("Clearing cache...")
        clear_cache(cache_dir)
        time.sleep(4)  # Allow cache to clear before refreshing

        # Monitor toast messages and update VPN server if needed
        last_connected = monitor_toast_messages(last_connected)

        # Check if the target application is the focused window
        focused_window = get_focused_window()
        if is_target_window(focused_window, app_name):
            logging.info(f"{app_name} is focused.")
            if not is_youtube_tcp_session_active():
                logging.info("No active TCP session to youtube.com detected. Refreshing application...")
                refresh_application()
            else:
                logging.info("Active TCP session to youtube.com detected. Skipping refresh.")
        else:
            logging.info(f"{app_name} is not focused. Skipping refresh.")

        logging.info(f"Waiting {interval // 3600} hours for the next refresh...")
        time.sleep(interval)  # Wait for the specified interval

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Automate cache clearing and refreshing of a target application.")
    parser.add_argument("--cache-dir", type=str, default=os.path.expanduser("~/.var/app/io.freetubeapp.FreeTube/cache"),
                        help="Path to the cache directory to clear (default: ~/.var/app/io.freetubeapp.FreeTube/cache).")
    parser.add_argument("--app-name", type=str, default="FreeTube",
                        help="Name of the application window to monitor (default: FreeTube).")
    parser.add_argument("--interval", type=int, default=3600,
                        help="Refresh interval in seconds (default: 3600 seconds or 1 hour).")
    args = parser.parse_args()

    # Validate dependencies
    for tool in ["xdotool", "wmctrl", "lsof", "protonvpn-app"]:
        if shutil.which(tool) is None:
            logging.error(f"Required tool '{tool}' is not installed. Please install it and try again.")
            return

    # Start the periodic refresher
    try:
        logging.info(f"Starting periodic refresher for {args.app_name}...")
        refresh_periodically(args.cache_dir, args.app_name, args.interval)
    except KeyboardInterrupt:
        logging.info("Exiting gracefully...")

if __name__ == "__main__":
    main()
