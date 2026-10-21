#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TW Stock Multi-Factor Daily Screener (台股多面向全市場選股掃描器)
遵循 tw-stock-screener「5+1 面向評估體系」與籌碼核心邏輯：
1. 流動性防守：日成交量 > 1,000 張，股價 > 15 元
2. 籌碼土洋合力：投信積極認養、外資同步偏多、三大法人合計買超
3. 籌碼沉澱過濾：融資餘額下降（散戶浮額退場，籌碼流向法人）
4. 軋空動能加分：券資比 > 15%~30% 且抗跌
5. 估值安全邊際：合理本益比 (PE) 與淨值比 (PB)
"""

import urllib.request
import json
import os
import sys
import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'data'))

def safe_float(v):
    if v is None or v == '' or v == '--':
        return 0.0
    try:
        return float(str(v).replace(',', '').strip())
    except Exception:
        return 0.0

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode('utf-8'))

def run_screener(top_n=20):
    print("🚀 [Step 1/4] 抓取臺灣證券交易所當日所有個股成交量價 (STOCK_DAY_ALL)...")
    stocks_raw = fetch_json('https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL')

    print("📊 [Step 2/4] 抓取個股評價與殖利率數據 (BWIBBU_ALL)...")
    val_raw = fetch_json('https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL')
    val_map = {x['Code'].strip(): x for x in val_raw}

    print("🏦 [Step 3/4] 抓取三大法人買賣超日報 (T86)...")
    t86_raw = fetch_json('https://www.twse.com.tw/rwd/zh/fund/T86?response=json&selectType=ALL')
    inst_map = {}
    inst_date = t86_raw.get('date', '')
    for r in t86_raw.get('data', []):
        code = r[0].strip()
        foreign_lots = safe_float(r[4]) // 1000
        trust_lots = safe_float(r[10]) // 1000
        dealer_lots = safe_float(r[11]) // 1000
        total_lots = safe_float(r[18]) // 1000
        inst_map[code] = {
            'foreign_lots': int(foreign_lots),
            'trust_lots': int(trust_lots),
            'dealer_lots': int(dealer_lots),
            'total_lots': int(total_lots)
        }

    print("⚖️  [Step 4/4] 抓取信用交易融資融券餘額 (MI_MARGN)...")
    margin_raw = fetch_json('https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?response=json&selectType=ALL')
    margin_map = {}
    margin_date = margin_raw.get('date', '')
    for t in margin_raw.get('tables', []):
        if t.get('title') and '融資融券彙總' in t.get('title'):
            for r in t.get('data', []):
                code = r[0].strip()
                m_prev = safe_float(r[5])
                m_curr = safe_float(r[6])
                s_curr = safe_float(r[12])
                ratio = round((s_curr / m_curr) * 100, 2) if m_curr > 0 else 0.0
                margin_map[code] = {
                    'margin_balance': int(m_curr),
                    'margin_change': int(m_curr - m_prev),
                    'short_balance': int(s_curr),
                    'short_margin_ratio': ratio
                }
            break

    print(f"篩選市場母體：{len(stocks_raw)} 檔股票/ETF，法人日報：{len(inst_map)} 檔，融資融券：{len(margin_map)} 檔。")

    scored_stocks = []
    for s in stocks_raw:
        code = s.get('Code', '').strip()
        # 僅針對台股普通股 (4位純數字，排除權證、ETN、可轉債)
        if not (len(code) == 4 and code.isdigit()):
            continue

        vol_shares = safe_float(s.get('TradeVolume', 0))
        vol_lots = vol_shares / 1000
        # 濾網 1: 流動性防守 (當日成交量 >= 1,000 張)
        if vol_lots < 1000:
            continue

        close = safe_float(s.get('ClosingPrice', 0))
        # 濾網 2: 排除水餃低價股 (股價 >= 15 元)
        if close < 15:
            continue

        open_p = safe_float(s.get('OpeningPrice', 0))
        high_p = safe_float(s.get('HighestPrice', 0))
        low_p = safe_float(s.get('LowestPrice', 0))
        chg = safe_float(s.get('Change', 0))
        chg_pct = round((chg / (close - chg)) * 100, 2) if (close - chg) > 0 else 0.0

        v = val_map.get(code, {})
        pe = safe_float(v.get('PEratio', 0))
        pb = safe_float(v.get('PBratio', 0))
        div_yield = safe_float(v.get('DividendYield', 0))

        inst = inst_map.get(code, {})
        foreign = inst.get('foreign_lots', 0)
        trust = inst.get('trust_lots', 0)
        dealer = inst.get('dealer_lots', 0)
        total_inst = inst.get('total_lots', 0)

        margin = margin_map.get(code, {})
        m_balance = margin.get('margin_balance', 0)
        m_chg = margin.get('margin_change', 0)
        s_balance = margin.get('short_balance', 0)
        s_ratio = margin.get('short_margin_ratio', 0.0)

        # 多因子評分模型 (0~100 分)
        score = 0.0
        reasons = []

        # 1. 投信動向 (權重 25 分 - 內資主力核心認養指標)
        if trust >= 1000:
            score += 25
            reasons.append(f"投信強勢認養加碼 (+{trust:,} 張)")
        elif trust >= 300:
            score += 18
            reasons.append(f"投信積極佈局 (+{trust:,} 張)")
        elif trust > 0:
            score += 10
            reasons.append(f"投信偏多買超 (+{trust:,} 張)")

        # 2. 外資動向 (權重 20 分 - 國際熱錢指標)
        if foreign >= 3000:
            score += 20
            reasons.append(f"外資大幅回補 (+{foreign:,} 張)")
        elif foreign >= 1000:
            score += 14
            reasons.append(f"外資波段加碼 (+{foreign:,} 張)")
        elif foreign > 0:
            score += 8
            reasons.append(f"外資偏多買超 (+{foreign:,} 張)")

        # 土洋同步加分 (土洋合作推升力道最強)
        if trust > 0 and foreign > 0:
            score += 10
            reasons.append("⚡ 土洋法人同步買超")

        # 3. 籌碼沉澱度 (權重 15 分 - 融資增減)
        if m_chg < -500:
            score += 15
            reasons.append(f"散戶融資大退場 (-{abs(m_chg):,} 張，籌碼高度沉澱)")
        elif m_chg < 0:
            score += 10
            reasons.append(f"融資減少 (-{abs(m_chg):,} 張，浮額清洗)")

        # 4. 軋空與券資比 (權重 10 分)
        if s_ratio >= 25:
            score += 10
            reasons.append(f"🔥 券資比高達 {s_ratio:.1f}% (具潛在軋空動能)")
        elif s_ratio >= 15:
            score += 5
            reasons.append(f"券資比水位適中 ({s_ratio:.1f}%)")

        # 5. 當日價量型態 (權重 15 分)
        if chg > 0:
            score += 10
            reasons.append(f"股價強勢收紅 (+{chg_pct:.2f}%)")
        elif chg == 0:
            score += 5
            reasons.append("平盤抗跌守穩")

        if vol_lots >= 10000:
            score += 5
            reasons.append(f"量能充沛 (成交量 {int(vol_lots):,} 張)")

        # 6. 基本面安全邊際 (權重 5 分)
        if 0 < pe <= 25 and 0 < pb <= 3.5:
            score += 5
            reasons.append(f"估值穩健 (PE: {pe:.1f}, PB: {pb:.2f})")

        scored_stocks.append({
            'code': code,
            'name': s.get('Name', '').strip(),
            'close': close,
            'change': chg,
            'change_percent': chg_pct,
            'volume_lots': int(vol_lots),
            'institutional': {
                'foreign_lots': foreign,
                'trust_lots': trust,
                'dealer_lots': dealer,
                'total_lots': total_inst
            },
            'margin': {
                'margin_balance': m_balance,
                'margin_change': m_chg,
                'short_balance': s_balance,
                'short_margin_ratio': s_ratio
            },
            'valuation': {
                'pe': pe,
                'pb': pb,
                'dividend_yield': div_yield
            },
            'score': min(100, round(score, 1)),
            'reasons': reasons
        })

    # 排序取前 Top N
    top_picks = sorted(scored_stocks, key=lambda x: x['score'], reverse=True)[:top_n]

    tz_tw = datetime.timezone(datetime.timedelta(hours=8))
    now_tw = datetime.datetime.now(tz_tw)

    result_payload = {
        'generated_at': now_tw.strftime('%Y-%m-%d %H:%M:%S'),
        'total_scanned': len(scored_stocks),
        'top_count': len(top_picks),
        'top_picks': top_picks
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    out_file = os.path.join(DATA_DIR, 'screener_results.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(result_payload, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 篩選完成！已輸出至 {out_file}")
    print("=" * 65)
    print(f"{'代號':<6} {'名稱':<8} {'現價':<8} {'漲跌%':<8} {'法人合計':<10} {'投信/外資':<16} {'融資增減':<10} {'評分'}")
    print("-" * 65)
    for p in top_picks:
        f_t = f"+{p['institutional']['trust_lots']}/+{p['institutional']['foreign_lots']}"
        print(f"{p['code']:<6} {p['name']:<8} {p['close']:<8.2f} {p['change_percent']:<+8.2f} {p['institutional']['total_lots']:<+10,d} {f_t:<16} {p['margin']['margin_change']:<+10,d} {p['score']}")
    print("=" * 65)
    return result_payload

if __name__ == '__main__':
    count = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 20
    run_screener(top_n=count)
