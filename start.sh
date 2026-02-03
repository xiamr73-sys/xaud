#!/bin/bash
set -e

# Start the consolidated Monitor App (Flask + Background Thread)
# exec replaces the shell with the python process, ensuring signals are passed correctly
echo "Starting Monitor App on PORT=${PORT:-5001}..."
exec python3 monitor_app.py
