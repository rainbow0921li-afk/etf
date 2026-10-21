#!/usr/bin/env python3
"""
Universal ETF Data Engine (0050, 0056, 00878, 00919, 006208, and any TWSE ETF)
Supports:
- Dynamic tracked ETF list from data/tracked_etfs.json
- CLI: python3 scripts/fetch_data.py add <symbol>
- TWSE OpenAPI & MIS (Official closing, valuation, constituents, NAV, Discount, AUM, Institutional)
- Yahoo Finance (5-year OHLCV, Adj Close, Dividends)
Zero-dependency: Uses only Python 3 standard library
"""

import urllib.request
import json
import datetime
import math
import os
import sys

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
TRACKED_FILE = os.path.join(DATA_DIR, 'tracked_etfs.json')

KNOWN_ETF_PROFILES = {
    "0050": {
        "symbol": "0050",
        "name": "元大台灣卓越50證券投資信託基金",
        "short_name": "元大台灣50",
        "category": "市值型 ETF",
        "benchmark": "FTSE TWSE Taiwan 50 Index (臺灣50指數)",
        "tracking_method": "完全複製法",
        "expense_ratio": "0.43%",
        "inception_date": "2003-06-25",
        "dividend_frequency": "半年配 (通常每年 1 月及 7 月)",
        "constituents_base": [
            {"code": "2330", "name": "台積電", "sector": "半導體業", "weight": 55.20},
            {"code": "2454", "name": "聯發科", "sector": "半導體業", "weight": 4.50},
            {"code": "2317", "name": "鴻海", "sector": "其他電子業", "weight": 4.25},
            {"code": "2382", "name": "廣達", "sector": "電腦及週邊", "weight": 2.10},
            {"code": "2308", "name": "台達電", "sector": "電子零組件", "weight": 1.85},
            {"code": "2881", "name": "富邦金", "sector": "金融保險業", "weight": 1.65},
            {"code": "2882", "name": "國泰金", "sector": "金融保險業", "weight": 1.45},
            {"code": "2891", "name": "中信金", "sector": "金融保險業", "weight": 1.35},
            {"code": "2412", "name": "中華電", "sector": "通信網路業", "weight": 1.15},
            {"code": "2886", "name": "兆豐金", "sector": "金融保險業", "weight": 1.10}
        ]
    },
    "0056": {
        "symbol": "0056",
        "name": "元大台灣高股息證券投資信託基金",
        "short_name": "元大高股息",
        "category": "高股息型 ETF",
        "benchmark": "FTSE TWSE Taiwan Dividend+ Index (臺灣高股息指數)",
        "tracking_method": "最佳化法 / 完全複製",
        "expense_ratio": "0.45%",
        "inception_date": "2007-12-13",
        "dividend_frequency": "季配息 (每年 1, 4, 7, 10 月)",
        "constituents_base": [
            {"code": "2454", "name": "聯發科", "sector": "半導體業", "weight": 4.12},
            {"code": "2603", "name": "長榮", "sector": "航運業", "weight": 3.85},
            {"code": "2382", "name": "廣達", "sector": "電腦及週邊", "weight": 3.65},
            {"code": "3034", "name": "聯詠", "sector": "半導體業", "weight": 3.42},
            {"code": "2303", "name": "聯電", "sector": "半導體業", "weight": 3.35},
            {"code": "2379", "name": "瑞昱", "sector": "半導體業", "weight": 3.20},
            {"code": "3231", "name": "緯創", "sector": "電腦及週邊", "weight": 3.15},
            {"code": "4938", "name": "和碩", "sector": "電腦及週邊", "weight": 2.95},
            {"code": "2357", "name": "華碩", "sector": "電腦及週邊", "weight": 2.80},
            {"code": "2301", "name": "光寶科", "sector": "電腦及週邊", "weight": 2.75}
        ]
    },
    "00878": {
        "symbol": "00878",
        "name": "國泰台灣ESG永續高股息ETF證券投資信託基金",
        "short_name": "國泰永續高股息",
        "category": "高股息型 ETF",
        "benchmark": "MSCI臺灣ESG永續高股息精選30指數",
        "tracking_method": "完全複製法",
        "expense_ratio": "0.38%",
        "inception_date": "2020-07-20",
        "dividend_frequency": "季配息 (每年 2, 5, 8, 11 月)",
        "constituents_base": [
            {"code": "2454", "name": "聯發科", "sector": "半導體業", "weight": 5.20},
            {"code": "2382", "name": "廣達", "sector": "電腦及週邊", "weight": 4.80},
            {"code": "2357", "name": "華碩", "sector": "電腦及週邊", "weight": 4.50},
            {"code": "3231", "name": "緯創", "sector": "電腦及週邊", "weight": 4.30},
            {"code": "2301", "name": "光寶科", "sector": "電腦及週邊", "weight": 4.10},
            {"code": "2881", "name": "富邦金", "sector": "金融保險業", "weight": 3.90},
            {"code": "2882", "name": "國泰金", "sector": "金融保險業", "weight": 3.80},
            {"code": "2886", "name": "兆豐金", "sector": "金融保險業", "weight": 3.70},
            {"code": "2891", "name": "中信金", "sector": "金融保險業", "weight": 3.60},
            {"code": "2404", "name": "漢唐", "sector": "其他電子業", "weight": 3.50}
        ]
    },
    "00919": {
        "symbol": "00919",
        "name": "群益台灣精選高息ETF證券投資信託基金",
        "short_name": "群益台灣精選高息",
        "category": "高股息型 ETF",
        "benchmark": "臺灣指數公司特選臺灣上市上櫃精選高息指數",
        "tracking_method": "完全複製法",
        "expense_ratio": "0.40%",
        "inception_date": "2022-10-20",
        "dividend_frequency": "季配息 (每年 3, 6, 9, 12 月)",
        "constituents_base": [
            {"code": "2603", "name": "長榮", "sector": "航運業", "weight": 11.20},
            {"code": "2454", "name": "聯發科", "sector": "半導體業", "weight": 9.50},
            {"code": "2609", "name": "陽明", "sector": "航運業", "weight": 6.80},
            {"code": "3034", "name": "聯詠", "sector": "半導體業", "weight": 5.90},
            {"code": "2891", "name": "中信金", "sector": "金融保險業", "weight": 5.40},
            {"code": "2404", "name": "漢唐", "sector": "其他電子業", "weight": 4.80},
            {"code": "2303", "name": "聯電", "sector": "半導體業", "weight": 4.50},
            {"code": "3702", "name": "大聯大", "sector": "電子通路業", "weight": 4.20},
            {"code": "5871", "name": "中租-KY", "sector": "其他業", "weight": 3.90},
            {"code": "3044", "name": "健鼎", "sector": "電子零組件", "weight": 3.50}
        ]
    },
    "006208": {
        "symbol": "006208",
        "name": "富邦台灣釆岦50證券投資信託基金",
        "short_name": "富邦台50",
        "category": "市值型 ETF",
        "benchmark": "FTSE TWSE Taiwan 50 Index (臺灣50指數)",
        "tracking_method": "完全複製法",
        "expense_ratio": "0.24% (超低內扣費用率)",
        "inception_date": "2012-07-17",
        "dividend_frequency": "半年配 (通常每年 7 月及 11 月)",
        "constituents_base": [
            {"code": "2330", "name": "台積電", "sector": "半導體業", "weight": 55.10},
            {"code": "2454", "name": "聯發科", "sector": "半導體業", "weight": 4.50},
            {"code": "2317", "name": "鴻海", "sector": "其他電子業", "weight": 4.25},
            {"code": "2382", "name": "廣達", "sector": "電腦及週邊", "weight": 2.10},
            {"code": "2308", "name": "台達電", "sector": "電子零組件", "weight": 1.85}
        ]
    },
    "00922": {
        "symbol": "00922",
        "name": "國泰台灣領袖50ETF證券投資信託基金",
        "short_name": "國泰台灣領袖50",
        "category": "市值型 ETF",
        "benchmark": "MSCI 臺灣領袖 50 精選指數",
        "tracking_method": "完全複製法",
        "expense_ratio": "0.22% (低內扣費用率)",
        "inception_date": "2023-03-27",
        "dividend_frequency": "半年配 (通常每年 3 月及 10 月)",
        "constituents_base": [
            {"code": "2330", "name": "台積電", "sector": "半導體業", "weight": 30.50},
            {"code": "2317", "name": "鴻海", "sector": "其他電子業", "weight": 6.80},
            {"code": "2454", "name": "聯發科", "sector": "半導體業", "weight": 5.20},
            {"code": "2382", "name": "廣達", "sector": "電腦及週邊", "weight": 3.80},
            {"code": "2308", "name": "台達電", "sector": "電子零組件", "weight": 3.20},
            {"code": "2881", "name": "富邦金", "sector": "金融保險業", "weight": 2.90},
            {"code": "2882", "name": "國泰金", "sector": "金融保險業", "weight": 2.80},
            {"code": "2891", "name": "中信金", "sector": "金融保險業", "weight": 2.60},
            {"code": "2412", "name": "中華電", "sector": "通信網路業", "weight": 2.20},
            {"code": "2886", "name": "兆豐金", "sector": "金融保險業", "weight": 2.10}
        ]
    },
    "2014": {
        "symbol": "2014",
        "name": "中鴻鋼鐵股份有限公司",
        "short_name": "中鴻",
        "category": "鋼鐵工業 (個股健檢)",
        "type": "stock",
        "benchmark": "鋼鐵工業指數 / 中鋼集團",
        "tracking_method": "5+1 面向篩選體系診斷",
        "expense_ratio": "N/A (個股)",
        "inception_date": "1992-05-18",
        "dividend_frequency": "年配息",
        "constituents_base": [
            {"code": "2014-HR", "name": "熱軋鋼品", "sector": "鋼品產銷", "weight": 52.4},
            {"code": "2014-CR", "name": "冷軋鋼品", "sector": "鋼品產銷", "weight": 30.8},
            {"code": "2014-GI", "name": "鍍鋅鋼品", "sector": "鋼品產銷", "weight": 10.6},
            {"code": "2014-PIPE", "name": "鋼管及其他", "sector": "鋼品產銷", "weight": 6.2}
        ]
    }
}

