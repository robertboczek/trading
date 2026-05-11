"""
Candle Pattern Day Trader
=========================
Broker: Charles Schwab API (OAuth2 / REST)
 
Patterns detected:
  - Bullish/Bearish Engulfing
  - Hammer & Shooting Star
  - Doji (indecision / reversal warning)
  - Morning Star & Evening Star (3-candle reversal)
  - 3-candle Momentum (3 consecutive green or red)
 
Additional filters:
  - VWAP (price must be above for longs, below for shorts)
  - RSI (avoid overbought/oversold entries)
  - Volume confirmation (candle volume > average)
 
Setup:
  pip install pandas ta requests
 
Schwab API setup (one-time):
  1. Register an app at https://developer.schwab.com
  2. Note your App Key (client_id) and App Secret (client_secret)
  3. Set REDIRECT_URI to match what you registered (e.g. https://127.0.0.1)
  4. Run the script once — it will open a browser for OAuth login and save
     tokens to TOKEN_FILE automatically. Tokens auto-refresh after that.
 
Configuration:
  Set your credentials and stock list in the CONFIG section below.
"""
 
import time
import json
import logging
import webbrowser
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs
 
import requests
import pandas as pd
import ta  # pip install ta
 
# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG — edit this section
# ══════════════════════════════════════════════════════════════════════════════
CONFIG = {
    # ── Schwab API credentials ───────────────────────────────────────────────
    # Register your app at https://developer.schwab.com
    "CLIENT_ID":     "YOUR_SCHWAB_APP_KEY",       # "App Key" in Schwab dev portal
    "CLIENT_SECRET": "YOUR_SCHWAB_APP_SECRET",    # "App Secret" in Schwab dev portal
    "REDIRECT_URI":  "https://127.0.0.1",         # must match your registered redirect URI
    "TOKEN_FILE":    "schwab_tokens.json",         # where OAuth tokens are cached locally
 
    # Schwab API base URLs (do not change unless Schwab updates them)
    "AUTH_URL":      "https://api.schwabapi.com/v1/oauth/authorize",
    "TOKEN_URL":     "https://api.schwabapi.com/v1/oauth/token",
    "TRADER_URL":    "https://api.schwabapi.com/trader/v1",
    "MARKET_URL":    "https://api.schwabapi.com/marketdata/v1",
 
    # Stocks to scan each cycle
    "WATCHLIST": ["AAPL", "TSLA", "NVDA", "AMD", "SPY"],
 
    # Candle timeframe for pattern detection
    # Schwab periodType/period/frequencyType/frequency combos:
    #   "1Min"  → periodType=day, period=1, frequencyType=minute, frequency=1
    #   "5Min"  → periodType=day, period=1, frequencyType=minute, frequency=5
    #   "15Min" → periodType=day, period=1, frequencyType=minute, frequency=15
    "TIMEFRAME": "5Min",          # 1Min | 5Min | 15Min
    "CANDLES_LOOKBACK": 20,       # how many candles to fetch per cycle
 
    # Risk management
    "RISK_PER_TRADE_PCT": 1.0,    # % of portfolio to risk per trade
    "STOP_LOSS_PCT": 1.5,         # stop loss % below/above entry
    "TAKE_PROFIT_PCT": 3.0,       # take profit % above/below entry
    "MAX_OPEN_POSITIONS": 3,      # maximum simultaneous positions
 
    # Indicator filters
    "RSI_PERIOD": 14,
    "RSI_OVERBOUGHT": 70,
    "RSI_OVERSOLD": 30,
    "VOLUME_MULTIPLIER": 1.3,     # candle volume must be > N × avg volume
 
    # Loop
    "SCAN_INTERVAL_SEC": 60,      # seconds between scans
    "TRADE_START": "09:35",       # don't trade before this (market open buffer)
    "TRADE_END": "15:45",         # stop new entries before close
}
# ══════════════════════════════════════════════════════════════════════════════
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("CandleTrader")
 
 
# ─── Data classes ─────────────────────────────────────────────────────────────
 
@dataclass
class Signal:
    symbol: str
    direction: str          # "long" | "short"
    pattern: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float = 1.0  # 1–3 (more patterns = higher)
 
 
@dataclass
class Position:
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    qty: int
    pattern: str
 
 
# ─── Pattern Detection ────────────────────────────────────────────────────────
 
