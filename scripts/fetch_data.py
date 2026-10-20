#!/usr/bin/env python3
"""
Fetch 0050 ETF Data
Sources:
- Yahoo Finance (Historical OHLCV, Adj Close, Dividends, Quote)
- TWSE OpenAPI (Official closing, valuation, constituent metrics)
Zero-dependency: Uses only Python 3 standard library (urllib, json, datetime)
"""

import urllib.request
import json
import datetime
import math
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def fetch_json(url, timeout=10):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))

def get_yahoo_data():
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/0050.TW?interval=1d&range=5y&events=div%7Csplit'
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
    twse_info = {}
    twse_constituents = {}
    try:
        url_stocks = 'https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'
        stocks_data = fetch_json(url_stocks)
        for s in stocks_data:
            code = s.get('Code', '')
            if code == '0050':
                twse_info['close'] = float(s.get('ClosingPrice', 0) or 0)
                twse_info['open'] = float(s.get('OpeningPrice', 0) or 0)
                twse_info['high'] = float(s.get('HighestPrice', 0) or 0)
                twse_info['low'] = float(s.get('LowestPrice', 0) or 0)
                twse_info['change'] = float(s.get('Change', 0) or 0)
                twse_info['trade_volume_shares'] = int(s.get('TradeVolume', 0) or 0)
                twse_info['trade_value_ntd'] = int(s.get('TradeValue', 0) or 0)
                twse_info['transactions'] = int(s.get('Transaction', 0) or 0)
                twse_info['date'] = s.get('Date', '')
            twse_constituents[code] = {
                'code': code,
                'name': s.get('Name', ''),
                'close': float(s.get('ClosingPrice', 0) or 0) if s.get('ClosingPrice') and s.get('ClosingPrice') != '--' else None,
                'change': s.get('Change', '0')
            }
    except Exception as e:
        print(f"Warning: Failed to fetch STOCK_DAY_ALL: {e}")

    try:
        url_bwibbu = 'https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL'
        bwibbu_data = fetch_json(url_bwibbu)
        for b in bwibbu_data:
            code = b.get('Code', '')
            if code == '0050':
                twse_info['dividend_yield'] = float(b.get('DividendYield', 0) or 0)
                twse_info['pe'] = float(b.get('PEratio', 0) or 0) if b.get('PEratio') and b.get('PEratio') != '-' else None
                twse_info['pb'] = float(b.get('PBratio', 0) or 0) if b.get('PBratio') and b.get('PBratio') != '-' else None
            if code in twse_constituents:
                twse_constituents[code]['pe'] = b.get('PEratio')
                twse_constituents[code]['yield'] = b.get('DividendYield')
                twse_constituents[code]['pb'] = b.get('PBratio')
    except Exception as e:
        print(f"Warning: Failed to fetch BWIBBU_ALL: {e}")

    return twse_info, twse_constituents