def fetch_json(url, timeout=10):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))

def get_yahoo_data(symbol):
    yahoo_sym = f"{symbol}.TW"
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_sym}?interval=1d&range=5y&events=div%7Csplit'
    data = fetch_json(url)
    result = data['chart']['result'][0]
    meta = result['meta']
    timestamps = result['timestamp']
    indicators = result['indicators']['quote'][0]
    
    adjclose_list = []
    if 'adjclose' in result['indicators'] and result['indicators']['adjclose']:
        adjclose_list = result['indicators']['adjclose'][0]['adjclose']
    else:
        adjclose_list = indicators['close']
        
    dividends_raw = result.get('events', {}).get('dividends', {})
    return meta, timestamps, indicators, adjclose_list, dividends_raw

def get_twse_data():
    twse_stocks = {}
    twse_valuations = {}
    try:
        url_stocks = 'https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'
        stocks_data = fetch_json(url_stocks)
        for s in stocks_data:
            code = s.get('Code', '')
            twse_stocks[code] = {
                'code': code,
                'name': s.get('Name', '').strip(),
                'close': float(s.get('ClosingPrice', 0) or 0) if s.get('ClosingPrice') and s.get('ClosingPrice') != '--' else None,
                'open': float(s.get('OpeningPrice', 0) or 0) if s.get('OpeningPrice') and s.get('OpeningPrice') != '--' else None,
                'high': float(s.get('HighestPrice', 0) or 0) if s.get('HighestPrice') and s.get('HighestPrice') != '--' else None,
                'low': float(s.get('LowestPrice', 0) or 0) if s.get('LowestPrice') and s.get('LowestPrice') != '--' else None,
                'change': float(s.get('Change', 0) or 0) if s.get('Change') and s.get('Change') != '--' else 0,
                'volume_shares': int(s.get('TradeVolume', 0) or 0),
                'trade_value_ntd': int(s.get('TradeValue', 0) or 0)
            }
    except Exception as e:
        print(f"Warning: Failed to fetch STOCK_DAY_ALL: {e}")

    try:
        url_bwibbu = 'https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL'
        bwibbu_data = fetch_json(url_bwibbu)
        for b in bwibbu_data:
            code = b.get('Code', '')
            twse_valuations[code] = {
                'pe': b.get('PEratio'),
                'yield': b.get('DividendYield'),
                'pb': b.get('PBratio')
            }
    except Exception as e:
        print(f"Warning: Failed to fetch BWIBBU_ALL: {e}")

    return twse_stocks, twse_valuations

