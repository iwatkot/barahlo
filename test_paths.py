#!/usr/bin/env python3
"""
Test script to verify paths are working correctly
"""
import os
import sys

# Add the script directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our main module
import main

print("📁 Script directory:", main.SCRIPT_DIR)
print("📄 Session file path:", main.SESSION_FILE)
print("📄 Forwarded messages file:", main.FORWARDED_MESSAGES_FILE)
print("🔑 API_ID loaded:", "Yes" if main.API_ID else "No")
print("🔑 PHONE_NUMBER loaded:", "Yes" if main.PHONE_NUMBER else "No")
print("🔍 Keywords loaded:", main.KEYWORDS)

# Check if files exist
print("\n📂 File existence:")
print(
    "  .env file:",
    "✅" if os.path.exists(os.path.join(main.SCRIPT_DIR, ".env")) else "❌",
)
print(
    "  Session file:", "✅" if os.path.exists(f"{main.SESSION_FILE}.session") else "❌"
)
print(
    "  Forwarded messages:",
    "✅" if os.path.exists(main.FORWARDED_MESSAGES_FILE) else "❌",
)