# Benchmark 50 Constituents of 0050 (Taiwan 50 Index)
CONSTITUENTS_BASE = [
    {"code": "2330", "name": "台積電", "sector": "半導體業", "weight": 55.20},
    {"code": "2454", "name": "聯發科", "sector": "半導體業", "weight": 4.50},
    {"code": "2317", "name": "鴻海", "sector": "其他電子業", "weight": 4.25},
    {"code": "2382", "name": "廣達", "sector": "電腦及週邊", "weight": 2.10},
    {"code": "2308", "name": "台達電", "sector": "電子零組件", "weight": 1.85},
    {"code": "2881", "name": "富邦金", "sector": "金融保險業", "weight": 1.65},
    {"code": "2882", "name": "國泰金", "sector": "金融保險業", "weight": 1.45},
    {"code": "2891", "name": "中信金", "sector": "金融保險業", "weight": 1.35},
    {"code": "2412", "name": "中華電", "sector": "通信網路業", "weight": 1.15},
    {"code": "2886", "name": "兆豐金", "sector": "金融保險業", "weight": 1.10},
    {"code": "3711", "name": "日月光投控", "sector": "半導體業", "weight": 1.05},
    {"code": "2884", "name": "玉山金", "sector": "金融保險業", "weight": 0.95},
    {"code": "3231", "name": "緯創", "sector": "電腦及週邊", "weight": 0.88},
    {"code": "2603", "name": "長榮", "sector": "航運業", "weight": 0.85},
    {"code": "2303", "name": "聯電", "sector": "半導體業", "weight": 0.82},
    {"code": "2892", "name": "第一金", "sector": "金融保險業", "weight": 0.78},
    {"code": "2885", "name": "元大金", "sector": "金融保險業", "weight": 0.75},
    {"code": "2357", "name": "華碩", "sector": "電腦及週邊", "weight": 0.72},
    {"code": "3008", "name": "大立光", "sector": "光電業", "weight": 0.68},
    {"code": "2880", "name": "華南金", "sector": "金融保險業", "weight": 0.65},
    {"code": "2887", "name": "台新金", "sector": "金融保險業", "weight": 0.62},
    {"code": "2890", "name": "永豐金", "sector": "金融保險業", "weight": 0.60},
    {"code": "2379", "name": "瑞昱", "sector": "半導體業", "weight": 0.58},
    {"code": "6669", "name": "緯穎", "sector": "電腦及週邊", "weight": 0.56},
    {"code": "1216", "name": "統一", "sector": "食品工業", "weight": 0.55},
    {"code": "2345", "name": "智邦", "sector": "通信網路業", "weight": 0.52},
    {"code": "2327", "name": "國巨", "sector": "電子零組件", "weight": 0.50},
    {"code": "2883", "name": "開發金", "sector": "金融保險業", "weight": 0.48},
    {"code": "1301", "name": "台塑", "sector": "塑膠工業", "weight": 0.46},
    {"code": "1303", "name": "南亞", "sector": "塑膠工業", "weight": 0.45},
    {"code": "3037", "name": "欣興", "sector": "電子零組件", "weight": 0.43},
    {"code": "2002", "name": "中鋼", "sector": "鋼鐵工業", "weight": 0.42},
    {"code": "3661", "name": "世芯-KY", "sector": "半導體業", "weight": 0.40},
    {"code": "5880", "name": "合庫金", "sector": "金融保險業", "weight": 0.38},
    {"code": "2912", "name": "統一超", "sector": "貿易百貨業", "weight": 0.36},
    {"code": "3034", "name": "聯詠", "sector": "半導體業", "weight": 0.35},
    {"code": "4938", "name": "和碩", "sector": "電腦及週邊", "weight": 0.33},
    {"code": "2609", "name": "陽明", "sector": "航運業", "weight": 0.32},
    {"code": "2615", "name": "萬海", "sector": "航運業", "weight": 0.30},
    {"code": "2801", "name": "彰銀", "sector": "金融保險業", "weight": 0.29},
    {"code": "1326", "name": "台化", "sector": "塑膠工業", "weight": 0.28},
    {"code": "6505", "name": "台塑化", "sector": "油電燃氣業", "weight": 0.27},
    {"code": "4919", "name": "新唐", "sector": "半導體業", "weight": 0.25},
    {"code": "2395", "name": "研華", "sector": "電腦及週邊", "weight": 0.24},
    {"code": "1101", "name": "台泥", "sector": "水泥工業", "weight": 0.23},
    {"code": "5871", "name": "中租-KY", "sector": "其他業", "weight": 0.22},
    {"code": "2301", "name": "光寶科", "sector": "電腦及週邊", "weight": 0.21},
    {"code": "3443", "name": "創意", "sector": "半導體業", "weight": 0.20},
    {"code": "2888", "name": "新光金", "sector": "金融保險業", "weight": 0.19},
    {"code": "2207", "name": "和泰車", "sector": "汽車工業", "weight": 0.18}
]