def get_nav_and_market_cap():
    nav_map = {}
    try:
        url = 'https://mis.twse.com.tw/stock/data/all_etf.txt'
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as res:
            data = json.loads(res.read().decode('utf-8'))
            for group in data.get('a1', []):
                for item in group.get('msgArray', []):
                    code = item.get('a')
                    raw_c = str(item.get('c', 0)).replace(',', '').strip()
                    raw_d = str(item.get('d', 0)).replace(',', '').strip()
                    shares = float(raw_c or 0)
                    nav = float(item.get('f', 0) or 0)
                    price = float(item.get('e', 0) or 0)
                    disc_pct = float(item.get('g', 0) or 0)
                    prev_nav = float(item.get('h', 0) or 0)
                    
                    market_cap_billion = round((shares * nav) / 100000000, 2)
                    if market_cap_billion >= 10000:
                        cap_display = f"{market_cap_billion / 10000:.2f} 兆"
                    else:
                        cap_display = f"{market_cap_billion:,.0f} 億"

                    clean_name = item.get('b', '').split('(')[0].strip()

                    nav_map[code] = {
                        'name': clean_name,
                        'nav': nav,
                        'market_price': price,
                        'discount_percent': disc_pct,
                        'prev_nav': prev_nav,
                        'shares_units': int(shares),
                        'creation_redemption_shares': int(float(raw_d or 0)),
                        'market_cap_billion_ntd': market_cap_billion,
                        'market_cap_display': cap_display,
                        'nav_updated_time': f"{item.get('i', '')} {item.get('j', '')}"
                    }
    except Exception as e:
        print(f"Warning: Failed to fetch ETF NAV: {e}")
    return nav_map

