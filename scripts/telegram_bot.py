#!/usr/bin/env python3
"""
Telegram Bot for ETF Dashboard & Remote Antigravity Agent
Pure Agent Mode (純代理模式):
- Directly wraps Google Antigravity (agy) engine in the Docker container.
- Turns Telegram into a 24/7 remote-control AI Coding Assistant.
- Fast-path for ETF quotes, system status, and git triggers.
- For all other requests, automatically executes `agy` with full tool capabilities.
"""

import urllib.request
import urllib.error
import json
import time
import os
import re
import sys
import datetime
import threading
import queue
import subprocess
import shutil

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8986464959:AAG6Hl26vSx2mygIHi3knYzsxA3xf_UJr9s")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "rainbow0921li-afk")
GITHUB_REPO = os.getenv("GITHUB_REPO", "etf")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, '..'))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')

# Task Queue for Sequential Agent Execution
task_queue = queue.Queue()

# --- Telegram API Helpers ---

def api_call(endpoint, payload=None):
    url = f"{API_BASE}/{endpoint}"
    data = json.dumps(payload).encode('utf-8') if payload else None
    headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode('utf-8'))
        except Exception:
            return {"ok": False, "description": str(e)}
    except Exception as e:
        print(f"API Error ({endpoint}): {e}")
        return {"ok": False, "description": str(e)}

