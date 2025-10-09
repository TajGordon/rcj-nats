#!/bin/bash
# Robot Startup Script
# Save to: /home/pi/start_robot.sh
# Make executable: chmod +x /home/pi/start_robot.sh

# Exit on error
set -e

# Configuration
ROBOT_DIR="/home/pi/rcj-nats"
LOG_LEVEL="${ROBOT_LOG_LEVEL:-INFO}"
VENV_PATH="$ROBOT_DIR/venv"  # If using virtual environment

# Banner
echo "========================================"
echo "   Soccer Robot - Starting Up"
echo "========================================"
echo "Log level: $LOG_LEVEL"
echo "Directory: $ROBOT_DIR"
echo "Time: $(date)"
echo "========================================"

# Change to robot directory
cd "$ROBOT_DIR" || exit 1

# Activate virtual environment if it exists
if [ -d "$VENV_PATH" ]; then
    echo "Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
fi

# Set environment variables
export ROBOT_LOG_LEVEL="$LOG_LEVEL"
export PYTHONUNBUFFERED=1

# Start robot
echo "Starting robot controller..."
python3 -m hypemage.scylla

# Capture exit code
EXIT_CODE=$?

# Log exit
if [ $EXIT_CODE -eq 0 ]; then
    echo "Robot exited cleanly (code 0)"
else
    echo "Robot exited with error (code $EXIT_CODE)"
    # Log to syslog for debugging
    logger -t robot "Robot exited with code $EXIT_CODE"
fi

exit $EXIT_CODE