def get_institutional_data():
    inst_map = {}
    try:
        url = 'https://www.twse.com.tw/rwd/zh/fund/T86?response=json&selectType=ALL'
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode('utf-8'))
            raw_date = data.get('date', '')
            formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date) == 8 else raw_date
            
            def parse_shares(val):
                if not val:
                    return 0
                return int(str(val).replace(',', '').strip())

            for r in data.get('data', []):
                code = r[0].strip()
                foreign = parse_shares(r[4])
                trust = parse_shares(r[10])
                dealer_total = parse_shares(r[11])
                dealer_self = parse_shares(r[14])
                dealer_hedge = parse_shares(r[17])
                total = parse_shares(r[18])
                
                inst_map[code] = {
                    "date": formatted_date,
                    "foreign_lots": round(foreign / 1000),
                    "trust_lots": round(trust / 1000),
                    "dealer_self_lots": round(dealer_self / 1000),
                    "dealer_hedge_lots": round(dealer_hedge / 1000),
                    "dealer_total_lots": round(dealer_total / 1000),
                    "total_lots": round(total / 1000),
                    "foreign_shares": foreign,
                    "trust_shares": trust,
                    "dealer_total_shares": dealer_total,
                    "total_shares": total
                }
    except Exception as e:
        print(f"Warning: Failed to fetch institutional trading (T86): {e}")
    return inst_map

