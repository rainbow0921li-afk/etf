#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "[$(date)] Waiting 4s for active agent turn to complete..." >> "$DIR/restart.log"
sleep 4

echo "[$(date)] Executing bot_service.sh restart..." >> "$DIR/restart.log"
"$DIR/bot_service.sh" restart >> "$DIR/restart.log" 2>&1

echo "[$(date)] Sending explicit keyboard update to Telegram..." >> "$DIR/restart.log"
python3 -c '
import urllib.request, json
token = "8986464959:AAG6Hl26vSx2mygIHi3knYzsxA3xf_UJr9s"
url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {
    "chat_id": 5709621345,
    "text": "🤖 Telegram Bot 已完成熱重載更新！現已全面支援「圖片與截圖多模態解讀」。請直接在 Telegram 重新傳送您的圖片，我會立即為您分析解讀！",
        "keyboard": [
            [
                {"text": "🌐 ETF 看板網站", "web_app": {"url": "https://rainbow0921li-afk.github.io/etf/"}},
                {"text": "🖥️ 伺服器狀態"}
            ]
        ],
        "resize_keyboard": True,
        "persistent": True
    }
}
try:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        print("Telegram API response:", resp.read().decode("utf-8"))
except Exception as e:
    print("Telegram API error:", e)
' >> "$DIR/restart.log" 2>&1

echo "[$(date)] Bot restart and refresh complete." >> "$DIR/restart.log"
