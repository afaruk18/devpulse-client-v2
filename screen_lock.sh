#!/bin/bash

# Screen Lock Script - Locks screen every 5 minutes
# Usage: ./screen_lock.sh [start|stop|status]

SCRIPT_NAME="screen_lock.sh"
LOCK_PID_FILE="/tmp/screen_lock.pid"

# Function to start the screen lock
start_lock() {
    echo "Starting screen lock (every 5 minutes)..."
    
    # Kill any existing xautolock process
    if [ -f "$LOCK_PID_FILE" ]; then
        kill $(cat "$LOCK_PID_FILE") 2>/dev/null
        rm -f "$LOCK_PID_FILE"
    fi
    
    # Start xautolock with i3lock
    xautolock -time 5 -locker "i3lock -c 000000" -detectsleep &
    echo $! > "$LOCK_PID_FILE"
    
    echo "Screen lock started! Screen will lock after 5 minutes of inactivity."
    echo "PID saved to: $LOCK_PID_FILE"
}

# Function to stop the screen lock
stop_lock() {
    echo "Stopping screen lock..."
    
    if [ -f "$LOCK_PID_FILE" ]; then
        PID=$(cat "$LOCK_PID_FILE")
        kill $PID 2>/dev/null
        rm -f "$LOCK_PID_FILE"
        echo "Screen lock stopped."
    else
        echo "No screen lock process found."
    fi
}

# Function to check status
check_status() {
    if [ -f "$LOCK_PID_FILE" ]; then
        PID=$(cat "$LOCK_PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Screen lock is ACTIVE (PID: $PID)"
            echo "Screen will lock after 5 minutes of inactivity"
        else
            echo "Screen lock process not running (stale PID file)"
            rm -f "$LOCK_PID_FILE"
        fi
    else
        echo "Screen lock is INACTIVE"
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [start|stop|status]"
    echo ""
    echo "Commands:"
    echo "  start   - Start screen lock (every 5 minutes)"
    echo "  stop    - Stop screen lock"
    echo "  status  - Check if screen lock is running"
    echo ""
    echo "Examples:"
    echo "  $0 start    # Start the screen lock"
    echo "  $0 stop     # Stop the screen lock"
    echo "  $0 status   # Check status"
}

# Main script logic
case "$1" in
    start)
        start_lock
        ;;
    stop)
        stop_lock
        ;;
    status)
        check_status
        ;;
    *)
        show_usage
        exit 1
        ;;
esac