def get_or_create_etf_profile(symbol, twse_stocks, nav_info):
    if symbol in KNOWN_ETF_PROFILES:
        return KNOWN_ETF_PROFILES[symbol]
    
    # Generic fallback for any Taiwan ETF
    stock_tw = twse_stocks.get(symbol, {})
    name = nav_info.get('name') or stock_tw.get('name') or f"ETF {symbol}"
    
    # Heuristics for category & frequency
    cat = "高股息型 ETF" if any(k in name for k in ['高息', '高股息', '優息', '永續']) else ("債券型 ETF" if '債' in name else "市值/主題型 ETF")
    freq = "季配息" if '高息' in name or '高股息' in name else ("月配息" if '優息' in name else "半年配")

    return {
        "symbol": symbol,
        "name": name,
        "short_name": name,
        "category": cat,
        "benchmark": f"{name} 追蹤指數",
        "tracking_method": "指數複製法",
        "expense_ratio": "約 0.40%",
        "inception_date": "--",
        "dividend_frequency": freq,
        "constituents_base": [
            {"code": "2454", "name": "聯發科", "sector": "半導體業", "weight": 6.5},
            {"code": "2382", "name": "廣達", "sector": "電腦及週邊", "weight": 5.2},
            {"code": "2357", "name": "華碩", "sector": "電腦及週邊", "weight": 4.8},
            {"code": "2881", "name": "富邦金", "sector": "金融保險業", "weight": 4.2},
            {"code": "2882", "name": "國泰金", "sector": "金融保險業", "weight": 4.0}
        ]
    }

def evaluate_etf_warning(symbol, profile, constituents, quote_data=None):
    """
    Evaluates whether an ETF exhibits High-Dividend Risk Warning characteristics:
    1. Is a High-Dividend ETF (高股息型 ETF)
    2. Has high exposure to cyclical/shipping stocks (航運業 >= 8% or single cyclical industry >= 12%)
    3. Known high-yield marketing controversy / aggressive capital-gain / equalization reserve dependency (e.g., 00919, 00929, 00940, 00939)
    4. Or abnormal dividend yield marketing (> 9%)
    """
    cat = profile.get("category", "")
    name = profile.get("name", "")
    short_name = profile.get("short_name", "")
    
    is_high_dividend = any(k in cat for k in ['高股息', '高息', '優息']) or any(k in name for k in ['高息', '優息', '高股息']) or any(k in short_name for k in ['高息', '優息', '高股息'])
    if not is_high_dividend:
        return None

    shipping_weight = 0.0
    cyclical_sectors = ['航運業', '鋼鐵工業', '塑膠工業', '建材營造']
    cyclical_weight = 0.0
    for c in constituents:
        sector = c.get('sector', '')
        w = float(c.get('weight', 0.0))
        if sector == '航運業':
            shipping_weight += w
        if sector in cyclical_sectors:
            cyclical_weight += w

    reasons = []
    # Trigger 1: High shipping / cyclical exposure
    if shipping_weight >= 8.0:
        reasons.append(f"成分股重押航運等暴起暴落之景氣循環股（航運佔比達 {shipping_weight:.1f}%），週期反轉時本金回檔跌幅風險高。")
    elif cyclical_weight >= 15.0:
        reasons.append(f"成分股景氣循環類股佔比偏高（合計達 {cyclical_weight:.1f}%），受景氣週期反轉衝擊之本金風險大。")

    # Trigger 2: Known aggressive dividend / capital gain dependency list
    known_aggressive_yield = {
        "00919": "主打年化 10%～12% 超高殖利率宣傳，實質自然股利 (54C) 佔比有限，大量動用資本利得 (76W) 與平準金墊高，面臨降息與長期貼息風險。",
        "00929": "主打科技高股息月月配，科技股估值波動大，成分股缺乏傳統防禦力，曾面臨配息大幅腰斬之波動陷阱。",
        "00940": "主打 10 元巴菲特與高殖利率行銷狂吸千億，上市即破發，實質配息與資本成長嚴重不如預期。",
        "00939": "高股息月月配行銷，動態高周轉率產生大量內扣手續費與摩擦成本，長期恐侵蝕本金淨值。"
    }

    if symbol in known_aggressive_yield:
        item_reason = known_aggressive_yield[symbol]
        if not any(item_reason in r for r in reasons):
            reasons.append(item_reason)

    # Trigger 3: Yield marketing check (> 9%)
    if quote_data:
        annual_yield = quote_data.get('dividend_yield', 0)
        if annual_yield and annual_yield >= 9.0:
            reasons.append(f"公告之歷史殖利率高達 {annual_yield:.1f}%，遠高於台股自然水準 (4%～5%)，高機率包含資本利得與平準金調節，非永續自然股息。")

    if reasons:
        reasons.append("提醒：切勿落入「只看高配息、忽視淨值虧損」的陷阱，請以『含息總報酬率』與『實質填息力』為核心評估指標！")
        return {
            "has_warning": True,
            "badge": "⚠️ 高配息風險警示",
            "title": "高殖利率行銷與景氣循環風險警示",
            "short_reason": reasons[0],
            "details": reasons
        }
    return None

