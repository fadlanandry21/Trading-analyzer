# hybrid_analyzer_nofilter.py (Final Core: SMC Simple + Liquidity Sweep Filter) 
import os
import time
import math
import logging
from typing import List, Dict, Any, Optional, Tuple
import ccxt
import numpy as np
from flask import Flask, request, jsonify, render_template
from concurrent.futures import ThreadPoolExecutor, as_completed
from db import get_conn
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps



def save_to_db(output, recommendation, trade_levels):
    conn = get_conn()
    if not conn:
        print("DB connection failed. Skip saving.")
        return

    cursor = conn.cursor()

    sql = """
        INSERT INTO analyses (
            coin_name,
            entry_price,
            market_structure_1h,
            market_structure_4h,
            rsi_1h,
            macd_1h,
            funding_rate,
            long_short_ratio,
            volatility_prediction,
            recommendation,
            entry,
            sl,
            tp1,
            rrr,
            position_size_units,
            ob_type
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    values = (
        output["coin_name"],
        output["entry_price"],
        output["market_structure"]["1h"],
        output["market_structure"]["4h"],
        output["indicators"]["RSI_1h"],
        output["indicators"]["MACD_1h"],
        output["funding_rate"]["fundingRate"],
        output["long_short_ratio"]["longShortRatio"],
        output["volatility_pred"],
        recommendation,
        trade_levels["entry"] if trade_levels else None,
        trade_levels["sl"]if trade_levels else None,
        trade_levels["tp1"]if trade_levels else None,
        trade_levels["rrr"]if trade_levels else None,
        trade_levels["position_size_units"]if trade_levels else None,
        trade_levels["ob_type"]if trade_levels else None,
    )

    cursor.execute(sql, values)
    conn.commit()
    cursor.close()
    conn.close()

    print("Analisa Tersimpan di DB")

# ==============================================================
# CONFIGURATION & INITIALIZATION
# ==============================================================

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "replace-with-a-random-secret")
# Menggunakan CCXT untuk akses data publik Binance Futures
exchange = ccxt.binance({'options': {'defaultType': 'future'}})

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("HybridAnalyzerV8")

# --- TRADING PARAMETERS ---
MIN_RRR = 2.0                 # Rasio Risiko/Imbalan minimum (Dikembalikan ke 2.0)
ATR_MULTIPLIER = 2.0          # Koefisien untuk SL
ATR_PERIOD = 14               # Periode ATR
RISK_PER_TRADE_PERCENT = 1.0  
EQUITY = 10000                # Asumsi Modal Awal untuk perhitungan ukuran posisi

# Timeframes
TF_HIGH = "1d"
TF_MID = "4h"
TF_LOW = "1h"

# ==============================================================
# DATA FETCH CORE (Menggunakan CCXT)
# ==============================================================

def fetch_candles_ccxt(symbol: str, timeframe: str, limit: int) -> List[Dict[str, float]]:
    """Fetch OHLCV data using ccxt"""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        return [
            {
                "open_time": x[0], "open": float(x[1]), "high": float(x[2]), 
                "low": float(x[3]), "close": float(x[4]), "volume": float(x[5]),
            }
            for x in ohlcv
        ]
    except Exception as e:
        logger.error(f"CCXT fetch error {symbol} {timeframe}: {e}")
        return []

def fetch_sentiment_data(symbol: str) -> Dict[str, Any]:
    """Fetch Funding Rate dan Long/Short Ratio"""
    sentiment = {"funding_rate": 0.0, "open_interest": 0.0, "long_short_ratio": 1.0}
    try:
        symbol_no_slash = symbol.replace('/USDT', '').replace('/', '') + 'USDT'
        
        fr_data = exchange.fapiPublicGetPremiumIndex({'symbol': symbol_no_slash})
        sentiment["funding_rate"] = float(fr_data.get("lastFundingRate", 0.0))
        
        params_ls = {'symbol': symbol_no_slash, 'period': '5m', 'limit': 30}
        ls_data = exchange.fapiDataGetGlobalLongShortAccountRatio(params_ls)
        if ls_data:
            sentiment["long_short_ratio"] = float(ls_data[-1].get("longShortRatio", 1.0))
            
    except Exception as e:
        logger.warning(f"Failed to fetch sentiment data for {symbol}: {e}")
        
    return sentiment

# ==============================================================
# ANALYSIS CORE (SMC & INDICATORS)
# ==============================================================

def calculate_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Menghitung Relative Strength Index (RSI)"""
    if len(closes) < period + 1: return None
    
    deltas = np.diff(closes)
    gains = deltas * (deltas > 0)
    losses = -deltas * (deltas < 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    if avg_loss == 0: return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi)

