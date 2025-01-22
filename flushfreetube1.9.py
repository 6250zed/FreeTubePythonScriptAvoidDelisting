import os
import shutil
import time
import subprocess
import pyautogui
import sqlite3
from scapy.all import sniff, TCP

CACHE_DIR = os.path.expanduser("~/.config/FreeTube/Cache")
YOUTUBE_DOMAINS = ["youtube.com", "google.com"]

def clear_cache():
    """Clears the FreeTube cache directory."""
    if os.path.exists(CACHE_DIR):
        try:
            shutil.rmtree(CACHE_DIR)
            os.makedirs(CACHE_DIR)
            print("[INFO] Cache cleared.")
        except Exception as e:
            print(f"[ERROR] Error clearing cache: {e}")

def get_focused_window():
    """Returns the title of the currently focused window using wmctrl."""
    try:
        result = subprocess.run(
            ["wmctrl", "-lp"],
            stdout=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            print("[ERROR] Failed to retrieve focused window.")
            return None

        active_window = subprocess.check_output(["xdotool", "getwindowfocus", "getwindowname"], text=True).strip()
        print(f"[DEBUG] Focused window: {active_window}")
        return active_window
    except Exception as e:
        print(f"[ERROR] Unable to get focused window: {e}")
        return None

def is_freetube_window():
    """Checks if the focused window belongs to FreeTube."""
    focused_window = get_focused_window()
    is_focused = focused_window and "FreeTube" in focused_window
    print(f"[DEBUG] Is FreeTube window focused: {is_focused}")
    return is_focused

def refresh_freetube():
    """Simulates Ctrl+Shift+R to refresh FreeTube using pyautogui."""
    try:
        pyautogui.hotkey('ctrl', 'shift', 'r')
        print("[INFO] Refreshed FreeTube.")
    except Exception as e:
        print(f"[ERROR] Failed to refresh FreeTube: {e}")

def remove_youtube_cache_entries():
    """
    Queries the ~/.cache/mozilla/firefox/i0yvla7i.default-release/cache2/index.sqlite
    file for any entries containing 'youtube.com' and removes them entirely.
    Adjust the table name as needed if your Firefox version differs.
    """
    index_db = os.path.expanduser("~/.cache/mozilla/firefox/i0yvla7i.default-release/cache2/index.sqlite")

    if not os.path.exists(index_db):
        print(f"[ERROR] The Firefox cache index database was not found at: {index_db}")
        return

    try:
        # Connect to the index.sqlite database
        conn = sqlite3.connect(index_db)
        cursor = conn.cursor()

        # The table name "moz_cache" may vary; in some releases it could be "entries" or something else.
        # If you receive an error, open index.sqlite in an SQLite browser to verify the table and column names.
        table_name = "moz_cache"  # Adjust if needed
        column_key = "key"        # Adjust if needed
        column_id = "id"          # Adjust if needed

        # Look for entries containing "youtube.com" in the 'key' column
        query_select = f"SELECT {column_id}, {column_key} FROM {table_name} WHERE {column_key} LIKE '%youtube.com%'"
        cursor.execute(query_select)
        entries = cursor.fetchall()

        if entries:
            for entry_id, key in entries:
                print(f"[INFO] Found YouTube-related entry (ID: {entry_id}) => {key}")
                # Delete the entry by ID
                query_delete = f"DELETE FROM {table_name} WHERE {column_id} = ?"
                cursor.execute(query_delete, (entry_id,))

            conn.commit()
            print("[INFO] Successfully removed YouTube cache entries.")
        else:
            print("[INFO] No YouTube entries found in Firefox cache index.")

        conn.close()

    except sqlite3.Error as e:
        print(f"[ERROR] SQLite Error: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error while removing YouTube cache entries: {e}")

def packet_callback(packet):
    """Callback function to handle packets."""
    try:
        if packet.haslayer(TCP):
            # Extract the destination host if available
            if packet.haslayer("IP"):
                host = packet["IP"].dst
            elif packet.haslayer("IPv6"):
                host = packet["IPv6"].dst
            else:
                return

            # Check if the host matches YouTube or Google domains
            for domain in YOUTUBE_DOMAINS:
                if domain in str(host):
                    print(f"[DEBUG] Detected HTTPS request to {host}")
                    if is_freetube_window():
                        print("[INFO] FreeTube is focused. Refreshing...")
                        clear_cache()
                        time.sleep(4)  # Allow cache to clear before refreshing
                        refresh_freetube()
                        # Additional task: remove entries with youtube.com in Firefox cache
                        remove_youtube_cache_entries()
                    else:
                        print("[INFO] FreeTube is not focused. Skipping refresh.")
                    break
    except Exception as e:
        print(f"[ERROR] Exception in packet processing: {e}")

def monitor_https_requests():
    """Monitors network traffic for HTTPS requests to or from Google."""
    print("[INFO] Monitoring HTTPS requests...")
    try:
        sniff(filter="tcp port 443", prn=packet_callback, store=False)
    except KeyboardInterrupt:
        print("[INFO] Stopping network monitor.")
    except Exception as e:
        print(f"[ERROR] Error monitoring network traffic: {e}")

if __name__ == "__main__":
    try:
        print("[INFO] Starting FreeTube HTTPS monitor...")
        monitor_https_requests()
    except KeyboardInterrupt:
        print("[INFO] Exiting...")