class CandlePatterns:
    """Stateless pattern detection on a DataFrame with OHLCV columns."""
 
    @staticmethod
    def body(c): return abs(c["close"] - c["open"])
    @staticmethod
    def upper_wick(c): return c["high"] - max(c["open"], c["close"])
    @staticmethod
    def lower_wick(c): return min(c["open"], c["close"]) - c["low"]
    @staticmethod
    def is_bullish(c): return c["close"] > c["open"]
    @staticmethod
    def is_bearish(c): return c["close"] < c["open"]
 
    # ── Single-candle ──────────────────────────────────────────────────────
 
    def doji(self, c) -> bool:
        """Body ≤ 10 % of total range → indecision."""
        rng = c["high"] - c["low"]
        return rng > 0 and self.body(c) / rng <= 0.10
 
    def hammer(self, c) -> bool:
        """Bullish reversal: small body at top, long lower wick (≥ 2× body)."""
        b = self.body(c)
        lw = self.lower_wick(c)
        uw = self.upper_wick(c)
        return b > 0 and lw >= 2 * b and uw <= 0.3 * b
 
    def shooting_star(self, c) -> bool:
        """Bearish reversal: small body at bottom, long upper wick (≥ 2× body)."""
        b = self.body(c)
        uw = self.upper_wick(c)
        lw = self.lower_wick(c)
        return b > 0 and uw >= 2 * b and lw <= 0.3 * b
 
    # ── Two-candle ─────────────────────────────────────────────────────────
 
    def bullish_engulfing(self, prev, curr) -> bool:
        """Bearish candle followed by a larger bullish candle."""
        return (
            self.is_bearish(prev)
            and self.is_bullish(curr)
            and curr["open"] < prev["close"]
            and curr["close"] > prev["open"]
        )
 
    def bearish_engulfing(self, prev, curr) -> bool:
        """Bullish candle followed by a larger bearish candle."""
        return (
            self.is_bullish(prev)
            and self.is_bearish(curr)
            and curr["open"] > prev["close"]
            and curr["close"] < prev["open"]
        )
 
    # ── Three-candle ───────────────────────────────────────────────────────
 
    def morning_star(self, c1, c2, c3) -> bool:
        """Bearish → small body (gap down) → Bullish recovery."""
        return (
            self.is_bearish(c1)
            and self.body(c2) < 0.4 * self.body(c1)
            and self.is_bullish(c3)
            and c3["close"] > c1["open"] + (c1["close"] - c1["open"]) * 0.5
        )
 
    def evening_star(self, c1, c2, c3) -> bool:
        """Bullish → small body (gap up) → Bearish reversal."""
        return (
            self.is_bullish(c1)
            and self.body(c2) < 0.4 * self.body(c1)
            and self.is_bearish(c3)
            and c3["close"] < c1["open"] + (c1["close"] - c1["open"]) * 0.5
        )
 
    def three_green(self, c1, c2, c3) -> bool:
        """Three consecutive rising bullish candles (momentum)."""
        return (
            self.is_bullish(c1)
            and self.is_bullish(c2)
            and self.is_bullish(c3)
            and c2["close"] > c1["close"]
            and c3["close"] > c2["close"]
        )
 
    def three_red(self, c1, c2, c3) -> bool:
        """Three consecutive falling bearish candles (momentum)."""
        return (
            self.is_bearish(c1)
            and self.is_bearish(c2)
            and self.is_bearish(c3)
            and c2["close"] < c1["close"]
            and c3["close"] < c2["close"]
        )
 
    # ── Scanner ────────────────────────────────────────────────────────────
 
    def scan(self, df: pd.DataFrame) -> list[tuple[str, str, float]]:
        """
        Returns list of (pattern_name, direction, confidence) found in the
        last candles of df.  confidence = number of confirming patterns.
        """
        if len(df) < 3:
            return []
 
        results = []
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
 
        # Three-candle
        if self.morning_star(c1, c2, c3):
            results.append(("Morning Star", "long", 2.0))
        if self.evening_star(c1, c2, c3):
            results.append(("Evening Star", "short", 2.0))
        if self.three_green(c1, c2, c3):
            results.append(("3-Candle Momentum Up", "long", 1.5))
        if self.three_red(c1, c2, c3):
            results.append(("3-Candle Momentum Down", "short", 1.5))
 
        # Two-candle
        if self.bullish_engulfing(c2, c3):
            results.append(("Bullish Engulfing", "long", 2.0))
        if self.bearish_engulfing(c2, c3):
            results.append(("Bearish Engulfing", "short", 2.0))
 
        # Single-candle
        if self.hammer(c3):
            results.append(("Hammer", "long", 1.0))
        if self.shooting_star(c3):
            results.append(("Shooting Star", "short", 1.0))
        if self.doji(c3):
            results.append(("Doji", "neutral", 0.5))
 
        return results
 
 