def calculate_ema(data: List[float], period: int) -> List[float]:
    """Menghitung Exponential Moving Average (EMA) secara rekursif"""
    if len(data) < period: return []
    prices = np.array(data)
    alpha = 2 / (period + 1)
    ema = np.zeros_like(prices)
    ema[period - 1] = np.mean(prices[:period])
    for i in range(period, len(prices)):
        ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]
    return list(ema[period - 1:])

def calculate_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[float]:
    """Menghitung MACD Line (hanya satu nilai terakhir) menggunakan EMA yang stabil"""
    if len(closes) < slow: return None
    ema_fast_list = calculate_ema(closes, fast)
    ema_slow_list = calculate_ema(closes, slow)
    if not ema_slow_list: return None
    diff_len = len(ema_fast_list) - len(ema_slow_list)
    macd_line = np.array(ema_fast_list[diff_len:]) - np.array(ema_slow_list)
    return float(macd_line[-1])

def calc_structure_and_bias(candles: List[Dict[str, float]]) -> str:
    """Menentukan bias dasar pasar"""
    if len(candles) < 20: return "Sideways"
    closes = [c["close"] for c in candles]
    slope = (closes[-1] - closes[0]) / closes[0]
    if slope > 0.01: return "Bullish"
    elif slope < -0.01: return "Bearish"
    else: return "Sideways"

