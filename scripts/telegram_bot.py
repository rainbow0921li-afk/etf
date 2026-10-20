#!/usr/bin/env python3
"""
Telegram Bot for ETF Dashboard
Supports Natural Language ChatOps:
- "幫我加入00878", "新增00919", "我想看006208": Automatically crawls and pushes to GitHub
- "0050", "0056", "00878", "00878 報價": Instantly shows price, NAV, discount, and institutional trading
- /start, /help, /compare, /dca, /update
Zero external dependencies: Uses only Python 3 standard library
"""

import urllib.request
import json
import time
import os
import re
import sys
import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8986464959:AAG6Hl26vSx2mygIHi3knYzsxA3xf_UJr9s")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "rainbow0921li-afk")
GITHUB_REPO = os.getenv("GITHUB_REPO", "etf")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')

NAME_TO_CODE = {
    "國泰永續高股息": "00878",
    "群益台灣精選高息": "00919",
    "富邦台50": "006208",
    "富邦台灣50": "006208",
    "元大台灣50": "0050",
    "元大高股息": "0056",
    "復華台灣科技優息": "00929",
    "元大高息低波": "00713",
    "元大台灣高息低波": "00713"
}

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
    # Dynamically build keyboard based on tracked ETFs
    buttons = [
        [{"text": "📊 0050 即時行情"}, {"text": "💰 0056 即時行情"}],
        [{"text": "📈 雙標的速評比較"}, {"text": "🔄 觸發雲端更新"}],
        [{"text": "🌐 開啟專屬看板網頁"}]
    ]
    tracked_file = os.path.join(DATA_DIR, 'tracked_etfs.json')
    if os.path.exists(tracked_file):
        try:
            with open(tracked_file, 'r', encoding='utf-8') as f:
                tracked = json.load(f)
                extra = [t for t in tracked if t not in ['0050', '0056']]
                if extra:
                    extra_row = [{"text": f"📌 {code} 行情"} for code in extra[:2]]
                    buttons.insert(1, extra_row)
        except Exception:
            pass

    return {
        "keyboard": buttons,
        "resize_keyboard": True,
        "persistent": True
    }

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
近1月 `{data.get('returns', {}).get('1M', '--')}%` ｜ 近1年 `{data.get('returns', {}).get('1Y', '--')}%` ｜ 近3年 `{data.get('returns', {}).get('3Y', '--')}%`

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