# ─── Indicator Filters ────────────────────────────────────────────────────────
 
def compute_indicators(df: pd.DataFrame, rsi_period: int) -> pd.DataFrame:
    df = df.copy()
    # RSI
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=rsi_period).rsi()
    # VWAP (cumulative intraday)
    df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
    # Average volume
    df["avg_vol"] = df["volume"].rolling(10).mean()
    return df
 
 
def passes_filters(df: pd.DataFrame, direction: str, cfg: dict) -> bool:
    last = df.iloc[-1]
    rsi = last["rsi"]
    price = last["close"]
    vwap = last["vwap"]
    vol = last["volume"]
    avg_vol = last["avg_vol"]
 
    # Volume confirmation
    if avg_vol > 0 and vol < cfg["VOLUME_MULTIPLIER"] * avg_vol:
        return False
 
    if direction == "long":
        if rsi > cfg["RSI_OVERBOUGHT"]:  # don't buy overbought
            return False
        if price < vwap:                  # price below VWAP → weak
            return False
    elif direction == "short":
        if rsi < cfg["RSI_OVERSOLD"]:    # don't short oversold
            return False
        if price > vwap:                  # price above VWAP → weak short
            return False
 
    return True
 
 
# ─── Schwab OAuth2 Token Manager ─────────────────────────────────────────────
 
class SchwabAuth:
    """
    Handles OAuth2 authorization_code flow + automatic token refresh.
    Tokens are persisted to TOKEN_FILE so you only need to log in once.
    """
 
    def __init__(self, cfg: dict):
        self.client_id = cfg["CLIENT_ID"]
        self.client_secret = cfg["CLIENT_SECRET"]
        self.redirect_uri = cfg["REDIRECT_URI"]
        self.auth_url = cfg["AUTH_URL"]
        self.token_url = cfg["TOKEN_URL"]
        self.token_file = Path(cfg["TOKEN_FILE"])
        self._tokens: dict = {}
 
    # ── Token persistence ──────────────────────────────────────────────────
 
    def _save(self):
        self.token_file.write_text(json.dumps(self._tokens, indent=2))
 
    def _load(self) -> bool:
        if self.token_file.exists():
            self._tokens = json.loads(self.token_file.read_text())
            return True
        return False
 
    # ── First-time login ───────────────────────────────────────────────────
 
    def _authorize(self):
        """Open browser, capture redirect, exchange code for tokens."""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "readonly trading",
        }
        url = f"{self.auth_url}?{urlencode(params)}"
        log.info("Opening Schwab login in your browser…")
        webbrowser.open(url)
        redirected = input(
            "\nAfter logging in, paste the full redirect URL here:\n> "
        ).strip()
        code = parse_qs(urlparse(redirected).query).get("code", [None])[0]
        if not code:
            raise ValueError("Could not extract authorization code from URL.")
        self._exchange_code(code)
 
    def _exchange_code(self, code: str):
        resp = requests.post(
            self.token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            },
            auth=(self.client_id, self.client_secret),
        )
        resp.raise_for_status()
        self._tokens = resp.json()
        self._tokens["obtained_at"] = time.time()
        self._save()
        log.info("Schwab tokens saved.")
 
    # ── Token refresh ──────────────────────────────────────────────────────
 
    def _refresh(self):
        resp = requests.post(
            self.token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._tokens["refresh_token"],
            },
            auth=(self.client_id, self.client_secret),
        )
        resp.raise_for_status()
        self._tokens.update(resp.json())
        self._tokens["obtained_at"] = time.time()
        self._save()
        log.info("Schwab access token refreshed.")
 
    # ── Public ─────────────────────────────────────────────────────────────
 
    def get_access_token(self) -> str:
        if not self._tokens:
            if not self._load():
                self._authorize()
 
        # Refresh if token expires within 5 minutes
        expires_in = self._tokens.get("expires_in", 1800)
        obtained_at = self._tokens.get("obtained_at", 0)
        if time.time() - obtained_at > expires_in - 300:
            self._refresh()
 
        return self._tokens["access_token"]
 
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.get_access_token()}"}
 
 
# ─── Schwab Broker Wrapper ────────────────────────────────────────────────────
 
