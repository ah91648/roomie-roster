#!/bin/bash

# RoomieRoster Application Launcher for Unix/Linux/macOS
# This shell script launches the Python launcher script

echo "======================================================"
echo "🏠 RoomieRoster Application Launcher (Unix/Linux/macOS)"
echo "   Household Chore Management Made Easy"
echo "======================================================"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the Python launcher
cd "$SCRIPT_DIR"
python3 launch_app.py