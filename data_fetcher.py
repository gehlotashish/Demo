import os
import requests
import pandas as pd
from nsepy import get_history
import yfinance as yf
from datetime import datetime, timedelta
import time
import zipfile
from io import BytesIO
import random

# --- Proxy/VPN Support ---
import itertools
PROXIES_ENV = os.getenv('PROXIES', '')
PROXY_LIST = [p.strip() for p in PROXIES_ENV.split(',') if p.strip()]
proxy_cycle = itertools.cycle(PROXY_LIST) if PROXY_LIST else None
current_proxy = [next(proxy_cycle)] if proxy_cycle else [None]

def get_proxy_dict():
    if current_proxy[0]:
        return {"http": current_proxy[0], "https": current_proxy[0]}
    return None

def rotate_proxy():
    if proxy_cycle:
        current_proxy[0] = next(proxy_cycle)
        from logger import log_error
        log_error(f"Proxy switched to: {current_proxy[0]}")

# --- NSE Option Chain Scraper ---
def fetch_nse_option_chain(symbol: str = 'BANKNIFTY') -> pd.DataFrame:
    """
    Scrape live option chain data from NSE India.
    Returns DataFrame with CE/PE, LTP, IV, Volume, OI, etc.
    Handles anti-bot detection using session, headers, and cookies.
    """
    url_map = {
        'BANKNIFTY': 'https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY',
        'NIFTY': 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY',
    }
    url = url_map.get(symbol.upper())
    if not url:
        raise ValueError('Only BANKNIFTY and NIFTY supported')

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.nseindia.com/option-chain",
    }

    session = requests.Session()
    session.headers.update(headers)

    # Get cookies by visiting homepage first
    for _ in range(5):
        try:
            session.get("https://www.nseindia.com", timeout=5, proxies=get_proxy_dict())
            break
        except Exception as e:
            from logger import log_error
            log_error(f"NSE homepage proxy error: {e}")
            rotate_proxy()
            time.sleep(random.uniform(1, 3))

    # Retry logic for API
    for attempt in range(10):
        try:
            resp = session.get(url, timeout=10, proxies=get_proxy_dict())
            if resp.status_code == 200:
                data = resp.json()
                records = []
                for d in data['records']['data']:
                    strike = d.get('strikePrice')
                    ce = d.get('CE', {})
                    pe = d.get('PE', {})
                    records.append({
                        'strike': strike,
                        'CE_LTP': ce.get('lastPrice'),
                        'CE_IV': ce.get('impliedVolatility'),
                        'CE_Volume': ce.get('totalTradedVolume'),
                        'CE_OI': ce.get('openInterest'),
                        'CE_ChangeOI': ce.get('changeinOpenInterest'),
                        'PE_LTP': pe.get('lastPrice'),
                        'PE_IV': pe.get('impliedVolatility'),
                        'PE_Volume': pe.get('totalTradedVolume'),
                        'PE_OI': pe.get('openInterest'),
                        'PE_ChangeOI': pe.get('changeinOpenInterest'),
                    })
                df = pd.DataFrame(records)
                return df
            elif resp.status_code in (403, 429):
                from logger import log_error
                log_error(f"NSE API blocked, rotating proxy. Status: {resp.status_code}")
                rotate_proxy()
                time.sleep(random.uniform(2, 8))
        except Exception as e:
            from logger import log_error
            log_error(f"NSE API proxy error: {e}")
            rotate_proxy()
            time.sleep(random.uniform(2, 8))
    raise Exception('Failed to fetch option chain after retries')

# --- Bhavcopy Downloader ---
def download_bhavcopy(date: datetime) -> pd.DataFrame:
    """
    Download and parse NSE Bhavcopy for given date.
    Returns DataFrame or None if not available (weekend/holiday).
    """
    # Format: https://www1.nseindia.com/content/historical/EQUITIES/2024/MAY/cm06MAY2024bhav.csv.zip
    yyyy = date.strftime('%Y')
    mmm = date.strftime('%b').upper()
    dd = date.strftime('%d')
    url = f"https://www1.nseindia.com/content/historical/EQUITIES/{yyyy}/{mmm}/cm{dd}{mmm}{yyyy}bhav.csv.zip"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www1.nseindia.com/products/content/equities/equities/archieve_eq.htm",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15, proxies=get_proxy_dict())
        if resp.status_code != 200:
            return None
        z = zipfile.ZipFile(BytesIO(resp.content))
        csv_name = z.namelist()[0]
        df = pd.read_csv(z.open(csv_name))
        return df
    except Exception as e:
        from logger import log_error
        log_error(f"Bhavcopy proxy error: {e}")
        rotate_proxy()
        return None

# --- OHLC Fetcher (nsepy/yfinance) ---
def fetch_ohlc(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    """
    Fetch OHLCV data using nsepy or yfinance.
    """
    # Example using yfinance
    try:
        data = yf.download(symbol + ".NS", start=start, end=end, interval="5m")
        return data
    except Exception as e:
        from logger import log_error
        log_error(f"yfinance proxy error: {e}")
        rotate_proxy()
        return pd.DataFrame()

def fetch_ohlc_yfinance(symbol: str = 'BANKNIFTY', interval: str = '5m', lookback: int = 60) -> pd.DataFrame:
    """
    Fetch recent OHLCV data for symbol using yfinance.
    symbol: 'NIFTY' or 'BANKNIFTY'
    interval: '1m', '5m', etc.
    lookback: how many minutes of data (not used, always fetches today)
    Returns DataFrame with OHLCV
    """
    yf_symbol = '^NSEBANK' if symbol.upper() == 'BANKNIFTY' else '^NSEI'
    try:
        df = yf.download(yf_symbol, period='1d', interval=interval, progress=False, auto_adjust=False)
        return df.reset_index()
    except Exception as e:
        from logger import log_error
        log_error(f"yfinance proxy error: {e}")
        rotate_proxy()
        return pd.DataFrame() 