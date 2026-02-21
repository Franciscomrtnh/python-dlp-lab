import warnings
warnings.filterwarnings("ignore", category=UserWarning)import os
import re
import hashlib
from datetime import datetime
import getpass
import time

# Only needed for Excel files
try:
    import openpyxl
except ImportError:
    print("openpyxl not installed, .xlsx files will be skipped")

# ===== CONFIG =====
CONFIDENTIAL_FOLDER = "C:\\Company\\Confidential"
USB_FOLDER = "C:\\Company\\USB"
LOG_FILE = "C:\\Company\\Logs\\dlp_log.txt"

# ===== PATTERNS =====
patterns = {
    "Credit Card": r"\b\d{4}-\d{4}-\d{4}-\d{4}\b",
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "API Key": r"sk_[a-zA-Z0-9_]+"
}

# ===== HASH FUNCTION =====
def hash_file(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()

# ===== READ EXCEL =====
def read_excel(filepath):
    try:
        wb = openpyxl.load_workbook(filepath, data_only=True)
        text = ""
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                for cell in row:
                    if cell:
                        text += str(cell) + " "
        return text
    except Exception as e:
        print(f"⚠ Could not read Excel file {filepath}: {e}")
        return ""

# ===== SCAN FILE =====
def scan_file(filepath):
    if os.path.isdir(filepath):
        return None
    content = ""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".txt":
        try:
            with open(filepath, "r", errors="ignore") as f:
                content = f.read()
        except:
            return None
    elif ext == ".xlsx":
        if "openpyxl" in globals():
            content = read_excel(filepath)
        else:
            return None
    else:
        return None

    username = getpass.getuser()
    file_hash = hash_file(filepath)

    # Determine severity
    abs_path = os.path.abspath(filepath).replace("\\", "/").lower()
    usb_path = os.path.abspath(USB_FOLDER).replace("\\", "/").lower()
    if abs_path.startswith(usb_path):
        severity = "HIGH"
    else:
        severity = "MEDIUM"

    alerts = []
    for label, pattern in patterns.items():
        if re.search(pattern, content):
            alerts.append((label, severity, username, filepath, file_hash))
    return alerts

# ===== MAIN LOOP =====
print("🔍 DLP scan started. Press Ctrl+C to stop.")
logged_hashes = set()

try:
    while True:
        for folder in [CONFIDENTIAL_FOLDER, USB_FOLDER]:
            if not os.path.exists(folder):
                continue
            for file in os.listdir(folder):
                filepath = os.path.join(folder, file)
                results = scan_file(filepath)
                if results:
                    for label, severity, username, fp, file_hash in results:
                        if file_hash not in logged_hashes:
                            logged_hashes.add(file_hash)
                            log_entry = f"{datetime.now()} | {severity} | {label} detected | User: {username} | File: {fp} | Hash: {file_hash}\n"
                            with open(LOG_FILE, "a") as log:
                                log.write(log_entry)
                            print(f"🚨 ALERT: {label} detected in {fp} (Severity: {severity})")
        time.sleep(5)
except KeyboardInterrupt:
    print("DLP scan stopped.")