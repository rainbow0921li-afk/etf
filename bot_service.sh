#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$DIR/bot.log"
PID_FILE="$DIR/bot.pid"
if [ -f "$DIR/.env" ]; then
    export $(grep -v '^#' "$DIR/.env" | xargs)
fi

start() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Telegram Bot is already running with PID $(cat "$PID_FILE")."
        return 0
    fi
    echo "Starting Telegram Bot as an independent system daemon..."
    cd "$DIR"
    export GITHUB_TOKEN="$GITHUB_TOKEN"
    setsid nohup python3 -u scripts/telegram_bot.py > "$LOG_FILE" 2>&1 < /dev/null &
    NEW_PID=$!
    echo $NEW_PID > "$PID_FILE"
    sleep 2
    if kill -0 $NEW_PID 2>/dev/null; then
        echo "Telegram Bot started successfully with PID $NEW_PID."
        echo "Logs: $LOG_FILE"
    else
        echo "Failed to start Telegram Bot. Check $LOG_FILE."
    fi
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 $PID 2>/dev/null; then
            echo "Stopping Telegram Bot (PID $PID)..."
            kill $PID
            sleep 1
            kill -9 $PID 2>/dev/null
        fi
        rm -f "$PID_FILE"
    fi
    pkill -f "python3 scripts/telegram_bot.py" 2>/dev/null
    echo "Telegram Bot stopped."
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Telegram Bot is RUNNING with PID $(cat "$PID_FILE")."
        ps -f -p $(cat "$PID_FILE")
    else
        PID=$(pgrep -f "python3 scripts/telegram_bot.py")
        if [ -n "$PID" ]; then
            echo "Telegram Bot is RUNNING with PID $PID (untracked pidfile)."
        else
            echo "Telegram Bot is STOPPED."
        fi
    fi
}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) stop && sleep 1 && start ;;
    status) status ;;
    *) echo "Usage: $0 {start|stop|restart|status}" ;;
esac
