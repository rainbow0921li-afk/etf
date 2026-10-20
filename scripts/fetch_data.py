#!/usr/bin/env python3
"""
Fetch ETF Data (0050 and 0056)
Sources:
- Yahoo Finance (Historical OHLCV, Adj Close, Dividends, Quote)
- TWSE OpenAPI & MIS (Official closing, valuation, constituent metrics, NAV, Discount, AUM, Institutional Trading)
Zero-dependency: Uses only Python 3 standard library
"""

import urllib.request
import json
import datetime
import math
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

ETF_CONFIGS = {
    "0050": {
        "symbol": "0050",
        "yahoo_symbol": "0050.TW",
        "name": "元大台灣卓越50證券投資信託基金",
        "short_name": "元大台灣50",
        "category": "市值型 ETF",
        "exchange": "TWSE (臺灣證券交易所)",
        "benchmark": "FTSE TWSE Taiwan 50 Index (臺灣50指數)",
        "tracking_method": "完全複製法 (Full Replication)",
        "expense_ratio": "0.43% (經理費 0.32% + 保管費 0.035% + 相關費用)",
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
    },
    "0056": {
        "symbol": "0056",
        "yahoo_symbol": "0056.TW",
        "name": "元大台灣高股息證券投資信託基金",
        "short_name": "元大高股息",
        "category": "高股息型 ETF",
        "exchange": "TWSE (臺灣證券交易所)",
        "benchmark": "FTSE TWSE Taiwan Dividend+ Index (臺灣高股息指數)",
        "tracking_method": "最佳化法 / 完全複製",
        "expense_ratio": "0.45% (經理費 0.30% + 保管費 0.035% + 相關費用)",
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
            {"code": "2301", "name": "光寶科", "sector": "電腦及週邊", "weight": 2.75},
            {"code": "3702", "name": "大聯大", "sector": "電子通路業", "weight": 2.65},
            {"code": "3044", "name": "健鼎", "sector": "電子零組件", "weight": 2.50},
            {"code": "2404", "name": "漢唐", "sector": "其他電子業", "weight": 2.45},
            {"code": "2891", "name": "中信金", "sector": "金融保險業", "weight": 2.40},
            {"code": "2890", "name": "永豐金", "sector": "金融保險業", "weight": 2.35},
            {"code": "2353", "name": "宏碁", "sector": "電腦及週邊", "weight": 2.30},
            {"code": "2356", "name": "英業達", "sector": "電腦及週邊", "weight": 2.25},
            {"code": "2324", "name": "仁寶", "sector": "電腦及週邊", "weight": 2.20},
            {"code": "2409", "name": "友達", "sector": "光電業", "weight": 2.15},
            {"code": "3481", "name": "群創", "sector": "光電業", "weight": 2.10},
            {"code": "1402", "name": "遠東新", "sector": "紡織纖維業", "weight": 2.05},
            {"code": "2609", "name": "陽明", "sector": "航運業", "weight": 2.00},
            {"code": "2615", "name": "萬海", "sector": "航運業", "weight": 1.95},
            {"code": "3045", "name": "台灣大", "sector": "通信網路業", "weight": 1.90},
            {"code": "4904", "name": "遠傳", "sector": "通信網路業", "weight": 1.85},
            {"code": "2886", "name": "兆豐金", "sector": "金融保險業", "weight": 1.80},
            {"code": "2892", "name": "第一金", "sector": "金融保險業", "weight": 1.75},
            {"code": "5880", "name": "合庫金", "sector": "金融保險業", "weight": 1.70},
            {"code": "2880", "name": "華南金", "sector": "金融保險業", "weight": 1.65},
            {"code": "2887", "name": "台新金", "sector": "金融保險業", "weight": 1.60},
            {"code": "2884", "name": "玉山金", "sector": "金融保險業", "weight": 1.55},
            {"code": "2885", "name": "元大金", "sector": "金融保險業", "weight": 1.50},
            {"code": "2809", "name": "京城銀", "sector": "金融保險業", "weight": 1.45},
            {"code": "1216", "name": "統一", "sector": "食品工業", "weight": 1.40},
            {"code": "1101", "name": "台泥", "sector": "水泥工業", "weight": 1.35},
            {"code": "1102", "name": "亞泥", "sector": "水泥工業", "weight": 1.30},
            {"code": "1303", "name": "南亞", "sector": "塑膠工業", "weight": 1.25},
            {"code": "1301", "name": "台塑", "sector": "塑膠工業", "weight": 1.20},
            {"code": "2002", "name": "中鋼", "sector": "鋼鐵工業", "weight": 1.15},
            {"code": "1504", "name": "東元", "sector": "電機機械業", "weight": 1.10},
            {"code": "2015", "name": "豐興", "sector": "鋼鐵工業", "weight": 1.05},
            {"code": "2606", "name": "裕民", "sector": "航運業", "weight": 1.00},
            {"code": "2637", "name": "慧洋-KY", "sector": "航運業", "weight": 0.95},
            {"code": "4958", "name": "臻鼎-KY", "sector": "電子零組件", "weight": 0.90},
            {"code": "3037", "name": "欣興", "sector": "電子零組件", "weight": 0.85},
            {"code": "2915", "name": "潤泰全", "sector": "貿易百貨業", "weight": 0.80},
            {"code": "9945", "name": "潤泰新", "sector": "建材營造業", "weight": 0.75},
            {"code": "5871", "name": "中租-KY", "sector": "其他業", "weight": 0.70},
            {"code": "2345", "name": "智邦", "sector": "通信網路業", "weight": 0.65},
            {"code": "2327", "name": "國巨", "sector": "電子零組件", "weight": 0.60}
        ]
    }
}

