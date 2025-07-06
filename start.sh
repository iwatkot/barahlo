#!/bin/bash
# Startup script for Telegram Chat Parser
# Use this script to run the parser on your VPS

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script directory
cd "$SCRIPT_DIR"

# Run the Python script
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/main.py"
