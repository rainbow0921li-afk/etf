#!/usr/bin/env python3
"""
Telegram Bot for ETF Dashboard (0050 & 0056)
Supports:
- /start, /help: Interactive quick buttons
- /0050, 0050: Quote, NAV, Discount/Premium, Market Cap, Institutional Trading
- /0056, 0056: Quote, NAV, Discount/Premium, Market Cap, Institutional Trading
- /compare: 0050 vs 0056 Comparison
- /update: Trigger GitHub Actions remote re-crawl
- /dca <symbol> <amount> <years>: DCA investment simulation
Zero external dependencies: Uses only Python 3 standard library
"""

import urllib.request
import json
import time
import os
import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8986464959:AAG6Hl26vSx2mygIHi3knYzsxA3xf_UJr9s")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "rainbow0921li-afk")
GITHUB_REPO = os.getenv("GITHUB_REPO", "etf")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')

def api_call(endpoint, payload=None):
    url = f"{API_BASE}/{endpoint}"
    data = json.dumps(payload).encode('utf-8') if payload else None
    headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"API Error ({endpoint}): {e}")
        return None

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return api_call("sendMessage", payload)

def get_main_keyboard():
    return {
        "keyboard": [
            [{"text": "📊 0050 即時行情"}, {"text": "💰 0056 即時行情"}],
            [{"text": "📈 0050 vs 0056 比較"}, {"text": "🔄 觸發雲端更新"}],
            [{"text": "🌐 開啟專屬看板網頁"}]
        ],
        "resize_keyboard": True,
        "persistent": True
    }

def get_etf_data(symbol):
    local_file = os.path.join(DATA_DIR, f"{symbol}.json")
    if os.path.exists(local_file):
        with open(local_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    # Fallback to GitHub Pages
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

    # 三大法人
    def fmt_lots(lots):
        if lots is None:
            return "--"
        s = "+" if lots > 0 else ""
        return f"{s}{lots:,} 張"

    msg = f"""
*{m['symbol']} {m['short_name']}* ({m.get('category', 'ETF')})
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
近1月 `{q.get('returns', {}).get('1M', '--')}%` ｜ 近1年 `{data.get('returns', {}).get('1Y', '--')}%` ｜ 近3年 `{data.get('returns', {}).get('3Y', '--')}%`

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
    """Trigger GitHub Actions workflow dispatch"""
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/update-data.yml/dispatches"
    headers = {
        'Authorization': f'Bearer {GITHUB_TOKEN}',
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

def calculate_dca(symbol, monthly_amt, years):
    data = get_etf_data(symbol)
    if not data or not data.get('prices'):
        return "⚠️ 查無歷史價格，無法試算。"
    
    all_prices = data['prices']
    trading_days = min(len(all_prices), years * 252)
    sub = all_prices[-trading_days:]

    last_month = ''
    total_shares = 0
    total_invested = 0

    for p in sub:
        m = p['date'][:7]
        if m != last_month:
            last_month = m
            buy_price = p.get('adj_close') or p['close']
            shares = monthly_amt / buy_price
            total_shares += shares
            total_invested += monthly_amt

    latest_price = sub[-1]['close']
    current_val = round(total_shares * latest_price)
    profit = current_val - total_invested
    ret_pct = round((profit / total_invested) * 100, 1) if total_invested > 0 else 0
    sign = "+" if profit >= 0 else ""

    return f"""
💰 *{symbol} 定期定額歷史回測試算*
━━━━━━━━━━━━━━━━━━
• 每月扣款：`NT$ {monthly_amt:,} 元`
• 投資時間：`近 {years} 年`
• 累積投入本金：`NT$ {total_invested:,} 元`
• 目前累積市值：`NT$ {current_val:,} 元`
• 累積獲利金額：`{sign}NT$ {profit:,} 元`
• *總投資報酬率*：`{sign}{ret_pct}%`
• 累積持有股數：`{round(total_shares):,} 股`
_(以還原收盤價模擬每月首日扣款，含股息再投資)_
""".strip()

def handle_message(msg):
    chat_id = msg['chat']['id']
    text = (msg.get('text') or '').strip()

    print(f"Received from {chat_id}: {text}")

    if text in ['/start', '/help', '選單', 'help', 'menu']:
        welcome_text = """
👋 您好！我是您的 *0050 / 0056 ETF 隨身助理*！

您可以直接點擊下方按鈕或輸入指令：
▫️ `/0050` - 查看 0050 現價、淨值、折溢價與三大法人
▫️ `/0056` - 查看 0056 現價、淨值、折溢價與三大法人
▫️ `/compare` - 雙標的速評比較
▫️ `/dca 0050 5000 3` - 定期定額回測試算
▫️ `/update` - 遠端命令 GitHub 重抓最新資料
▫️ `/web` - 取得手機專屬看板連結
""".strip()
        send_message(chat_id, welcome_text, reply_markup=get_main_keyboard())

    elif text in ['/0050', '0050', '📊 0050 即時行情']:
        send_message(chat_id, format_etf_card('0050'), reply_markup=get_main_keyboard())

    elif text in ['/0056', '0056', '💰 0056 即時行情']:
        send_message(chat_id, format_etf_card('0056'), reply_markup=get_main_keyboard())

    elif text in ['/compare', '比較', '📈 0050 vs 0056 比較']:
        send_message(chat_id, format_comparison(), reply_markup=get_main_keyboard())

    elif text in ['/update', '更新', '🔄 觸發雲端更新']:
        send_message(chat_id, "⏳ 正在聯絡 GitHub 雲端觸發重新爬蟲...", reply_markup=get_main_keyboard())
        res = trigger_github_update()
        send_message(chat_id, res, reply_markup=get_main_keyboard())

    elif text in ['/web', '/site', '網頁', '🌐 開啟專屬看板網頁']:
        link_msg = f"""
📱 *您的專屬 ETF 看板網站：*
👉 [點此開啟手機儀表板](https://{GITHUB_OWNER}.github.io/{GITHUB_REPO}/)

支援手機加入主畫面、自選 0050/0056 切換、互動走勢圖與 50 檔成分股透視！
""".strip()
        send_message(chat_id, link_msg, reply_markup=get_main_keyboard())

    elif text.startswith('/dca'):
        parts = text.split()
        symbol = '0050'
        amt = 5000
        years = 3
        if len(parts) >= 2 and parts[1] in ['0050', '0056']:
            symbol = parts[1]
        if len(parts) >= 3 and parts[2].isdigit():
            amt = int(parts[2])
        if len(parts) >= 4 and parts[3].isdigit():
            years = int(parts[3])
        send_message(chat_id, calculate_dca(symbol, amt, years), reply_markup=get_main_keyboard())

    else:
        # Default fallback
        send_message(chat_id, f"💡 收到指令：「{text}」\n您可以點擊下方選單按鈕，或輸入 `/0050`、`/0056` 進行查詢！", reply_markup=get_main_keyboard())

def run_polling():
    print("Telegram Bot Polling started...")
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
            # print(f"Polling warning: {e}")
            time.sleep(2)

if __name__ == '__main__':
    run_polling()