def build_dataset():
    print("Fetching data from Yahoo Finance...")
    meta, timestamps, quote, adjclose, dividends_raw = get_yahoo_data()
    print("Fetching data from TWSE OpenAPI...")
    twse_info, twse_constituents = get_twse_data()

    # Process Price Series
    price_records = []
    date_to_idx = {}
    for i, ts in enumerate(timestamps):
        c = quote['close'][i]
        o = quote['open'][i]
        h = quote['high'][i]
        l = quote['low'][i]
        v = quote['volume'][i]
        ac = adjclose[i] if i < len(adjclose) else c
        
        # Filter nulls (holidays/early close)
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

    # Current Price & Changes
    curr_price = latest.get('close', 0)
    prev_close = prev.get('close', curr_price)
    change = round(curr_price - prev_close, 2)
    change_pct = round((change / prev_close) * 100, 2) if prev_close else 0.0

    # Calculate Multi-period Total Returns (using adj_close for total return)
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

    # Process Dividend Records and calculate fill-in days
    dividends_list = []
    for ts_str, d_info in sorted(dividends_raw.items(), key=lambda x: int(x[0]), reverse=True):
        d_amount = round(d_info['amount'], 3)
        d_date_obj = datetime.date.fromtimestamp(d_info['date'])
        d_date_str = d_date_obj.strftime('%Y-%m-%d')
        
        # Find index in price_records
        idx = date_to_idx.get(d_date_str)
        if idx is None:
            # find closest trading day
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
            
            # Count days to fill dividend (price >= pre_close)
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

    # Enrich Constituents
    enriched_constituents = []
    sector_summary = {}
    for c in CONSTITUENTS_BASE:
        code = c['code']
        twse_c = twse_constituents.get(code, {})
        item = {
            "code": code,
            "name": c['name'],
            "sector": c['sector'],
            "weight": c['weight'],
            "close": twse_c.get('close'),
            "pe": twse_c.get('pe'),
            "yield": twse_c.get('yield'),
            "pb": twse_c.get('pb')
        }
        enriched_constituents.append(item)
        sector_summary[c['sector']] = round(sector_summary.get(c['sector'], 0) + c['weight'], 2)

    # Sort sector summary
    sorted_sectors = [{"name": k, "weight": v} for k, v in sorted(sector_summary.items(), key=lambda x: x[1], reverse=True)]

    # Taiwan Time (UTC+8)
    tz_tw = datetime.timezone(datetime.timedelta(hours=8))
    now_tw = datetime.datetime.now(tz_tw)

    # Final Dataset
    dataset = {
        "metadata": {
            "symbol": "0050",
            "name": "元大台灣卓越50證券投資信託基金",
            "short_name": "元大台灣50",
            "exchange": "TWSE (臺灣證券交易所)",
            "benchmark": "FTSE TWSE Taiwan 50 Index (臺灣50指數)",
            "tracking_method": "完全複製法 (Full Replication)",
            "expense_ratio": "0.43% (經理費 0.32% + 保管費 0.035% + 相關費用)",
            "inception_date": "2003-06-25",
            "dividend_frequency": "半年配 (通常每年 1 月及 7 月)",
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
            "volume_shares": twse_info.get('trade_volume_shares', latest.get('volume', 0)),
            "trade_value_ntd": twse_info.get('trade_value_ntd', 0),
            "high_52w": meta.get('fiftyTwoWeekHigh', 0),
            "low_52w": meta.get('fiftyTwoWeekLow', 0),
            "dividend_yield": twse_info.get('dividend_yield', 0),
            "pe": twse_info.get('pe'),
            "pb": twse_info.get('pb')
        },
        "returns": returns,
        "dividends": dividends_list,
        "sectors": sorted_sectors,
        "top_holdings": enriched_constituents[:10],
        "all_constituents": enriched_constituents,
        "prices": price_records[-756:]  # Keep last 3 years of daily OHLCV (fast load ~150KB)
    }

    return dataset

if __name__ == '__main__':
    data = build_dataset()
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', '0050.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Success! Generated {output_path} (Size: {os.path.getsize(output_path) / 1024:.1f} KB)")