def download_telegram_file(file_id, dest_path):
    res = api_call("getFile", {"file_id": file_id})
    if not res or not res.get("ok"):
        return False
    file_path = res["result"].get("file_path")
    if not file_path:
        return False
    
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    req = urllib.request.Request(file_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r, open(dest_path, "wb") as f:
            f.write(r.read())
        return True
    except Exception as e:
        print(f"Failed to download telegram file {file_id}: {e}")
        return False

def send_chat_action(chat_id, action="typing"):
    return api_call("sendChatAction", {"chat_id": chat_id, "action": action})

def send_message(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup

    res = api_call("sendMessage", payload)
    # If markdown parsing fails, fallback to plain text
    if not res or not res.get("ok"):
        if parse_mode:
            payload.pop("parse_mode", None)
            res = api_call("sendMessage", payload)
    return res

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="Markdown"):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "disable_web_page_preview": True
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup

    res = api_call("editMessageText", payload)
    if not res or not res.get("ok"):
        if parse_mode:
            payload.pop("parse_mode", None)
            res = api_call("editMessageText", payload)
    return res

def send_or_edit_response(chat_id, message_id, text, reply_markup=None):
    if not text or not text.strip():
        text = "✅ 執行完成（無文字輸出）。"

    max_len = 3900
    chunks = []
    while len(text) > max_len:
        split_idx = text.rfind('\n', 0, max_len)
        if split_idx == -1 or split_idx < 1500:
            split_idx = max_len
        chunks.append(text[:split_idx])
        text = text[split_idx:].lstrip()
    if text:
        chunks.append(text)

    # Edit the first chunk into the placeholder message
    first_chunk = chunks[0]
    res = edit_message(chat_id, message_id, first_chunk, reply_markup=(reply_markup if len(chunks) == 1 else None))
    if not res or not res.get("ok"):
        send_message(chat_id, first_chunk, reply_markup=(reply_markup if len(chunks) == 1 else None))

    # Send remaining chunks
    for i, chunk in enumerate(chunks[1:]):
        is_last = (i == len(chunks[1:]) - 1)
        send_message(chat_id, chunk, reply_markup=(reply_markup if is_last else None))

# --- Typing Notification Thread ---

def typing_indicator_loop(chat_id, stop_event):
    while not stop_event.is_set():
        try:
            send_chat_action(chat_id, "typing")
        except Exception:
            pass
        stop_event.wait(4.0)

# --- Agent Worker Thread ---

def run_agent_turn(chat_id, prompt, is_new=False):
    short_prompt = prompt if len(prompt) < 70 else prompt[:67] + "..."
    # Escape markdown special characters in prompt preview
    safe_preview = short_prompt.replace('*', '').replace('_', '').replace('`', '')
    
    init_msg = f"""
🤖 *Antigravity AI 正在執行中...*
━━━━━━━━━━━━━━━━━━
💬 *任務*：`{safe_preview}`
⏳ _正在編寫程式碼、呼叫工具或分析資料，請稍候..._
""".strip()
    init_res = send_message(chat_id, init_msg, reply_markup=get_main_keyboard())
    msg_id = init_res['result']['message_id'] if init_res and init_res.get('ok') else None

    stop_typing = threading.Event()
    th = threading.Thread(target=typing_indicator_loop, args=(chat_id, stop_typing), daemon=True)
    th.start()

    if is_new:
        cmd = ['agy', '-p', prompt, '--dangerously-skip-permissions']
    else:
        cmd = ['agy', '-c', '-p', prompt, '--dangerously-skip-permissions']

    print(f"[Agent Task] Running for {chat_id}: {prompt[:50]}")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=PROJECT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        stdout, _ = proc.communicate(timeout=240)
        output = stdout.strip() if stdout else "✅ 任務完成（無額外輸出）。"
    except subprocess.TimeoutExpired:
        proc.kill()
        output = "⚠️ 任務執行逾時（超過 4 分鐘）。已自動終止行程。"
    except Exception as e:
        output = f"❌ 執行發生異常：{e}"
    finally:
        stop_typing.set()

    print(f"[Agent Task] Completed for {chat_id}, output length: {len(output)}")
    if msg_id:
        send_or_edit_response(chat_id, msg_id, output, reply_markup=get_main_keyboard())
    else:
        send_message(chat_id, output, reply_markup=get_main_keyboard())

def agent_worker_loop():
    print("Agent Worker Thread started...")
    while True:
        try:
            item = task_queue.get()
            if item is None:
                break
            chat_id, prompt, is_new = item
            run_agent_turn(chat_id, prompt, is_new)
        except Exception as e:
            print(f"Agent worker error: {e}")
        finally:
            task_queue.task_done()

# --- System & Quick Features ---

def get_main_keyboard():
    return {
        "keyboard": [[{"text": "🖥️ 伺服器狀態"}]],
        "resize_keyboard": True,
        "persistent": True
    }

def format_system_status():
    uptime_str = "--"
    try:
        with open("/proc/uptime", "r") as f:
            seconds = float(f.readline().split()[0])
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            uptime_str = f"{hours} 小時 {mins} 分"
    except Exception:
        pass

    mem_str = "--"
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
            total = int([l for l in lines if "MemTotal" in l][0].split()[1]) // 1024
            avail = int([l for l in lines if "MemAvailable" in l][0].split()[1]) // 1024
            used = total - avail
            mem_str = f"{used} MB / {total} MB"
    except Exception:
        pass

    disk_str = "--"
    try:
        du = shutil.disk_usage("/home/developer")
        disk_total_gb = du.total / (1024**3)
        disk_used_gb = du.used / (1024**3)
        disk_str = f"{disk_used_gb:.1f} GB / {disk_total_gb:.1f} GB ({du.used / du.total * 100:.1f}%)"
    except Exception:
        pass

    git_str = "--"
    try:
        res = subprocess.run(["git", "log", "-1", "--oneline"], cwd=PROJECT_DIR, capture_output=True, text=True)
        git_str = res.stdout.strip()
    except Exception:
        pass

    tracked = []
    tracked_file = os.path.join(DATA_DIR, 'tracked_etfs.json')
    if os.path.exists(tracked_file):
        try:
            with open(tracked_file, 'r', encoding='utf-8') as f:
                tracked = json.load(f)
        except Exception:
            pass

    msg = f"""
🖥️ *容器與 Agent 伺服器狀態*
━━━━━━━━━━━━━━━━━━
⚙️ *代理模式*：`純代理模式 (Antigravity Headless Agent)`
⏱️ *容器運行時間*：`{uptime_str}`
🧠 *記憶體使用*：`{mem_str}`
💾 *硬碟容量*：`{disk_str}`
📌 *目前追蹤標的*：`{', '.join(tracked) if tracked else '0050, 0056'}`
🌿 *最新 Git 提交*：`{git_str}`
🌐 *看板線上網址*：[點此開啟](https://{GITHUB_OWNER}.github.io/{GITHUB_REPO}/)

💡 _現在本機就是您的 24/7 AI 雲端工作站，您可以直接打任何文字交代任務！_
""".strip()
    return msg

def get_etf_data(symbol):
    local_file = os.path.join(DATA_DIR, f"{symbol}.json")
    if os.path.exists(local_file):
        with open(local_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    try:
        url = f"https://{GITHUB_OWNER}.github.io/{GITHUB_REPO}/data/{symbol}.json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"Failed to fetch {symbol}.json: {e}")
        return None

def format_etf_card(symbol):
    data = get_etf_data(symbol)
    if not data:
        return f"⚠️ 暫時無法讀取 {symbol} 資料，請稍後再試。"

    m = data['metadata']
    q = data['quote']
    inst = data.get('institutional', {})

    is_up = q['change'] > 0
    is_down = q['change'] < 0
    sign = "+" if is_up else ""
    trend_emoji = "🔴" if is_up else ("🟢" if is_down else "⚪")

    disc = q.get('discount_percent', 0.0)
    disc_sign = "+" if disc > 0 else ""
    disc_tag = "溢價" if disc > 0 else ("折價" if disc < 0 else "平價")

    def fmt_lots(lots):
        if lots is None: return "--"
        s = "+" if lots > 0 else ""
        return f"{s}{lots:,} 張"

    w = m.get('warning')
    warning_badge = " ⚠️ [風險警示]" if (w and w.get('has_warning')) else ""
    warning_block = ""
    if w and w.get('has_warning'):
        warning_block = f"""
⚠️ *【{w.get('title', '高配息與景氣循環風險警示')}】*
• {w.get('short_reason', '')}
• 提醒：切勿落入高殖利率陷阱，請以「含息總報酬率」為核心評估指標！
"""

    msg = f"""
*{m['symbol']} {m['short_name']}*{warning_badge} ({m.get('category', 'ETF')})
━━━━━━━━━━━━━━━━━━
💰 *現價*：`NT$ {q['price']:.2f}` {trend_emoji} `{sign}{q['change']:.2f} ({sign}{q['change_percent']:.2f}%)`
⚖️ *即時淨值*：`NT$ {q.get('nav', 0):.2f}` ({disc_tag} `{disc_sign}{disc:.2f}%`)
🏢 *基金總規模*：`NT$ {q.get('market_cap_display', '--')}`
📊 *今日區間*：`{q.get('low', 0):.2f} ~ {q.get('high', 0):.2f}`
📦 *成交量*：`{q.get('volume_shares', 0) // 1000:,} 張`

👥 *三大法人買賣超* ({inst.get('date', '最新')}):
• 外資及陸資：`{fmt_lots(inst.get('foreign_lots'))}`
• 投信：`{fmt_lots(inst.get('trust_lots'))}`
• 自營商 (總計)：`{fmt_lots(inst.get('dealer_total_lots'))}`
  └ 自行 `{fmt_lots(inst.get('dealer_self_lots'))}` / 避險 `{fmt_lots(inst.get('dealer_hedge_lots'))}`
• *三大法人合計*：`{fmt_lots(inst.get('total_lots'))}`

📈 *累積報酬率 (含息)*：
近1月 `{data.get('returns', {}).get('1M', '--')}%` ｜ 近1年 `{data.get('returns', {}).get('1Y', '--')}%` ｜ 近3年 `{data.get('returns', {}).get('3Y', '--')}%`
{warning_block}
🕒 *最後更新*：`{m.get('updated_at', '')}`
""".strip()
    return msg

def format_comparison():
    d50 = get_etf_data('0050')
    d56 = get_etf_data('0056')
    if not d50 or not d56:
        return "⚠️ 比較資料載入失敗。"

    q50, q56 = d50['quote'], d56['quote']
    r50, r56 = d50['returns'], d56['returns']

    msg = f"""
⚖️ *0050 (市值型) vs 0056 (高股息) 重點速評*
━━━━━━━━━━━━━━━━━━
【*0050 元大台灣50*】
• 市價：`NT$ {q50['price']:.2f}` (淨值 {q50.get('nav', 0):.2f})
• 規模：`NT$ {q50.get('market_cap_display', '--')}`
• 費用率：`0.43%` ｜ 半年配
• 近1年報酬：`+{r50.get('1Y', 0)}%`
• 近3年報酬：`+{r50.get('3Y', 0)}%`
• 核心特色：半導體佔比 >63%，台積電龍頭成長爆發力。

【*0056 元大高股息*】
• 市價：`NT$ {q56['price']:.2f}` (淨值 {q56.get('nav', 0):.2f})
• 規模：`NT$ {q56.get('market_cap_display', '--')}`
• 費用率：`0.45%` ｜ 季季配 (1/4/7/10月)
• 近1年報酬：`+{r56.get('1Y', 0)}%`
• 近3年報酬：`+{r56.get('3Y', 0)}%`
• 核心特色：電腦代工與高殖利率金融/傳產，現金流防禦穩定。
""".strip()
    return msg

def trigger_github_update():
    token = GITHUB_TOKEN or os.getenv("GITHUB_TOKEN", "")
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/update-data.yml/dispatches"
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'TelegramBot'
    }
    payload = json.dumps({"ref": "main"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            if res.status == 204:
                return "🚀 *已成功向 GitHub 雲端發送更新指令！*\n\n雲端爬蟲已經開始執行，約 30～45 秒後網頁與機器人資料將同步更新至最新！"
    except Exception as e:
        return f"❌ 觸發更新失敗: {e}"
    return "⚠️ 觸發更新未收到確認。"

# --- Main Message Handler ---

def handle_message(msg):
    chat_id = msg['chat']['id']
    text = (msg.get('text') or '').strip()
    photo = msg.get('photo')
    caption = (msg.get('caption') or '').strip()
    document = msg.get('document')

    # 1. 圖片訊息 (Photo / Image Document) - 啟動多模態視覺 AI 解讀
    if photo or (document and document.get('mime_type', '').startswith('image/')):
        img_dir = os.path.join(PROJECT_DIR, 'tg_images')
        os.makedirs(img_dir, exist_ok=True)
        
        if photo:
            # 取最高解析度的相片 (陣列最後一個)
            file_id = photo[-1]['file_id']
            ext = '.jpg'
        else:
            file_id = document['file_id']
            orig_name = document.get('file_name', 'img.png')
            ext = os.path.splitext(orig_name)[1] or '.png'

        timestamp = int(time.time() * 1000)
        local_img_path = os.path.join(img_dir, f"tg_{chat_id}_{timestamp}{ext}")

        send_message(chat_id, "📥 收到圖片！正在下載並啟動 Antigravity 多模態視覺 AI 分析中...")
        success = download_telegram_file(file_id, local_img_path)
        if not success or not os.path.exists(local_img_path):
            send_message(chat_id, "❌ 圖片下載失敗，請稍後再試。")
            return

        if caption:
            prompt = f"請使用 view_file 查看使用者傳送的圖片 {local_img_path}，並依據使用者隨附的要求或問題進行詳細回答與解讀：「{caption}」"
        else:
            prompt = f"請使用 view_file 查看使用者傳送的圖片 {local_img_path}，詳細解讀並結構化分析這張圖片的內容、畫面細節、圖表文字/數據與重點意涵。"

        print(f"Received image from {chat_id}, saved to {local_img_path}, caption: {caption}")
        task_queue.put((chat_id, prompt, False))
        return

    if not text:
        return

    print(f"Received from {chat_id}: {text}")

    # 2. 說明與選單
    if text in ['/start', '/help', '選單', 'help', 'menu']:
        welcome_text = """
👋 您好！我是您的 *Antigravity AI 全能助理（純代理模式）*！

這個機器人直接連結此 Docker 容器內的 **Google Antigravity 核心引擎**。即使您關閉電腦終端機，隨時拿起手機在 Telegram 交代任務，我都可以在此容器內全自動完成！

💡 *您可以要我做什麼？（任何事情都可以！）*
▫️ 「*直接傳送圖片或截圖*」- 支援多模態視覺解讀（K線圖、對帳單、程式碼截圖、發票等）！
▫️ 「*幫我寫一個 Python 腳本抓每天天氣*」
▫️ 「*修改看板首頁，把標題加上今日日期*」
▫️ 「*幫我加入 00919 並推送到 GitHub Pages*」
▫️ 「*檢查容器目前的 git status 與檔案改動*」
▫️ 「*幫我分析 0050 與 00878 的配息優缺點*」

🛠️ *快捷控制指令*：
▫️ `/status` - 查看容器運算資源與伺服器狀態
▫️ `/reset` - 開啟全新的 AI 對話工作階段
▫️ `/compare` - 市值型 vs 高股息速評
▫️ 點選下方快速選單可即時查看伺服器狀態！

現在，請直接傳送任何文字、指令或圖片給我試試看吧！🚀
""".strip()
        send_message(chat_id, welcome_text, reply_markup=get_main_keyboard())
        return

    # 2. 伺服器狀態
    if text in ['/status', 'status', '🖥️ 伺服器狀態', '狀態', '系統狀態']:
        send_message(chat_id, format_system_status(), reply_markup=get_main_keyboard())
        return

    # 3. 開啟新對話 Session
    if text in ['/reset', '/new', '重置', '開啟新對話', '🔄 開啟新對話 (/reset)']:
        task_queue.put((chat_id, "已開啟全新對話工作階段。請簡短問候使用者，說明你已準備好協助任何程式與開發工作。", True))
        return

    # 4. 快速行情按鈕 (0.1秒秒回)
    etf_match = re.match(r'^(?:📊|💰|📌)?\s*(00\d{2,3}[A-Za-z]?)\s*(?:行情|即時行情|報價)?$', text)
    if etf_match:
        code = etf_match.group(1)
        card = format_etf_card(code)
        if "⚠️ 暫時無法讀取" not in card:
            send_message(chat_id, card, reply_markup=get_main_keyboard())
            return

    if text in ['/compare', '比較', '📈 雙標的速評比較']:
        send_message(chat_id, format_comparison(), reply_markup=get_main_keyboard())
        return

    if text in ['/update', '更新', '🔄 觸發雲端更新']:
        send_message(chat_id, "⏳ 正在聯絡 GitHub 雲端觸發重新爬蟲...", reply_markup=get_main_keyboard())
        res = trigger_github_update()
        send_message(chat_id, res, reply_markup=get_main_keyboard())
        return

    if text in ['/web', '/site', '網頁', '🌐 開啟專屬看板網頁']:
        link_msg = f"""
📱 *您的專屬 ETF 看板網站：*
👉 [點此開啟手機儀表板](https://{GITHUB_OWNER}.github.io/{GITHUB_REPO}/)

支援手機加入主畫面、自選 ETF 切換、即時淨值折溢價、互動走勢圖與法人籌碼動向！
""".strip()
        send_message(chat_id, link_msg, reply_markup=get_main_keyboard())
        return

    # 5. 【純代理模式核心】：任何自然語言指令與對話全部委託給 Antigravity Agent (agy) 執行！
    task_queue.put((chat_id, text, False))

def run_polling():
    print("Telegram Bot Polling started with Pure Agent Mode...")
    # Start Agent background worker
    worker_th = threading.Thread(target=agent_worker_loop, daemon=True)
    worker_th.start()

    last_update_id = 0
    while True:
        try:
            url = f"{API_BASE}/getUpdates?offset={last_update_id + 1}&timeout=20"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as res:
                data = json.loads(res.read().decode('utf-8'))
                for item in data.get('result', []):
                    last_update_id = item['update_id']
                    if 'message' in item:
                        handle_message(item['message'])
        except Exception as e:
            time.sleep(2)

if __name__ == '__main__':
    run_polling()