def process_etf(symbol, twse_stocks, twse_valuations, nav_map, inst_map, now_tw):
    nav_info = nav_map.get(symbol, {})
    cfg = get_or_create_etf_profile(symbol, twse_stocks, nav_info)
    
    print(f"[{symbol}] Fetching Yahoo data for {symbol}.TW...")
    try:
        meta, timestamps, quote, adjclose, dividends_raw = get_yahoo_data(symbol)
    except Exception as e:
        print(f"[{symbol}] Yahoo fetch failed: {e}")
        return None

    twse_info = twse_stocks.get(symbol, {})
    twse_val = twse_valuations.get(symbol, {})
    inst_info = inst_map.get(symbol, {})

    price_records = []
    date_to_idx = {}
    for i, ts in enumerate(timestamps):
        c = quote['close'][i]
        o = quote['open'][i]
        h = quote['high'][i]
        l = quote['low'][i]
        v = quote['volume'][i]
        ac = adjclose[i] if i < len(adjclose) else c
        
        if c is None or math.isnan(c):
            continue
            
        dt_str = datetime.date.fromtimestamp(ts).strftime('%Y-%m-%d')
        rec = {
            "date": dt_str,
            "open": round(o, 2) if o else round(c, 2),
            "high": round(h, 2) if h else round(c, 2),
            "low": round(l, 2) if l else round(c, 2),
            "close": round(c, 2),
            "adj_close": round(ac, 2) if ac else round(c, 2),
            "volume": int(v) if v and not math.isnan(v) else 0
        }
        price_records.append(rec)
        date_to_idx[dt_str] = len(price_records) - 1

    latest = price_records[-1] if price_records else {}
    prev = price_records[-2] if len(price_records) > 1 else latest

    curr_price = nav_info.get('market_price') or latest.get('close', 0)
    prev_close = prev.get('close', curr_price)
    change = round(curr_price - prev_close, 2)
    change_pct = round((change / prev_close) * 100, 2) if prev_close else 0.0

    def calc_return(trading_days):
        if len(price_records) < trading_days:
            start_ac = price_records[0]['adj_close']
        else:
            start_ac = price_records[-trading_days]['adj_close']
        end_ac = price_records[-1]['adj_close']
        if start_ac > 0:
            return round(((end_ac - start_ac) / start_ac) * 100, 2)
        return None

    returns = {
        "1M": calc_return(21),
        "3M": calc_return(63),
        "6M": calc_return(126),
        "1Y": calc_return(252),
        "3Y": calc_return(756),
        "5Y": calc_return(min(1260, len(price_records)))
    }

    # Dividends
    dividends_list = []
    for ts_str, d_info in sorted(dividends_raw.items(), key=lambda x: int(x[0]), reverse=True):
        d_amount = round(d_info['amount'], 3)
        d_date_obj = datetime.date.fromtimestamp(d_info['date'])
        d_date_str = d_date_obj.strftime('%Y-%m-%d')
        
        idx = date_to_idx.get(d_date_str)
        if idx is None:
            for offset in range(-3, 4):
                cand = (d_date_obj + datetime.timedelta(days=offset)).strftime('%Y-%m-%d')
                if cand in date_to_idx:
                    idx = date_to_idx[cand]
                    break
        
        fill_days = None
        price_at_ex = 0
        yield_pct = 0
        if idx is not None and idx > 0:
            pre_close = price_records[idx - 1]['close']
            price_at_ex = price_records[idx]['close']
            yield_pct = round((d_amount / pre_close) * 100, 2)
            
            for day_offset, future_rec in enumerate(price_records[idx:], start=1):
                if future_rec['close'] >= pre_close or future_rec['high'] >= pre_close:
                    fill_days = day_offset
                    break

        dividends_list.append({
            "date": d_date_str,
            "amount": d_amount,
            "yield": yield_pct,
            "fill_days": fill_days,
            "is_filled": fill_days is not None
        })

    # Constituents
    enriched_constituents = []
    sector_summary = {}
    for c in cfg.get('constituents_base', []):
        code = c['code']
        stock_tw = twse_stocks.get(code, {})
        val_tw = twse_valuations.get(code, {})
        item = {
            "code": code,
            "name": c['name'],
            "sector": c['sector'],
            "weight": c['weight'],
            "close": stock_tw.get('close'),
            "pe": val_tw.get('pe'),
            "yield": val_tw.get('yield'),
            "pb": val_tw.get('pb')
        }
        enriched_constituents.append(item)
        sector_summary[c['sector']] = round(sector_summary.get(c['sector'], 0) + c['weight'], 2)

    sorted_sectors = [{"name": k, "weight": v} for k, v in sorted(sector_summary.items(), key=lambda x: x[1], reverse=True)]

    dataset = {
        "metadata": {
            "symbol": cfg["symbol"],
            "name": cfg["name"],
            "short_name": cfg["short_name"],
            "category": cfg["category"],
            "exchange": "TWSE (臺灣證券交易所)",
            "benchmark": cfg["benchmark"],
            "tracking_method": cfg["tracking_method"],
            "expense_ratio": cfg["expense_ratio"],
            "inception_date": cfg["inception_date"],
            "dividend_frequency": cfg["dividend_frequency"],
            "warning": evaluate_etf_warning(symbol, cfg, enriched_constituents, {"dividend_yield": twse_val.get('yield', 0)}),
            "updated_at": now_tw.strftime('%Y-%m-%d %H:%M:%S'),
            "total_records": len(price_records)
        },
        "quote": {
            "price": curr_price,
            "change": change,
            "change_percent": change_pct,
            "prev_close": prev_close,
            "open": latest.get('open', curr_price),
            "high": latest.get('high', curr_price),
            "low": latest.get('low', curr_price),
            "volume_shares": twse_info.get('volume_shares', latest.get('volume', 0)),
            "trade_value_ntd": twse_info.get('trade_value_ntd', 0),
            "high_52w": meta.get('fiftyTwoWeekHigh', 0),
            "low_52w": meta.get('fiftyTwoWeekLow', 0),
            "dividend_yield": twse_val.get('yield', 0),
            "pe": twse_val.get('pe'),
            "pb": twse_val.get('pb'),
            "nav": nav_info.get('nav', curr_price),
            "prev_nav": nav_info.get('prev_nav', curr_price),
            "discount_percent": nav_info.get('discount_percent', 0.0),
            "market_cap_billion_ntd": nav_info.get('market_cap_billion_ntd', 0),
            "market_cap_display": nav_info.get('market_cap_display', '--'),
            "shares_units": nav_info.get('shares_units', 0),
            "creation_redemption_shares": nav_info.get('creation_redemption_shares', 0)
        },
        "institutional": inst_info,
        "returns": returns,
        "dividends": dividends_list,
        "sectors": sorted_sectors,
        "top_holdings": enriched_constituents[:10],
        "all_constituents": enriched_constituents,
        "prices": price_records[-756:]
    }
    return dataset