_TIMEFRAME_MAP = {
    "1Min":  {"frequencyType": "minute", "frequency": "1"},
    "5Min":  {"frequencyType": "minute", "frequency": "5"},
    "15Min": {"frequencyType": "minute", "frequency": "15"},
}
 
 
class SchwabBroker:
    """
    Thin wrapper around Schwab Trader + MarketData REST APIs.
    Implements the same interface as the original AlpacaBroker so the
    trading engine above requires zero changes.
    """
 
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.auth = SchwabAuth(cfg)
        self.trader_url = cfg["TRADER_URL"]
        self.market_url = cfg["MARKET_URL"]
        self._account_hash: Optional[str] = None  # cached after first call
 
    # ── Internal helpers ───────────────────────────────────────────────────
 
    def _get(self, base: str, path: str, params: dict = None) -> dict:
        r = requests.get(
            f"{base}{path}",
            headers=self.auth.headers(),
            params=params or {},
        )
        r.raise_for_status()
        return r.json()
 
    def _post(self, base: str, path: str, payload: dict) -> requests.Response:
        r = requests.post(
            f"{base}{path}",
            headers={**self.auth.headers(), "Content-Type": "application/json"},
            json=payload,
        )
        r.raise_for_status()
        return r
 
    def _account_hash(self) -> str:
        """Schwab requires an encrypted account hash instead of plain account number."""
        if self._account_hash:
            return self._account_hash
        accounts = self._get(self.trader_url, "/accounts/accountNumbers")
        # Pick the first account; extend here if you have multiple
        self._account_hash = accounts[0]["hashValue"]
        return self._account_hash
 
    # ── Market data ────────────────────────────────────────────────────────
 
    def get_bars(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        tf = _TIMEFRAME_MAP.get(timeframe, _TIMEFRAME_MAP["5Min"])
        params = {
            "symbol": symbol,
            "periodType": "day",
            "period": "1",
            "frequencyType": tf["frequencyType"],
            "frequency": tf["frequency"],
            "needExtendedHoursData": "false",
        }
        data = self._get(self.market_url, "/pricehistory", params)
        candles = data.get("candles", [])
        if not candles:
            return pd.DataFrame()
 
        df = pd.DataFrame(candles)
        df["datetime"] = pd.to_datetime(df["datetime"], unit="ms")
        df = df.set_index("datetime")
        df = df[["open", "high", "low", "close", "volume"]].astype(float)
        return df.tail(limit)
 
    def market_is_open(self) -> bool:
        data = self._get(self.market_url, "/markets/hours", {"markets": "equity"})
        try:
            return data["equity"]["equity"]["isOpen"]
        except (KeyError, TypeError):
            return False
 
    # ── Account ────────────────────────────────────────────────────────────
 
    def get_portfolio_value(self) -> float:
        acct = self._get(
            self.trader_url,
            f"/accounts/{self._account_hash()}",
            {"fields": "positions"},
        )
        return float(
            acct["securitiesAccount"]["currentBalances"]["liquidationValue"]
        )
 
    def get_open_positions(self) -> list[str]:
        acct = self._get(
            self.trader_url,
            f"/accounts/{self._account_hash()}",
            {"fields": "positions"},
        )
        positions = acct["securitiesAccount"].get("positions", [])
        return [p["instrument"]["symbol"] for p in positions]
 
    # ── Order placement ────────────────────────────────────────────────────
 
    def submit_bracket_order(
        self, symbol: str, qty: int, side: str,
        stop_loss: float, take_profit: float,
    ):
        """
        Schwab uses a childOrders list to express bracket (OSO) orders.
        Entry: MARKET order → children: LIMIT (take profit) + STOP (stop loss)
        """
        instruction = "BUY" if side == "buy" else "SELL_SHORT"
        exit_instruction = "SELL" if side == "buy" else "BUY_TO_COVER"
 
        order = {
            "orderType": "MARKET",
            "session": "NORMAL",
            "duration": "DAY",
            "orderStrategyType": "TRIGGER",
            "orderLegCollection": [
                {
                    "instruction": instruction,
                    "quantity": qty,
                    "instrument": {"symbol": symbol, "assetType": "EQUITY"},
                }
            ],
            "childOrderStrategies": [
                {
                    "orderStrategyType": "OCO",
                    "childOrderStrategies": [
                        {
                            # Take-profit leg
                            "orderType": "LIMIT",
                            "session": "NORMAL",
                            "duration": "DAY",
                            "price": round(take_profit, 2),
                            "orderStrategyType": "SINGLE",
                            "orderLegCollection": [
                                {
                                    "instruction": exit_instruction,
                                    "quantity": qty,
                                    "instrument": {"symbol": symbol, "assetType": "EQUITY"},
                                }
                            ],
                        },
                        {
                            # Stop-loss leg
                            "orderType": "STOP",
                            "session": "NORMAL",
                            "duration": "DAY",
                            "stopPrice": round(stop_loss, 2),
                            "orderStrategyType": "SINGLE",
                            "orderLegCollection": [
                                {
                                    "instruction": exit_instruction,
                                    "quantity": qty,
                                    "instrument": {"symbol": symbol, "assetType": "EQUITY"},
                                }
                            ],
                        },
                    ],
                }
            ],
        }
 
        self._post(self.trader_url, f"/accounts/{self._account_hash()}/orders", order)
 
    def close_position(self, symbol: str):
        """Market-sell (or buy-to-cover) all shares of symbol."""
        positions = self._get(
            self.trader_url,
            f"/accounts/{self._account_hash()}",
            {"fields": "positions"},
        )["securitiesAccount"].get("positions", [])
 
        for pos in positions:
            if pos["instrument"]["symbol"] != symbol:
                continue
            qty = int(abs(pos["longQuantity"] or pos.get("shortQuantity", 0)))
            is_short = pos.get("shortQuantity", 0) > 0
            instruction = "BUY_TO_COVER" if is_short else "SELL"
            order = {
                "orderType": "MARKET",
                "session": "NORMAL",
                "duration": "DAY",
                "orderStrategyType": "SINGLE",
                "orderLegCollection": [
                    {
                        "instruction": instruction,
                        "quantity": qty,
                        "instrument": {"symbol": symbol, "assetType": "EQUITY"},
                    }
                ],
            }
            self._post(self.trader_url, f"/accounts/{self._account_hash()}/orders", order)
            return
 
 
# ─── Position Sizing ──────────────────────────────────────────────────────────
 
def calc_qty(portfolio: float, risk_pct: float, entry: float, stop: float) -> int:
    risk_amount = portfolio * (risk_pct / 100)
    risk_per_share = abs(entry - stop)
    if risk_per_share == 0:
        return 0
    qty = int(risk_amount / risk_per_share)
    return max(qty, 1)
 
 
# ─── Trading Engine ───────────────────────────────────────────────────────────
 
class CandleTrader:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.broker = SchwabBroker(cfg)
        self.patterns = CandlePatterns()
        self.open_positions: dict[str, Position] = {}
 
    # ── Helpers ────────────────────────────────────────────────────────────
 
    def _within_trading_hours(self) -> bool:
        now = datetime.now().strftime("%H:%M")
        return self.cfg["TRADE_START"] <= now <= self.cfg["TRADE_END"]
 
    def _already_positioned(self, symbol: str) -> bool:
        broker_positions = self.broker.get_open_positions()
        return symbol in self.open_positions or symbol in broker_positions
 
    # ── Core ───────────────────────────────────────────────────────────────
 
    def analyze(self, symbol: str) -> Optional[Signal]:
        df = self.broker.get_bars(
            symbol, self.cfg["TIMEFRAME"], self.cfg["CANDLES_LOOKBACK"]
        )
        if df.empty or len(df) < 5:
            return None
 
        df = compute_indicators(df, self.cfg["RSI_PERIOD"])
        detections = self.patterns.scan(df)
 
        if not detections:
            return None
 
        # Aggregate signals by direction
        long_signals = [(p, c) for p, d, c in detections if d == "long"]
        short_signals = [(p, c) for p, d, c in detections if d == "short"]
 
        if long_signals and len(long_signals) >= len(short_signals):
            direction = "long"
            pattern_names = " + ".join(p for p, _ in long_signals)
            confidence = sum(c for _, c in long_signals)
        elif short_signals:
            direction = "short"
            pattern_names = " + ".join(p for p, _ in short_signals)
            confidence = sum(c for _, c in short_signals)
        else:
            return None
 
        if not passes_filters(df, direction, self.cfg):
            log.info(f"  {symbol}: pattern '{pattern_names}' filtered out by indicators")
            return None
 
        entry = df.iloc[-1]["close"]
        sl_mult = self.cfg["STOP_LOSS_PCT"] / 100
        tp_mult = self.cfg["TAKE_PROFIT_PCT"] / 100
 
        if direction == "long":
            stop_loss = entry * (1 - sl_mult)
            take_profit = entry * (1 + tp_mult)
        else:
            stop_loss = entry * (1 + sl_mult)
            take_profit = entry * (1 - tp_mult)
 
        return Signal(
            symbol=symbol,
            direction=direction,
            pattern=pattern_names,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
        )
 
    def execute(self, signal: Signal):
        portfolio = self.broker.get_portfolio_value()
        qty = calc_qty(
            portfolio, self.cfg["RISK_PER_TRADE_PCT"],
            signal.entry_price, signal.stop_loss
        )
        if qty == 0:
            log.warning(f"  {signal.symbol}: qty=0, skipping.")
            return
 
        side = "buy" if signal.direction == "long" else "sell"
 
        try:
            self.broker.submit_bracket_order(
                symbol=signal.symbol,
                qty=qty,
                side=side,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
            )
            pos = Position(
                symbol=signal.symbol,
                direction=signal.direction,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                qty=qty,
                pattern=signal.pattern,
            )
            self.open_positions[signal.symbol] = pos
            log.info(
                f"  ✅ ORDER PLACED  {signal.symbol}  {side.upper()}  qty={qty}  "
                f"entry={signal.entry_price:.2f}  SL={signal.stop_loss:.2f}  "
                f"TP={signal.take_profit:.2f}  [{signal.pattern}]"
            )
        except Exception as e:
            log.error(f"  Order failed for {signal.symbol}: {e}")
 
    def run_cycle(self):
        log.info("─" * 60)
        log.info(f"Scanning {len(self.cfg['WATCHLIST'])} symbols…")
 
        open_count = len(self.broker.get_open_positions())
        if open_count >= self.cfg["MAX_OPEN_POSITIONS"]:
            log.info(f"Max positions ({self.cfg['MAX_OPEN_POSITIONS']}) reached. Skipping entries.")
            return
 
        signals: list[Signal] = []
 
        for symbol in self.cfg["WATCHLIST"]:
            if self._already_positioned(symbol):
                continue
            try:
                sig = self.analyze(symbol)
                if sig:
                    log.info(
                        f"  📊 {symbol}: {sig.direction.upper()} signal "
                        f"[{sig.pattern}] conf={sig.confidence:.1f}"
                    )
                    signals.append(sig)
            except Exception as e:
                log.error(f"  Error scanning {symbol}: {e}")
 
        # Sort by confidence, take best signals up to remaining slot count
        signals.sort(key=lambda s: s.confidence, reverse=True)
        slots = self.cfg["MAX_OPEN_POSITIONS"] - open_count
 
        for sig in signals[:slots]:
            self.execute(sig)
 
    def run(self):
        log.info("=" * 60)
        log.info("  Candle Pattern Day Trader — Starting")
        log.info(f"  Watchlist : {self.cfg['WATCHLIST']}")
        log.info(f"  Timeframe : {self.cfg['TIMEFRAME']}")
        log.info(f"  Patterns  : Engulfing, Hammer/Star, Doji, Morning/Evening Star, 3-Candle")
        log.info("=" * 60)
 
        while True:
            try:
                if not self.broker.market_is_open():
                    log.info("Market closed. Waiting…")
                    time.sleep(60)
                    continue
 
                if not self._within_trading_hours():
                    log.info(f"Outside trading window ({self.cfg['TRADE_START']}–{self.cfg['TRADE_END']}). Waiting…")
                    time.sleep(60)
                    continue
 
                self.run_cycle()
 
            except KeyboardInterrupt:
                log.info("Shutting down. Goodbye.")
                break
            except Exception as e:
                log.error(f"Unexpected error: {e}")
 
            time.sleep(self.cfg["SCAN_INTERVAL_SEC"])
 
 
# ─── Entry Point ──────────────────────────────────────────────────────────────
 
if __name__ == "__main__":
    trader = CandleTrader(CONFIG)
    trader.run()