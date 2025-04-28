#!/bin/bash
# MAC launcher for the citra tracker

# Change directory to the launcher file directory
cd "$( dirname "$0" )"

# Run the version check script to test if 3.12 is installed
python util/python-version-check.py

# ERROR LEVELS: 0 - Success, 127 - Fail (python not found), 2 - Fail (incorrect python version)
case $? in
127)
    # Python not found on PATH
    echo Python is not installed or the PATH was not set during installation.
    echo Python 3.12 is required to run the tracker. Install from https://www.python.org/
    echo Check for an "add python to PATH" option and make sure that is enabled.
    ;;
0)
    # Run the tracker
    echo Launching the Citra Tracker...
    python citra-updater.py
    ;;
esac

read -p "Press any key to exit..."