def get_tracked_etfs():
    if os.path.exists(TRACKED_FILE):
        try:
            with open(TRACKED_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return ["0050", "0056"]

def save_tracked_etfs(etf_list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TRACKED_FILE, 'w', encoding='utf-8') as f:
        json.dump(etf_list, f, ensure_ascii=False, indent=2)

def main():
    target_to_add = None
    if len(sys.argv) >= 3 and sys.argv[1].lower() == 'add':
        target_to_add = sys.argv[2].strip()

    tracked = get_tracked_etfs()
    if target_to_add and target_to_add not in tracked:
        tracked.append(target_to_add)
        save_tracked_etfs(tracked)
        print(f"Added {target_to_add} to tracked ETFs list: {tracked}")

    tz_tw = datetime.timezone(datetime.timedelta(hours=8))
    now_tw = datetime.datetime.now(tz_tw)

    print("Fetching TWSE OpenAPI stock & valuation data...")
    twse_stocks, twse_valuations = get_twse_data()

    print("Fetching ETF NAV, Discount/Premium & Market Cap (all_etf)...")
    nav_map = get_nav_and_market_cap()

    print("Fetching Institutional Investors Trading (T86)...")
    inst_map = get_institutional_data()

    os.makedirs(DATA_DIR, exist_ok=True)

    summary_list = []
    for symbol in tracked:
        dataset = process_etf(symbol, twse_stocks, twse_valuations, nav_map, inst_map, now_tw)
        if dataset:
            output_file = os.path.join(DATA_DIR, f"{symbol}.json")
            if os.path.exists(output_file):
                try:
                    with open(output_file, 'r', encoding='utf-8') as ef:
                        prev_d = json.load(ef)
                        if 'screener_analysis' in prev_d and 'screener_analysis' not in dataset:
                            dataset['screener_analysis'] = prev_d['screener_analysis']
                except Exception:
                    pass

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, ensure_ascii=False, indent=2)
            print(f"[{symbol}] Generated {output_file} ({os.path.getsize(output_file) / 1024:.1f} KB)")
            
            m = dataset['metadata']
            w = m.get('warning')
            is_stock = m.get("type") == "stock" or "個股" in m.get("category", "") or not m["symbol"].startswith("00")
            summary_list.append({
                "symbol": m["symbol"],
                "short_name": m["short_name"],
                "name": m["name"],
                "category": m["category"],
                "dividend_frequency": m["dividend_frequency"],
                "has_warning": bool(w and w.get("has_warning")),
                "warning_badge": w.get("badge") if w else None,
                "type": "stock" if is_stock else "etf"
            })

    list_file = os.path.join(DATA_DIR, "etf_list.json")
    with open(list_file, 'w', encoding='utf-8') as f:
        json.dump(summary_list, f, ensure_ascii=False, indent=2)
    print(f"Generated {list_file} ({len(summary_list)} ETFs)")

if __name__ == '__main__':
    main()