def add_new_etf_and_push(symbol, chat_id):
    """ChatOps: Add new ETF dynamically, fetch, commit & push to GitHub"""
    send_message(chat_id, f"⏳ 收到指令！正在為您向臺灣證券交易所與 Yahoo 抓取【{symbol}】的即時報價、淨值、法人籌碼與配息資料...")
    
    fetch_script = os.path.join(BASE_DIR, 'fetch_data.py')
    cmd = f"{sys.executable} {fetch_script} add {symbol}"
    ret = os.system(cmd)
    if ret != 0:
        send_message(chat_id, f"❌ 抓取【{symbol}】失敗，請確認代號是否為臺灣證交所合法上市 ETF。")
        return

    data = get_etf_data(symbol)
    if not data:
        send_message(chat_id, f"❌ 未能生成【{symbol}】資料集。")
        return

    # Commit and push
    send_message(chat_id, f"📦 資料抓取成功！正在自動同步推送至您的雲端 GitHub Pages...")
    repo_dir = os.path.abspath(os.path.join(BASE_DIR, '..'))
    token = GITHUB_TOKEN or os.getenv("GITHUB_TOKEN", "")
    if token:
        remote_url = f"https://{token}@github.com/{GITHUB_OWNER}/{GITHUB_REPO}.git"
        push_cmd = f"cd {repo_dir} && git add data/ && git commit -m 'feat(etf): auto-add {symbol} via Telegram ChatOps' && git remote set-url origin {remote_url} && git push origin main && git remote set-url origin https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}.git"
        os.system(push_cmd)

    m = data['metadata']
    q = data['quote']
    disc = q.get('discount_percent', 0.0)
    disc_tag = "溢價" if disc > 0 else "折價"

    success_msg = f"""
🎉 *成功將【{symbol} {m.get('short_name', '')}】上架至您的雲端看板！*
━━━━━━━━━━━━━━━━━━
💰 *現價*：`NT$ {q['price']:.2f}`
⚖️ *即時淨值*：`NT$ {q.get('nav', 0):.2f}` ({disc_tag} `{disc:+.2f}%`)
🏢 *基金總規模*：`NT$ {q.get('market_cap_display', '--')}`
📅 *配息週期*：`{m.get('dividend_frequency', '--')}`

🌐 [點此在手機開啟 {symbol} 看板](https://{GITHUB_OWNER}.github.io/{GITHUB_REPO}/#{symbol})
_(手機重新整理後，頂部標籤頁已自動新增 [{symbol}] 按鈕！)_
""".strip()
    send_message(chat_id, success_msg, reply_markup=get_main_keyboard())

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

    # 1. 快捷選單指令
    if text in ['/start', '/help', '選單', 'help', 'menu']:
        welcome_text = """
👋 您好！我是您的 *ETF 智慧投資助理*！

您可以直接用大白話跟我說話，例如：
▫️ 「*幫我加入 00878*」或「*加入 00919*」
▫️ 「*查 0050*」或「*0056 淨值*」
▫️ 「*比較*」看 0050 與 0056 的差別
▫️ 「*試算 0050 5000 3年*」

或是直接點擊下方快速按鈕！
""".strip()
        send_message(chat_id, welcome_text, reply_markup=get_main_keyboard())
        return

    # 2. 自然語言識別：加入 / 新增標的
    is_add_action = any(k in text for k in ['加', '加入', '新增', '追蹤', '放進', '加進', '要看', '上架', '能不能加', '幫我加'])
    extracted_code = None
    
    code_match = re.search(r'(00\d{2,3}[A-Za-z]?)', text)
    if code_match:
        extracted_code = code_match.group(1)
    else:
        for name, code in NAME_TO_CODE.items():
            if name in text:
                extracted_code = code
                break

    if is_add_action and extracted_code:
        add_new_etf_and_push(extracted_code, chat_id)
        return

    # 3. 自然語言識別：查詢某檔 ETF（例如「0050」、「查0056」、「00878報價」）
    if extracted_code and not is_add_action:
        # Check if we already have it
        local_path = os.path.join(DATA_DIR, f"{extracted_code}.json")
        if os.path.exists(local_path):
            send_message(chat_id, format_etf_card(extracted_code), reply_markup=get_main_keyboard())
            return
        else:
            # 尚未收錄，主動詢問是否加入
            prompt = f"💡 站台目前尚未收錄【{extracted_code}】。\n\n您可以直接跟我說：\n👉「*幫我加入 {extracted_code}*」\n我就會立刻為您自動抓取並上架到手機網頁中！"
            send_message(chat_id, prompt, reply_markup=get_main_keyboard())
            return

    # 4. 固定按鈕對應
    if text in ['/0050', '📊 0050 即時行情']:
        send_message(chat_id, format_etf_card('0050'), reply_markup=get_main_keyboard())
    elif text in ['/0056', '💰 0056 即時行情']:
        send_message(chat_id, format_etf_card('0056'), reply_markup=get_main_keyboard())
    elif text in ['/compare', '比較', '📈 雙標的速評比較']:
        send_message(chat_id, format_comparison(), reply_markup=get_main_keyboard())
    elif text in ['/update', '更新', '🔄 觸發雲端更新']:
        send_message(chat_id, "⏳ 正在聯絡 GitHub 雲端觸發重新爬蟲...", reply_markup=get_main_keyboard())
        res = trigger_github_update()
        send_message(chat_id, res, reply_markup=get_main_keyboard())
    elif text in ['/web', '/site', '網頁', '🌐 開啟專屬看板網頁']:
        link_msg = f"""
📱 *您的專屬 ETF 看板網站：*
👉 [點此開啟手機儀表板](https://{GITHUB_OWNER}.github.io/{GITHUB_REPO}/)

支援手機加入主畫面、自選 ETF 切換、即時淨值折溢價、互動走勢圖與法人籌碼動向！
""".strip()
        send_message(chat_id, link_msg, reply_markup=get_main_keyboard())
    elif text.startswith('/dca') or '定期定額' in text or '試算' in text:
        parts = text.split()
        symbol = '0050'
        amt = 5000
        years = 3
        nums = re.findall(r'\d+', text)
        if len(nums) >= 1 and nums[0].startswith('00'):
            symbol = nums[0]
            if len(nums) >= 2: amt = int(nums[1])
            if len(nums) >= 3: years = int(nums[2])
        send_message(chat_id, calculate_dca(symbol, amt, years), reply_markup=get_main_keyboard())
    else:
        fallback_msg = f"""
💡 收到您的訊息：「{text}」

您可以直接用大白話跟我說：
▫️ 「*幫我加入 00878*」或「*加入 00919*」自動上架新標的
▫️ 「*0050*」或「*0056*」查最新市價、淨值與外資籌碼
▫️ 「*比較*」看市值型與高股息型差在哪
▫️ 點選下方快速按鈕！
""".strip()
        send_message(chat_id, fallback_msg, reply_markup=get_main_keyboard())

def run_polling():
    print("Telegram Bot Polling started with Natural Language ChatOps...")
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
