#!/bin/bash
# Flatpak launcher script for Money Tracker

# Set up environment
export PYTHONPATH="/app/app:$PYTHONPATH"
cd /app

# Run the Python application
exec python3 main.py "$@"