def fetch_json(url, timeout=10):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))

def get_yahoo_data(symbol):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5y&events=div%7Csplit'
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
                'name': s.get('Name', ''),
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
    """Fetch NAV, Discount/Premium, and Market Cap (AUM) from TWSE MIS all_etf.txt"""
    nav_map = {}
    try:
        url = 'https://mis.twse.com.tw/stock/data/all_etf.txt'
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as res:
            data = json.loads(res.read().decode('utf-8'))
            for group in data.get('a1', []):
                for item in group.get('msgArray', []):
                    code = item.get('a')
                    if code in ['0050', '0056']:
                        shares = float(item.get('c', 0) or 0)
                        nav = float(item.get('f', 0) or 0)
                        price = float(item.get('e', 0) or 0)
                        disc_pct = float(item.get('g', 0) or 0)
                        prev_nav = float(item.get('h', 0) or 0)
                        
                        # 市值 (規模): 總單位數 * 淨值
                        market_cap_billion = round((shares * nav) / 100000000, 2)
                        
                        # 格式化顯示
                        if market_cap_billion >= 10000:
                            cap_display = f"{market_cap_billion / 10000:.2f} 兆"
                        else:
                            cap_display = f"{market_cap_billion:,.0f} 億"

                        nav_map[code] = {
                            'nav': nav,
                            'market_price': price,
                            'discount_percent': disc_pct,
                            'prev_nav': prev_nav,
                            'shares_units': int(shares),
                            'creation_redemption_shares': int(float(item.get('d', 0) or 0)),
                            'market_cap_billion_ntd': market_cap_billion,
                            'market_cap_display': cap_display,
                            'nav_updated_time': f"{item.get('i', '')} {item.get('j', '')}"
                        }
    except Exception as e:
        print(f"Warning: Failed to fetch ETF NAV: {e}")
    return nav_map

def get_institutional_data():
    """Fetch 3 major institutional investors net trading from TWSE T86"""
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
                if code in ['0050', '0056']:
                    foreign = parse_shares(r[4])
                    trust = parse_shares(r[10])
                    dealer_total = parse_shares(r[11])
                    dealer_self = parse_shares(r[14])
                    dealer_hedge = parse_shares(r[17])
                    total = parse_shares(r[18])
                    
                    inst_map[code] = {
                        "date": formatted_date,
                        "foreign_lots": round(foreign / 1000),      # 張數
                        "trust_lots": round(trust / 1000),          # 張數
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

def process_etf(etf_id, twse_stocks, twse_valuations, nav_map, inst_map, now_tw):
    cfg = ETF_CONFIGS[etf_id]
    print(f"[{etf_id}] Fetching Yahoo data for {cfg['yahoo_symbol']}...")
    meta, timestamps, quote, adjclose, dividends_raw = get_yahoo_data(cfg['yahoo_symbol'])
    
    twse_info = twse_stocks.get(etf_id, {})
    twse_val = twse_valuations.get(etf_id, {})
    nav_info = nav_map.get(etf_id, {})
    inst_info = inst_map.get(etf_id, {})

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

    # Process Dividend Records and calculate fill-in days
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

    # Enrich Constituents
    enriched_constituents = []
    sector_summary = {}
    for c in cfg['constituents_base']:
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
            "exchange": cfg["exchange"],
            "benchmark": cfg["benchmark"],
            "tracking_method": cfg["tracking_method"],
            "expense_ratio": cfg["expense_ratio"],
            "inception_date": cfg["inception_date"],
            "dividend_frequency": cfg["dividend_frequency"],
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
            # 市值、淨值與折溢價
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

def main():
    tz_tw = datetime.timezone(datetime.timedelta(hours=8))
    now_tw = datetime.datetime.now(tz_tw)

    print("Fetching TWSE OpenAPI stock & valuation data...")
    twse_stocks, twse_valuations = get_twse_data()

    print("Fetching ETF NAV, Discount/Premium & Market Cap (all_etf)...")
    nav_map = get_nav_and_market_cap()

    print("Fetching Institutional Investors Trading (T86)...")
    inst_map = get_institutional_data()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')
    os.makedirs(data_dir, exist_ok=True)

    etf_list = []
    for etf_id in ETF_CONFIGS.keys():
        dataset = process_etf(etf_id, twse_stocks, twse_valuations, nav_map, inst_map, now_tw)
        output_file = os.path.join(data_dir, f"{etf_id}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        print(f"[{etf_id}] Generated {output_file} ({os.path.getsize(output_file) / 1024:.1f} KB)")
        
        cfg = ETF_CONFIGS[etf_id]
        etf_list.append({
            "symbol": cfg["symbol"],
            "short_name": cfg["short_name"],
            "name": cfg["name"],
            "category": cfg["category"],
            "dividend_frequency": cfg["dividend_frequency"]
        })

    list_file = os.path.join(data_dir, "etf_list.json")
    with open(list_file, 'w', encoding='utf-8') as f:
        json.dump(etf_list, f, ensure_ascii=False, indent=2)
    print(f"Generated {list_file}")

if __name__ == '__main__':
    main()