def calculate_atr(candles: List[Dict[str, float]], period: int) -> float:
    """Menghitung Average True Range (ATR)"""
    if len(candles) < period: return 0.0
    true_ranges = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["high"], candles[i]["low"], candles[i-1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        true_ranges.append(tr)
    if len(true_ranges) < period: return 0.0
    return sum(true_ranges[-period:]) / period

def detect_valid_order_block(candles: List[Dict[str, float]], bias: str) -> Optional[Dict[str, float]]:
    """Mendeteksi Order Block dasar (tanpa FVG ketat) di 10 candle terakhir."""
    
    # Jendela pencarian OB dikembalikan ke 10 candle terakhir (40 jam)
    if len(candles) < 10: return None
        
    for i in range(len(candles) - 10, len(candles) - 1): 
        ob_candle = candles[i]
        is_bullish_ob = ob_candle["close"] < ob_candle["open"] # Lilin Merah/Bearish -> Demand OB
        is_bearish_ob = ob_candle["close"] > ob_candle["open"] # Lilin Hijau/Bullish -> Supply OB
        
        # Filter: Harga saat ini tidak boleh berada di dalam OB
        current_price = candles[-1]["close"]
        if min(ob_candle["open"], ob_candle["close"]) < current_price < max(ob_candle["open"], ob_candle["close"]): 
            continue 
            
        if is_bullish_ob or is_bearish_ob:
            return {
                "type": "Demand" if is_bullish_ob else "Supply",
                "low": ob_candle["low"], 
                "high": ob_candle["high"], 
                "mid": (ob_candle["high"] + ob_candle["low"]) / 2,
            }
    return None

def detect_liquidity_sweep(candles: List[Dict[str, float]]) -> str:
    """Mendeteksi pola stop-hunt di 5 lilin terakhir."""
    if len(candles) < 5: return "None"
    last_highs = [c["high"] for c in candles[-5:]]
    last_lows = [c["low"] for c in candles[-5:]]
    
    # Sweep terjadi jika lilin terakhir menembus High/Low sebelumnya (tanpa menembus Low/High)
    sweep_high = last_highs[-1] > max(last_highs[:-1])
    sweep_low = last_lows[-1] < min(last_lows[:-1])
    
    if sweep_high: return "Buy-side liquidity sweep"
    elif sweep_low: return "Sell-side liquidity sweep"
    return "None"


# --- TRADE DECISION CORE ---

def calculate_rrr(entry: float, sl: float, tp: float, side: str) -> float:
    """Menghitung Rasio Risiko/Imbalan"""
    if side == "Long":
        risk = abs(entry - sl)
        reward = abs(tp - entry)
    else:
        risk = abs(sl - entry)
        reward = abs(entry - tp)
        
    return reward / risk if risk > 0 else 0.0


def generate_trade_levels(ob_zone: Dict[str, float], bias: str, current_price: float, candles_4h: List[Dict[str, float]]) -> Optional[Dict[str, Any]]:
    """Menghitung level Entry, SL, TP dinamis. RRR minimal 2.0 untuk semua sinyal."""
    
    MIN_RRR = 2.0  # RRR minimal 2.0 di semua kondisi
    DISTANCE_TOLERANCE = 0.05 # Maksimal 5% jarak dari harga saat ini
    
    entry = ob_zone["mid"]
    current_atr = calculate_atr(candles_4h, ATR_PERIOD)
    
    # Tentukan Side
    if ob_zone["type"] == "Demand": side = "Long"
    elif ob_zone["type"] == "Supply": side = "Short"
    else: return None 
    
    # Filter 1: POSISI HARGA SAAT INI (Logika Limit Order)
    if side == "Long":
        # Entry di bawah Current Price
        if entry >= current_price or (current_price - entry) / current_price > DISTANCE_TOLERANCE: return None 
    elif side == "Short":
        # Entry di atas Current Price
        if entry <= current_price or (entry - current_price) / current_price > DISTANCE_TOLERANCE: return None
    else:
        return None
        
    # SL Dinamis (ATR-Based)
    atr_risk = current_atr * ATR_MULTIPLIER
    
    if side == "Long":
        sl = min(ob_zone["low"] * 0.999, entry - atr_risk) 
        tp1 = entry + (entry - sl) * MIN_RRR
        tp2 = entry + (entry - sl) * 3.5 
    else: # side == "Short"
        sl = max(ob_zone["high"] * 1.001, entry + atr_risk)
        tp1 = entry - (sl - entry) * MIN_RRR
        tp2 = entry - (sl - entry) * 3.5
        
    # 2. Hitung RRR dan Filter
    rrr1 = calculate_rrr(entry, sl, tp1, side)
    
    if rrr1 < MIN_RRR:
        return None
        
    # Periksa apakah ini counter-trend
    is_counter = (bias == "Bearish" and side == "Long") or (bias == "Bullish" and side == "Short")
        
    # Jika lolos RRR, kembalikan level
    risk_dollars = EQUITY * (RISK_PER_TRADE_PERCENT / 100)
    risk_per_unit = abs(entry - sl)
    size_units = math.floor(risk_dollars / risk_per_unit) 

    return {
        "recommendation": side,
        "ob_type": ob_zone["type"],
        "is_counter_trend": is_counter, # Pertahankan flag risiko
        "entry": round(entry, 4),
        "sl": round(sl, 4),
        "tp1": round(tp1, 4),
        "tp2": round(tp2, 4),
        "rrr": round(rrr1, 2),
        "required_rrr": MIN_RRR,
        "position_size_units": size_units,
    }


# --- FUNGSI INI MENGGANTIKAN FUNGSI analyze_and_generate_signal LAMA ---
# --- FUNGSI analyze_and_generate_signal YANG BARU ---
def analyze_and_generate_signal(data: Dict[str, Any]) -> Tuple[Dict[str, Any], str, Optional[Dict[str, Any]]]:
    """Mengaktifkan mode Frekuensi Tinggi: Sinyal muncul berdasarkan OB + RRR 2.0 (Sweep hanya Konfluensi)."""
    
    c_1h = data["candles"][TF_LOW]
    c_4h = data["candles"][TF_MID]
    
    closes_1h = [c["close"] for c in c_1h]
    
    # 1. Indikator Klasik & Struktur
    rsi_1h = calculate_rsi(closes_1h)
    macd_1h = calculate_macd(closes_1h)
    atr_4h = calculate_atr(c_4h, ATR_PERIOD)
    bias_1h = calc_structure_and_bias(c_1h)
    bias_4h = calc_structure_and_bias(c_4h)
    
    # 2. Sentimen & Liquidity
    sent = data["sentiment"]
    frate = sent.get("funding_rate", 0.0)
    ls_ratio = sent.get("long_short_ratio", 1.0)
    liquidity_status_1h = detect_liquidity_sweep(c_1h) # Cek Sweep di 1H
    
    # 3. SMC & Level Perdagangan
    ob_zone = detect_valid_order_block(c_4h, bias_4h) 
    trade_levels = None
    
    # --- Filter UTAMA: OB Harus Ada DAN lolos RRR 2.0 ---
    if ob_zone:
        # Hitung level trading (RRR filter ada di dalam fungsi ini)
        trade_levels = generate_trade_levels(ob_zone, bias_4h, data["current_price"], c_4h)

    # 4. Volatility Prediction
    volatility_pred = "Moderate"
    if atr_4h / data["current_price"] > 0.02: 
        volatility_pred = "High Volatility"
    elif atr_4h / data["current_price"] < 0.005:
        volatility_pred = "Low Volatility"

    # --- Sinyal & Analisis Komprehensif ---
    analysis_text = ""
    recommendation = "NEUTRAL"
    
    if trade_levels:
        # Prioritas 1: Sinyal Presisi Ditemukan (OB + RRR Lolos)
        side = trade_levels['recommendation']
        recommendation = f"{side.upper()} (Limit Order)"
        
        # Cek dan catat konfluensi Sweep (TIDAK LAGI SEBAGAI FILTER)
        sweep_aligned = False
        if (side == "Long" and liquidity_status_1h == "Sell-side liquidity sweep") or \
           (side == "Short" and liquidity_status_1h == "Buy-side liquidity sweep"):
            sweep_aligned = True
        
        sweep_note = ", **TIDAK TERKONFIRMASI SWEEP**."
        if sweep_aligned:
             sweep_note = ", **Dikonfirmasi Liquidity Sweep**." # Konfirmasi Langsung!
        
        analysis_text = f"REKOMENDASI: {recommendation} DIHARAPKAN.\n\nANALISIS:\n"
        analysis_text += f"Setup Trading Institusional: {trade_levels['ob_type']} OB 4H Ditemukan{sweep_note}.\n"
        analysis_text += f"RRR Lolos Filter ({trade_levels['rrr']:.2f}). Kesiapan: **LEVEL HARGA PRESISI TERSEDIA.**"
        
        # Peringatan Counter-Trend
        is_counter_trend = (side == "Long" and bias_4h == "Bearish") or \
                           (side == "Short" and bias_4h == "Bullish")
        if is_counter_trend:
             analysis_text += "\n⚠️ PERINGATAN: SINYAL INI BERSIFAT COUNTER-TREND (Reversal)."
        
        analysis_text += f"\n\n--- DETAIL LEVEL ---\n"
        analysis_text += f"ENTRY ({trade_levels['ob_type']}): ${trade_levels['entry']:.4f}\n"
        analysis_text += f"SL (ATR-Based): ${trade_levels['sl']:.4f}\n"
        analysis_text += f"TP1 ({trade_levels['rrr']:.2f} RRR): ${trade_levels['tp1']:.4f}\n"
        analysis_text += f"Ukuran Posisi: {trade_levels['position_size_units']} unit ({RISK_PER_TRADE_PERCENT}% risiko)."
        
    elif bias_4h != "Sideways":
        # Prioritas 2: Mode menunggu (jika OB tidak lolos RRR atau tidak ada OB sama sekali)
        if bias_4h == "Bullish" and rsi_1h is not None and rsi_1h < 70:
            recommendation = "BULLISH (Tunggu Retracement)"
            analysis_text = f"Struktur 4H Bullish. RSI 1H ({rsi_1h:.2f}) sehat. Cari Buy Limit di Demand terdekat. **LEVEL HARGA PRESISI TIDAK DITEMUKAN.**"
        elif bias_4h == "Bearish" and rsi_1h is not None and rsi_1h > 30:
            recommendation = "BEARISH (Tunggu Pullback)"
            analysis_text = f"Struktur 4H Bearish. RSI 1H ({rsi_1h:.2f}) sehat. Cari Sell Limit di Supply terdekat. **LEVEL HARGA PRESISI TIDAK DITEMUKAN.**"
        else:
            analysis_text = f"Struktur {bias_4h} kuat, tetapi kondisi 1H (RSI {rsi_1h:.2f}) menunjukkan potensi konsolidasi. Tunggu."

    else:
        # Prioritas 3: Sideways
        analysis_text = "Pasar berada dalam kondisi Sideways. Hindari perdagangan terarah."


    # Penyesuaian Sentimen Akhir
    if frate > 0.0005:
        analysis_text += "\n\n*PERINGATAN SENTIMEN:* Funding Rate tinggi. Risiko Long Squeeze meningkat."
    elif frate < -0.0005:
        analysis_text += "\n\n*PERINGATAN SENTIMEN:* Funding Rate sangat negatif. Risiko Short Squeeze meningkat."

    # Struktur Data Output untuk Frontend
    output_data = {
        "coin_name": data["symbol"].replace('/USDT', '').replace('/', ''),
        "entry_price": data["current_price"],
        "market_structure": {"1h": bias_1h, "4h": bias_4h},
        "funding_rate": {"fundingRate": frate},
        "long_short_ratio": {"longShortRatio": ls_ratio},
        "indicators": {
            "RSI_1h": rsi_1h,
            "MACD_1h": macd_1h,
        },
        "volatility_pred": volatility_pred,
        "analysis": analysis_text,
        "trade_levels": trade_levels, 
    }
    
    return output_data, recommendation, trade_levels


# ==============================================================
# ORCHESTRATION & FLASK ROUTES
# ==============================================================

def get_all_market_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Mengumpulkan semua data yang dibutuhkan untuk analisis"""
    try:
        symbol_ccxt = symbol.upper() + "/USDT"
        
        candles_1d = fetch_candles_ccxt(symbol_ccxt, TF_HIGH, 200)
        candles_4h = fetch_candles_ccxt(symbol_ccxt, TF_MID, 300)
        candles_1h = fetch_candles_ccxt(symbol_ccxt, TF_LOW, 300)
        
        if not all([candles_1d, candles_4h, candles_1h]):
             logger.error(f"Failed to get essential candles for {symbol}")
             return None

        sentiment = fetch_sentiment_data(symbol_ccxt)

        return {
            "symbol": symbol_ccxt,
            "candles": {TF_HIGH: candles_1d, TF_MID: candles_4h, TF_LOW: candles_1h},
            "sentiment": sentiment,
            "current_price": candles_1h[-1]["close"]
        }
    except Exception as e:
        logger.error(f"Error compiling market data for {symbol}: {e}")
        return None
    

# Login and Register Auth
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
       if 'user_id' not in session:
           return redirect(url_for('login'))
       return f(*args, *kwargs)
    return decorated 


@app.route('/register', methods=['GET', 'POST'])
def register ():
    if request.method == 'POST':
        username = request.form.get("username","").strip() 
        password = request.form.get("password", "").strip()
        if not username or not password:
            return render_template('register.html', error="Username and Password Required!")
        
        hashed = generate_password_hash(password)
        conn = get_conn()

        if not conn:
            return render_template('register.html', error="Ups! Cannot connect DB")
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username, password) VALUES (%s,%s)", (username, hashed))
            conn.commit()
        except Exception as e:
            return render_template("register.html", error="Username Already exist!")
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        conn = get_conn()

        if not conn:
            return render_template("login.html", error="cannot connect DB!")
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close(); conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid Username and Password!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Merender index.html dari folder templates"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
@login_required
def analyze_single_coin():
    """Endpoint untuk menganalisis satu koin (sesuai permintaan frontend)"""
    start_time = time.time()
    
    coin_symbol = request.form.get('coin_name', '').upper().strip()
    if not coin_symbol:
        return jsonify({"error": "Coin symbol is required"}), 400

    logger.info(f"Analyzing {coin_symbol}...")
    
    data = get_all_market_data(coin_symbol)
    if not data: 
        return jsonify({"error": f"Failed to fetch market data for {coin_symbol}"}), 500

    output_data, recommendation, trade_levels = analyze_and_generate_signal(data)

    save_to_db(output_data, recommendation, trade_levels)

    latency = round(time.time() - start_time, 3)
    logger.info(f"✅ {output_data['coin_name']} | {recommendation} | {latency}s")

    return jsonify(output_data)


# function History 

@app.route("/history", methods=["GET"])
@login_required
def get_history():
    try:    
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                id,
                coin_name, 
                entry_price, 
                recommendation,
                created_at,
                entry,
                sl,
                tp1,
                rrr
            FROM analyses
            ORDER BY created_at DESC 
            LIMIT 5
        """)

        rows = cursor.fetchall()

        for row in rows:
            row ["has_trade_levels"] = (
                row["entry"] is not None and
                row["sl"] is not None and
                row["tp1"] is not None and
                row["rrr"] is not None
            )

        return jsonify(rows), 200

    except Exception as e:  
        return jsonify({"error": str(e)}), 500
    

@app.route("/history/<int:record_id>", methods=["GET"])
def get_history_detail(record_id):
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            id,
            coin_name,
            entry_price,
            market_structure_1h,
            market_structure_4h,
            rsi_1h,
            macd_1h,
            funding_rate,
            long_short_ratio,
            volatility_prediction,
            recommendation,
            entry,
            sl,
            tp1,
            rrr,
            position_size_units,
            ob_type,
            created_at
        FROM analyses
        WHERE id = %s
    """, (record_id,))

    row = cursor.fetchone()  
    cursor.close()
    conn.close()

    if not row:
        return jsonify({"error": "Record not found"}), 404

    return jsonify(row), 200


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    logger.info(f"Starting Hybrid Analyzer V8 (Final Simple + Sweep Core) on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)