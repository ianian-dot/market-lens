import base64
import os
from datetime import datetime
from typing import Union
from xml.etree import ElementTree

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


DEFAULT_TICKERS = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "NVDA",
    "TSLA",
    "NFLX",
    "JPM",
    "V",
    "XOM",
    "COST",
]
TIME_PERIODS = {
    "1 month": {"yahoo_range": "1mo", "business_days": 22},
    "3 months": {"yahoo_range": "3mo", "business_days": 63},
    "6 months": {"yahoo_range": "6mo", "business_days": 126},
    "1 year": {"yahoo_range": "1y", "business_days": 252},
    "2 years": {"yahoo_range": "2y", "business_days": 504},
    "5 years": {"yahoo_range": "5y", "business_days": 1260},
}
BENCHMARK_OPTIONS = {
    "S&P 500 ETF (SPY)": "SPY",
    "Nasdaq 100 ETF (QQQ)": "QQQ",
    "Vanguard Total World (VT)": "VT",
    "Vanguard S&P 500 (VOO)": "VOO",
    "iShares MSCI World (URTH)": "URTH",
}
POPULAR_STOCKS = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "meta": "META",
    "facebook": "META",
    "nvidia": "NVDA",
    "tesla": "TSLA",
    "netflix": "NFLX",
    "jpmorgan": "JPM",
    "jp morgan": "JPM",
    "visa": "V",
    "exxon": "XOM",
    "exxon mobil": "XOM",
    "costco": "COST",
    "berkshire": "BRK-B",
    "berkshire hathaway": "BRK-B",
    "eli lilly": "LLY",
    "lilly": "LLY",
    "novo nordisk": "NVO",
    "walmart": "WMT",
    "disney": "DIS",
    "coca cola": "KO",
    "coke": "KO",
    "pepsi": "PEP",
    "mcdonalds": "MCD",
    "mcdonald's": "MCD",
    "palantir": "PLTR",
    "amd": "AMD",
    "advanced micro devices": "AMD",
    "broadcom": "AVGO",
    "oracle": "ORCL",
    "salesforce": "CRM",
    "adobe": "ADBE",
    "spotify": "SPOT",
    "uber": "UBER",
    "coinbase": "COIN",
}
TRADING_212_BASE_URLS = {
    "Live / real money": "https://live.trading212.com/api/v0",
}


st.set_page_config(page_title="Market Lens", page_icon="ML", layout="wide")

if "watchlist" not in st.session_state:
    st.session_state.watchlist = DEFAULT_TICKERS.copy()


def resolve_symbol(query: str) -> str:
    cleaned = query.strip()
    common_name = cleaned.lower()
    if common_name in POPULAR_STOCKS:
        return POPULAR_STOCKS[common_name]

    return cleaned.upper().replace(".", "-")


def add_ticker(query: str) -> None:
    symbol = resolve_symbol(query)
    if not symbol:
        return

    if symbol not in st.session_state.watchlist:
        st.session_state.watchlist.append(symbol)


def reset_watchlist() -> None:
    st.session_state.watchlist = DEFAULT_TICKERS.copy()


def seeded_noise(day: int, ticker_index: int) -> float:
    raw = __import__("math").sin(day * 12.9898 + ticker_index * 78.233) * 43758.5453
    return (raw - int(raw) - 0.5) * 2


def generate_demo_prices(tickers: list[str], business_days: int) -> pd.DataFrame:
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=business_days)
    prices = pd.DataFrame(index=dates)

    for ticker_index, ticker in enumerate(tickers):
        profile = demo_profile(ticker, ticker_index)
        price = profile["start"]
        values = []

        for day in range(len(dates)):
            cycle = __import__("math").sin((day + ticker_index * 13) / 13) * profile["wave"]
            shock = seeded_noise(day, ticker_index) * profile["vol"]
            jump = 0.11 if day == 72 and ticker == "NVDA" else 0
            slump = -0.09 if day == 121 and ticker == "XOM" else 0
            price *= 1 + profile["drift"] + cycle / 20 + shock + jump + slump
            values.append(round(price, 2))

        prices[ticker] = values

    return prices


def demo_profile(ticker: str, ticker_index: int) -> dict[str, float]:
    known_profiles = {
        "AAPL": {"start": 184, "drift": 0.0004, "vol": 0.012, "wave": 0.018},
        "MSFT": {"start": 412, "drift": 0.00055, "vol": 0.011, "wave": 0.014},
        "GOOGL": {"start": 168, "drift": 0.00045, "vol": 0.014, "wave": 0.018},
        "AMZN": {"start": 183, "drift": 0.0005, "vol": 0.017, "wave": 0.019},
        "META": {"start": 496, "drift": 0.00065, "vol": 0.019, "wave": 0.021},
        "NVDA": {"start": 620, "drift": 0.0011, "vol": 0.026, "wave": 0.03},
        "TSLA": {"start": 238, "drift": 0.0002, "vol": 0.031, "wave": 0.028},
        "NFLX": {"start": 620, "drift": 0.00045, "vol": 0.021, "wave": 0.02},
        "JPM": {"start": 178, "drift": 0.00025, "vol": 0.01, "wave": 0.012},
        "V": {"start": 275, "drift": 0.00035, "vol": 0.011, "wave": 0.013},
        "XOM": {"start": 103, "drift": 0.00015, "vol": 0.014, "wave": 0.022},
        "COST": {"start": 720, "drift": 0.0004, "vol": 0.012, "wave": 0.012},
    }

    if ticker in known_profiles:
        return known_profiles[ticker]

    base = 80 + (sum(ord(character) for character in ticker) % 420)
    return {
        "start": float(base),
        "drift": 0.00015 + (ticker_index % 7) * 0.00008,
        "vol": 0.01 + (ticker_index % 5) * 0.004,
        "wave": 0.012 + (ticker_index % 6) * 0.003,
    }


@st.cache_data(ttl=60 * 30)
def fetch_yahoo_prices(tickers: tuple[str, ...], yahoo_range: str) -> pd.DataFrame:
    frames = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for ticker in tickers:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {"range": yahoo_range, "interval": "1d"}
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()

        payload = response.json()
        result = payload.get("chart", {}).get("result")
        if not result:
            error = payload.get("chart", {}).get("error", {})
            message = error.get("description", "Yahoo returned no chart data")
            raise ValueError(f"{ticker}: {message}")

        chart = result[0]
        timestamps = chart.get("timestamp", [])
        closes = chart.get("indicators", {}).get("quote", [{}])[0].get("close", [])

        ticker_prices = pd.DataFrame(
            {"Date": pd.to_datetime(timestamps, unit="s").date, ticker: closes}
        )
        ticker_prices = ticker_prices.dropna().set_index("Date")
        frames.append(ticker_prices)

    prices = pd.concat(frames, axis=1).dropna()

    if len(prices) < 10:
        raise ValueError("Live source returned too few shared trading days.")

    return prices


@st.cache_data(ttl=60 * 30)
def fetch_yahoo_prices_loose(tickers: tuple[str, ...], yahoo_range: str) -> pd.DataFrame:
    frames = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for ticker in tickers:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            params = {"range": yahoo_range, "interval": "1d"}
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            payload = response.json()
            result = payload.get("chart", {}).get("result")
            if not result:
                continue

            chart = result[0]
            timestamps = chart.get("timestamp", [])
            closes = chart.get("indicators", {}).get("quote", [{}])[0].get("close", [])
            ticker_prices = pd.DataFrame(
                {"Date": pd.to_datetime(timestamps, unit="s").date, ticker: closes}
            )
            ticker_prices = ticker_prices.dropna().set_index("Date")
            if not ticker_prices.empty:
                frames.append(ticker_prices)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, axis=1).dropna()


@st.cache_data(ttl=60 * 15)
def fetch_yahoo_news(ticker: str, limit: int = 5) -> list[dict[str, str]]:
    url = "https://feeds.finance.yahoo.com/rss/2.0/headline"
    response = requests.get(
        url,
        params={"s": ticker, "region": "US", "lang": "en-US"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    response.raise_for_status()

    root = ElementTree.fromstring(response.text)
    articles = []
    for item in root.findall("./channel/item")[:limit]:
        articles.append(
            {
                "title": item.findtext("title", default="Untitled"),
                "link": item.findtext("link", default=""),
                "published": item.findtext("pubDate", default=""),
                "summary": item.findtext("description", default=""),
                "ticker": ticker,
            }
        )

    return articles


def dedupe_articles(articles: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    unique_articles = []
    for article in articles:
        key = article["link"] or article["title"]
        if key in seen:
            continue
        seen.add(key)
        unique_articles.append(article)
    return unique_articles


def returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change().dropna()


def total_return(prices: pd.Series) -> float:
    return prices.iloc[-1] / prices.iloc[0] - 1


def momentum(prices: pd.Series, days: int = 30) -> float:
    lookback = min(days, len(prices) - 1)
    return prices.iloc[-1] / prices.iloc[-lookback] - 1


def annual_volatility(prices: pd.Series) -> float:
    return prices.pct_change().dropna().std() * (252**0.5)


def max_drawdown(prices: pd.Series) -> float:
    running_peak = prices.cummax()
    drawdown = prices / running_peak - 1
    return drawdown.min()


def momentum_score(prices: pd.Series, momentum_days: int) -> int:
    score = (
        50
        + total_return(prices) * 120
        + momentum(prices, momentum_days) * 90
        - annual_volatility(prices) * 45
        - abs(max_drawdown(prices)) * 70
    )
    return round(score)


def rebound_score(prices: pd.Series, momentum_days: int) -> int:
    score = (
        50
        - total_return(prices) * 40
        - momentum(prices, momentum_days) * 35
        + abs(max_drawdown(prices)) * 120
        - annual_volatility(prices) * 20
    )
    return round(score)


def quality_score(prices: pd.Series, momentum_days: int) -> int:
    score = (
        50
        + total_return(prices) * 60
        + momentum(prices, momentum_days) * 30
        - annual_volatility(prices) * 70
        - abs(max_drawdown(prices)) * 95
    )
    return round(score)


def score_explanation(style: str, momentum_column: str) -> str:
    if style == "Momentum":
        return f"""
```text
Momentum Score = 50
               + 120 * Total Return
               +  90 * {momentum_column}
               -  45 * Annual Volatility
               -  70 * abs(Max Drawdown)
```

- Higher return helps.
- Higher recent momentum helps.
- Higher volatility hurts.
- Deeper drawdown hurts.

This is a trend-following score, not a value score.
"""

    if style == "Rebound / drawdown proxy":
        return f"""
```text
Rebound Score = 50
              -  40 * Total Return
              -  35 * {momentum_column}
              + 120 * abs(Max Drawdown)
              -  20 * Annual Volatility
```

- Recent weakness helps.
- Bigger drawdowns help.
- Volatility still hurts a bit.

This is only a **mean-reversion proxy**, not true value investing.
It finds beaten-down names, but it cannot tell cheap from broken.
"""

    return f"""
```text
Price Quality Score = 50
                    +  60 * Total Return
                    +  30 * {momentum_column}
                    -  70 * Annual Volatility
                    -  95 * abs(Max Drawdown)
```

- Positive return helps.
- Positive momentum helps a little.
- High volatility hurts a lot.
- Deep drawdowns hurt a lot.

This favors steadier compounder-type price paths.
"""


def build_screener(prices: pd.DataFrame, style: str) -> pd.DataFrame:
    momentum_days = min(30, len(prices) - 1)
    rows = []
    for ticker in prices.columns:
        series = prices[ticker]
        if style == "Momentum":
            score = momentum_score(series, momentum_days)
        elif style == "Rebound / drawdown proxy":
            score = rebound_score(series, momentum_days)
        else:
            score = quality_score(series, momentum_days)

        rows.append(
            {
                "Ticker": ticker,
                "Last price": series.iloc[-1],
                "Total return": total_return(series),
                f"{momentum_days}-day momentum": momentum(series),
                "Annual vol": annual_volatility(series),
                "Max drawdown": max_drawdown(series),
                "Score": score,
            }
        )

    return pd.DataFrame(rows).sort_values("Score", ascending=False)


def build_score_overview(prices: pd.DataFrame) -> pd.DataFrame:
    momentum_days = min(30, len(prices) - 1)
    rows = []
    for ticker in prices.columns:
        series = prices[ticker]
        rows.append(
            {
                "Ticker": ticker,
                "Momentum score": momentum_score(series, momentum_days),
                "Rebound score": rebound_score(series, momentum_days),
                "Price quality score": quality_score(series, momentum_days),
            }
        )

    return pd.DataFrame(rows).sort_values("Momentum score", ascending=False)


def normalize_prices(prices: pd.DataFrame) -> pd.DataFrame:
    return prices / prices.iloc[0] * 100


def portfolio_stats(prices: pd.DataFrame, weights: dict[str, float]) -> dict[str, Union[float, str]]:
    clean_weights = pd.Series(weights, dtype=float).reindex(prices.columns).fillna(0)
    clean_weights = clean_weights / clean_weights.sum() if clean_weights.sum() else clean_weights
    portfolio_returns = returns(prices).mul(clean_weights, axis=1).sum(axis=1)
    cumulative_return = (1 + portfolio_returns).prod() - 1
    volatility = portfolio_returns.std() * (252**0.5)
    sharpe = 0 if volatility == 0 else (portfolio_returns.mean() * 252) / volatility
    contributions = prices.apply(total_return) * clean_weights

    return {
        "Portfolio return": cumulative_return,
        "Annual volatility": volatility,
        "Simple Sharpe": sharpe,
        "Top contributor": contributions.idxmax(),
    }


def trading_212_headers(api_key: str, api_secret: str) -> dict[str, str]:
    token = base64.b64encode(f"{api_key}:{api_secret}".encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def trading_212_get(base_url: str, path: str, api_key: str, api_secret: str):
    response = requests.get(
        f"{base_url}{path}",
        headers=trading_212_headers(api_key, api_secret),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def get_secret(name: str, default: str = "") -> str:
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.environ.get(name, default)


def format_optional_money(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return str(value)


def coalesce_first(flattened: pd.DataFrame, column_names: list[str], default="") -> pd.Series:
    series = pd.Series([default] * len(flattened), index=flattened.index, dtype="object")
    for column_name in column_names:
        if column_name in flattened.columns:
            candidate = flattened[column_name]
            if isinstance(candidate, pd.DataFrame):
                candidate = candidate.iloc[:, 0]
            series = series.where(series.notna() & (series != "") & (series != 0), candidate)
    return series.fillna(default)


def coalesce_numeric(flattened: pd.DataFrame, column_names: list[str]) -> pd.Series:
    series = pd.Series([pd.NA] * len(flattened), index=flattened.index, dtype="object")
    for column_name in column_names:
        if column_name in flattened.columns:
            candidate = flattened[column_name]
            if isinstance(candidate, pd.DataFrame):
                candidate = candidate.iloc[:, 0]
            candidate = pd.to_numeric(candidate, errors="coerce")
            series = pd.Series(series, index=flattened.index).fillna(candidate)
    return pd.to_numeric(series, errors="coerce")


def normalize_trading_212_positions(positions: list[dict]) -> pd.DataFrame:
    if not positions:
        return pd.DataFrame()

    flattened = pd.json_normalize(positions, sep="_")

    normalized = pd.DataFrame(index=flattened.index)
    normalized["Ticker"] = coalesce_first(
        flattened,
        ["instrument_ticker", "ticker", "symbol", "instrument.symbol"],
    )
    normalized["Name"] = coalesce_first(
        flattened,
        ["instrument_name", "name", "instrumentName", "instrument.name"],
    )
    normalized["Instrument currency"] = coalesce_first(
        flattened,
        ["instrument_currency", "currency", "instrumentCurrency"],
    )
    normalized["ISIN"] = coalesce_first(
        flattened,
        ["instrument_isin", "isin", "instrumentIsin"],
    )
    normalized["Quantity"] = coalesce_numeric(
        flattened,
        ["quantity", "qty", "filledQuantity", "positionQuantity"],
    ).fillna(0)
    normalized["Average price"] = coalesce_numeric(
        flattened,
        ["averagePrice", "averagePricePaid", "avgPrice", "averageCost", "openPrice", "price"],
    )
    normalized["Current price"] = coalesce_numeric(
        flattened,
        ["currentPrice", "lastPrice", "marketPrice", "currentRate"],
    )
    normalized["Market value"] = coalesce_numeric(
        flattened,
        [
            "currentValue",
            "walletImpact_currentValue",
            "value",
            "marketValue",
            "positionValue",
        ],
    )
    normalized["Unrealized P&L"] = coalesce_numeric(
        flattened,
        [
            "ppl",
            "unrealizedPpl",
            "unrealizedProfitLoss",
            "walletImpact_unrealizedProfitLoss",
            "profitLoss",
            "pnl",
        ],
    )
    normalized["Account currency"] = coalesce_first(
        flattened,
        ["walletImpact_currency"],
        default="",
    )
    normalized["Frontend"] = coalesce_first(flattened, ["frontend"], default="")
    normalized["Pie quantity"] = coalesce_numeric(flattened, ["pieQuantity"]).fillna(0)
    normalized["Initial fill date"] = coalesce_first(
        flattened,
        ["initialFillDate", "createdAt", "openedAt"],
        default="",
    )

    if normalized["Average price"].isna().all() and normalized["Market value"].notna().any():
        normalized["Average price"] = normalized["Market value"] / normalized["Quantity"].replace(0, pd.NA)

    if normalized["Current price"].isna().all() and normalized["Market value"].notna().any():
        normalized["Current price"] = normalized["Market value"] / normalized["Quantity"].replace(0, pd.NA)

    computed_value = normalized["Quantity"] * normalized["Current price"].fillna(0)
    normalized["Market value"] = normalized["Market value"].fillna(computed_value)
    normalized["Market value"] = normalized["Market value"].where(
        normalized["Market value"] != 0, computed_value
    )

    computed_pnl = normalized["Quantity"] * (
        normalized["Current price"].fillna(0) - normalized["Average price"].fillna(0)
    )
    normalized["Unrealized P&L"] = normalized["Unrealized P&L"].fillna(computed_pnl)
    normalized["Unrealized P&L"] = normalized["Unrealized P&L"].where(
        normalized["Unrealized P&L"] != 0, computed_pnl
    )

    normalized["Value"] = normalized["Market value"].fillna(0)
    normalized["Cost basis"] = (normalized["Quantity"] * normalized["Average price"].fillna(0)).fillna(0)
    normalized["Unrealized return %"] = (
        normalized["Current price"] / normalized["Average price"].replace(0, pd.NA) - 1
    )

    initial_fill_dates = pd.to_datetime(normalized["Initial fill date"], errors="coerce")
    normalized["Initial fill date"] = initial_fill_dates.apply(
        lambda value: value.strftime("%Y-%m-%d") if pd.notna(value) else ""
    )

    preferred_columns = [
        "Ticker",
        "Name",
        "Quantity",
        "Average price",
        "Current price",
        "Cost basis",
        "Value",
        "Unrealized P&L",
        "Unrealized return %",
        "Instrument currency",
        "Account currency",
        "ISIN",
        "Frontend",
        "Pie quantity",
    ]
    normalized = normalized[preferred_columns]

    return normalized


def summarize_trading_212_account(account_summary: dict) -> pd.DataFrame:
    cash = account_summary.get("cash", {}) or {}
    investments = account_summary.get("investments", {}) or {}
    rows = [
        ("Account id", account_summary.get("id")),
        ("Currency", account_summary.get("currency") or account_summary.get("currencyCode")),
        ("Total value", account_summary.get("totalValue")),
        ("Cash available", cash.get("availableToTrade")),
        ("Cash reserved", cash.get("reservedForOrders")),
        ("Cash in pies", cash.get("inPies")),
        ("Investments current value", investments.get("currentValue")),
        ("Investments total cost", investments.get("totalCost")),
        ("Realized P&L", investments.get("realizedProfitLoss")),
        ("Unrealized P&L", investments.get("unrealizedProfitLoss")),
    ]
    summary_df = pd.DataFrame(rows, columns=["Metric", "Value"])
    summary_df["Value"] = summary_df["Value"].apply(format_optional_money)
    return summary_df


def parse_possible_symbol(platform_ticker: str) -> str:
    if not platform_ticker:
        return ""

    cleaned = platform_ticker.replace(".", "-")
    if "_" in cleaned:
        prefix = cleaned.split("_")[0]
        if len(prefix) <= 5:
            return prefix

    return cleaned


@st.cache_data(ttl=60 * 60)
def fetch_company_profile(query: str) -> dict[str, str]:
    if not query:
        return {}

    try:
        ticker = yf.Ticker(query)
        info = ticker.info or {}
        sector = info.get("sectorDisp") or info.get("sector")
        industry = info.get("industryDisp") or info.get("industry")
        symbol = info.get("symbol") or query
        if sector or industry:
            return {
                "Yahoo symbol": symbol,
                "Sector": sector or "Unknown",
                "Industry": industry or "Unknown",
            }
    except Exception:
        pass

    search = yf.Search(query, max_results=5, news_count=0)
    quotes = search.quotes or []
    for quote in quotes:
        symbol = quote.get("symbol")
        if not symbol:
            continue

        sector = quote.get("sectorDisp") or quote.get("sector")
        industry = quote.get("industryDisp") or quote.get("industry")
        if sector or industry:
            return {
                "Yahoo symbol": symbol,
                "Sector": sector or "Unknown",
                "Industry": industry or "Unknown",
            }

    return {}


@st.cache_data(ttl=60 * 60)
def enrich_positions_with_classification(records: tuple[tuple[str, str, str], ...]) -> pd.DataFrame:
    enriched_rows = []
    for platform_ticker, name, isin in records:
        guessed_symbol = parse_possible_symbol(platform_ticker)
        profile = (
            fetch_company_profile(isin)
            or fetch_company_profile(guessed_symbol)
            or fetch_company_profile(name)
        )
        enriched_rows.append(
            {
                "Platform ticker": platform_ticker,
                "Yahoo symbol": profile.get("Yahoo symbol", guessed_symbol or ""),
                "Sector": profile.get("Sector", "Unknown"),
                "Industry": profile.get("Industry", "Unknown"),
            }
        )

    return pd.DataFrame(enriched_rows)


def render_sector_summary(positions_df: pd.DataFrame) -> None:
    if positions_df.empty:
        st.info("No positions available for sector analysis.")
        return

    required_columns = {"Ticker", "Name", "ISIN", "Market value"}
    if not required_columns.issubset(set(positions_df.columns)):
        st.info("Position data is missing fields needed for sector analysis.")
        return

    records = tuple(
        (str(row["Ticker"]), str(row["Name"]), str(row["ISIN"]))
        for _, row in positions_df[["Ticker", "Name", "ISIN"]].fillna("").iterrows()
    )
    merged = build_classified_positions(positions_df, records)

    total_value = merged["Market value"].sum()
    merged["Portfolio weight"] = (
        merged["Market value"] / total_value if total_value else 0
    )

    st.write("Sector exposure")
    sector_summary = (
        merged.groupby("Sector", dropna=False)["Market value"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    if total_value:
        sector_summary["Portfolio weight"] = sector_summary["Market value"] / total_value
    st.dataframe(
        sector_summary.style.format(
            {
                "Market value": "{:,.2f}",
                "Portfolio weight": "{:.1%}",
            },
            na_rep="",
        ),
        width="stretch",
        hide_index=True,
    )

    st.write("Industry exposure")
    industry_summary = (
        merged.groupby(["Sector", "Industry"], dropna=False)["Market value"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    if total_value:
        industry_summary["Portfolio weight"] = industry_summary["Market value"] / total_value
    st.dataframe(
        industry_summary.style.format(
            {
                "Market value": "{:,.2f}",
                "Portfolio weight": "{:.1%}",
            },
            na_rep="",
        ),
        width="stretch",
        hide_index=True,
    )

    top_sector = sector_summary.iloc[0]["Sector"] if not sector_summary.empty else "Unknown"
    top_sector_weight = (
        sector_summary.iloc[0]["Portfolio weight"] if "Portfolio weight" in sector_summary.columns and not sector_summary.empty else 0
    )
    known_weight = merged.loc[merged["Sector"] != "Unknown", "Portfolio weight"].sum()

    st.info(
        f"Your biggest sector exposure is **{top_sector}** at **{top_sector_weight:.1%}** of market value. "
        f"Sector mapping coverage is currently **{known_weight:.1%}** of the portfolio, so some names may still show as Unknown."
    )


def build_classified_positions(
    positions_df: pd.DataFrame, records: tuple[tuple[str, str, str], ...]
) -> pd.DataFrame:
    classifications = enrich_positions_with_classification(records)
    merged = positions_df.merge(
        classifications,
        left_on="Ticker",
        right_on="Platform ticker",
        how="left",
    )
    merged["Sector"] = merged["Sector"].fillna("Unknown")
    merged["Industry"] = merged["Industry"].fillna("Unknown")
    if "Market value" not in merged.columns:
        if {"Quantity", "Current price"}.issubset(merged.columns):
            merged["Market value"] = pd.to_numeric(
                merged["Quantity"], errors="coerce"
            ).fillna(0) * pd.to_numeric(merged["Current price"], errors="coerce").fillna(0)
        else:
            merged["Market value"] = 0.0
    else:
        merged["Market value"] = pd.to_numeric(merged["Market value"], errors="coerce")
        if {"Quantity", "Current price"}.issubset(merged.columns):
            merged["Market value"] = merged["Market value"].fillna(
                pd.to_numeric(merged["Quantity"], errors="coerce").fillna(0)
                * pd.to_numeric(merged["Current price"], errors="coerce").fillna(0)
            )
        merged["Market value"] = merged["Market value"].fillna(0)
    return merged


def render_concentration_risk(merged: pd.DataFrame) -> None:
    if merged.empty:
        st.info("No positions available for concentration analysis.")
        return

    total_value = merged["Market value"].sum()
    if total_value <= 0:
        st.info("Market values are missing, so concentration cannot be computed yet.")
        return

    holdings = merged.copy()
    holdings["Portfolio weight"] = holdings["Market value"] / total_value
    holdings = holdings.sort_values("Portfolio weight", ascending=False)
    holdings["Weight squared"] = holdings["Portfolio weight"] ** 2
    hhi = holdings["Weight squared"].sum()

    metric_cols = st.columns(4)
    metric_cols[0].metric("Top holding", holdings.iloc[0]["Name"])
    metric_cols[1].metric("Top holding weight", f"{holdings.iloc[0]['Portfolio weight']:.1%}")
    metric_cols[2].metric(
        "Top 3 weight", f"{holdings['Portfolio weight'].head(3).sum():.1%}"
    )
    metric_cols[3].metric("HHI", f"{hhi:.3f}")

    st.dataframe(
        holdings[["Ticker", "Name", "Market value", "Portfolio weight"]]
        .style.format(
            {
                "Market value": "{:,.2f}",
                "Portfolio weight": "{:.1%}",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    st.info(
        f"Your top 3 holdings account for **{holdings['Portfolio weight'].head(3).sum():.1%}** of market value. "
        f"The Herfindahl concentration index is **{hhi:.3f}**."
    )


def render_top_winners_losers(positions_df: pd.DataFrame) -> None:
    if positions_df.empty or "Unrealized P&L" not in positions_df.columns:
        st.info("No unrealized P&L data is available yet.")
        return

    table = positions_df.copy()
    table["Unrealized P&L"] = pd.to_numeric(table["Unrealized P&L"], errors="coerce")
    table = table.dropna(subset=["Unrealized P&L"])
    if table.empty:
        st.info("No unrealized P&L data is available yet.")
        return

    display_columns = [
        column
        for column in ["Ticker", "Name", "Value", "Unrealized P&L", "Unrealized return %", "Current price"]
        if column in table.columns
    ]
    winners = table.sort_values("Unrealized P&L", ascending=False).head(5)
    losers = table.sort_values("Unrealized P&L", ascending=True).head(5)

    winner_col, loser_col = st.columns(2)
    with winner_col:
        st.write("Top 5 winners")
        st.dataframe(
            winners[display_columns].style.format(
                {
                    "Value": "{:,.2f}",
                    "Unrealized P&L": "{:,.2f}",
                    "Unrealized return %": "{:.1%}",
                    "Current price": "{:,.2f}",
                },
                na_rep="",
            ),
            width="stretch",
            hide_index=True,
        )
    with loser_col:
        st.write("Top 5 losers")
        st.dataframe(
            losers[display_columns].style.format(
                {
                    "Value": "{:,.2f}",
                    "Unrealized P&L": "{:,.2f}",
                    "Unrealized return %": "{:.1%}",
                    "Current price": "{:,.2f}",
                },
                na_rep="",
            ),
            width="stretch",
            hide_index=True,
        )


def render_money_source_visuals(merged: pd.DataFrame) -> None:
    if merged.empty:
        st.info("No portfolio data is available for contribution visuals yet.")
        return

    visuals = merged.copy()
    for column in ["Market value", "Unrealized P&L"]:
        if column in visuals.columns:
            visuals[column] = pd.to_numeric(visuals[column], errors="coerce").fillna(0)
        else:
            visuals[column] = 0.0
    if "Value" in visuals.columns:
        visuals["Value"] = pd.to_numeric(visuals["Value"], errors="coerce").fillna(0)
    else:
        visuals["Value"] = visuals["Market value"]

    visual_col_1, visual_col_2 = st.columns(2)

    with visual_col_1:
        st.write("Unrealized P&L by holding")
        pnl_chart = (
            visuals.sort_values("Unrealized P&L", ascending=False)
            .head(10)[["Name", "Unrealized P&L"]]
            .set_index("Name")
        )
        if not pnl_chart.empty:
            st.bar_chart(pnl_chart)
        else:
            st.info("No P&L data available for the chart.")

    with visual_col_2:
        st.write("Market value by sector")
        sector_chart = (
            visuals.groupby("Sector", dropna=False)["Value"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .to_frame()
        )
        if not sector_chart.empty:
            st.bar_chart(sector_chart)
        else:
            st.info("No sector data available for the chart.")

    st.write("Top contributors to unrealized P&L")
    pnl_contribution = (
        visuals[["Ticker", "Name", "Unrealized P&L", "Value"]]
        .sort_values("Unrealized P&L", ascending=False)
        .head(10)
    )
    st.dataframe(
        pnl_contribution.style.format(
            {
                "Unrealized P&L": "{:,.2f}",
                "Value": "{:,.2f}",
            },
            na_rep="",
        ),
        width="stretch",
        hide_index=True,
    )


def render_benchmark_comparison(merged: pd.DataFrame, yahoo_range: str) -> None:
    if merged.empty:
        st.info("No positions available for benchmark comparison.")
        return

    total_value = merged["Market value"].sum()
    if total_value <= 0:
        st.info("Market values are missing, so benchmark comparison cannot be computed yet.")
        return

    benchmark_label = st.selectbox("Benchmark", list(BENCHMARK_OPTIONS), key="portfolio_benchmark")
    benchmark_symbol = BENCHMARK_OPTIONS[benchmark_label]

    valid_positions = (
        merged[["Yahoo symbol", "Name", "Market value"]]
        .dropna(subset=["Yahoo symbol"])
        .query("`Yahoo symbol` != ''")
        .groupby("Yahoo symbol", as_index=False)["Market value"]
        .sum()
    )
    if valid_positions.empty:
        st.info("No resolved Yahoo symbols available for benchmark comparison yet.")
        return

    symbols = tuple(valid_positions["Yahoo symbol"].tolist() + [benchmark_symbol])
    price_matrix = fetch_yahoo_prices_loose(symbols, yahoo_range)
    holding_symbols = [symbol for symbol in valid_positions["Yahoo symbol"] if symbol in price_matrix.columns]
    if benchmark_symbol not in price_matrix.columns or not holding_symbols:
        st.info("Could not fetch enough live history to compare against the selected benchmark.")
        return

    weights = (
        valid_positions.set_index("Yahoo symbol")["Market value"]
        .reindex(holding_symbols)
        .fillna(0)
    )
    weights = weights / weights.sum()

    comparison = price_matrix[holding_symbols + [benchmark_symbol]].dropna()
    if comparison.empty:
        st.info("No overlapping trading dates were available for the portfolio and benchmark.")
        return

    normalized = comparison / comparison.iloc[0] * 100
    portfolio_index = normalized[holding_symbols].mul(weights, axis=1).sum(axis=1)
    benchmark_index = normalized[benchmark_symbol]
    comparison_chart = pd.DataFrame(
        {"Portfolio": portfolio_index, benchmark_symbol: benchmark_index},
        index=comparison.index,
    )

    metric_cols = st.columns(4)
    portfolio_return = portfolio_index.iloc[-1] / portfolio_index.iloc[0] - 1
    benchmark_return = benchmark_index.iloc[-1] / benchmark_index.iloc[0] - 1
    excess_return = portfolio_return - benchmark_return
    metric_cols[0].metric("Portfolio return", f"{portfolio_return:.1%}")
    metric_cols[1].metric(f"{benchmark_symbol} return", f"{benchmark_return:.1%}")
    metric_cols[2].metric("Excess return", f"{excess_return:.1%}")
    metric_cols[3].metric("Mapped holdings", f"{weights.sum():.1%}")

    spread = portfolio_index - benchmark_index
    comparison_days = spread.iloc[1:] if len(spread) > 1 else spread
    above_days = int((comparison_days > 0).sum())
    below_days = int((comparison_days < 0).sum())
    tied_days = int((comparison_days == 0).sum())
    total_days = max(len(comparison_days), 1)

    day_cols = st.columns(3)
    day_cols[0].metric("Days above benchmark", f"{above_days}", f"{above_days / total_days:.1%}")
    day_cols[1].metric("Days below benchmark", f"{below_days}", f"{below_days / total_days:.1%}")
    day_cols[2].metric("Days tied", f"{tied_days}", f"{tied_days / total_days:.1%}")

    st.line_chart(comparison_chart)
    st.info(
        f"Benchmark comparison uses **current market-value weights** across the resolved holdings and compares them with **{benchmark_symbol}** over the selected window. "
        f"The day counts exclude the first normalized starting day, where both series begin at 100."
    )


st.title("Market Lens")
st.caption("A Python finance app for learning data ingestion, metrics, and portfolio analysis.")

with st.sidebar:
    st.header("Watchlist")
    st.caption("Add by ticker or common name, for example `GOOG`, `Google`, `AMD`, or `Berkshire`.")
    add_query = st.text_input("Add stock")
    add_col, reset_col = st.columns(2)
    if add_col.button("Add stock"):
        add_ticker(add_query)
    if reset_col.button("Reset list"):
        reset_watchlist()

    chosen_tickers = st.multiselect(
        "Stocks in dashboard",
        options=st.session_state.watchlist,
        default=st.session_state.watchlist,
    )
    if not chosen_tickers:
        st.warning("Select at least one stock.")
        st.stop()

    default_chart_tickers = chosen_tickers[: min(5, len(chosen_tickers))]
    chart_tickers = st.multiselect(
        "Stocks in chart and news",
        options=chosen_tickers,
        default=default_chart_tickers,
        max_selections=5,
        help="Keep this to five or fewer so the chart stays readable.",
    )
    if not chart_tickers:
        st.warning("Select at least one chart stock.")
        st.stop()

    st.header("Data Source")
    st.caption("Live Yahoo Finance data is the default for this dashboard.")
    with st.expander("Fallback / debug options", expanded=False):
        use_demo_mode = st.checkbox(
            "Use demo data instead of live Yahoo data",
            value=False,
            help="Only use this if you are testing the UI or Yahoo data is temporarily unavailable.",
        )
    selected_period = st.selectbox(
        "Time period",
        list(TIME_PERIODS),
        index=2,
        help="All return, risk, drawdown, and chart values are calculated over this selected window.",
    )

    st.header("Trading 212")
    st.caption("Use read-only API permissions while learning. Credentials are not saved by this app.")
    environment = st.selectbox("Environment", list(TRADING_212_BASE_URLS))
    api_key = st.text_input(
        "API key",
        type="password",
        value=get_secret("TRADING212_API_KEY"),
    )
    api_secret = st.text_input(
        "API secret",
        type="password",
        value=get_secret("TRADING212_API_SECRET"),
    )
    connect = st.button("Connect Trading 212")

period_config = TIME_PERIODS[selected_period]
if not use_demo_mode:
    try:
        prices = fetch_yahoo_prices(tuple(chosen_tickers), period_config["yahoo_range"])
        st.success(f"Loaded live Yahoo Finance data for {len(prices.columns)} tickers.")
    except Exception as exc:
        st.error(f"Live Yahoo fetch failed: {exc}")
        st.info("Open the fallback/debug options in the sidebar if you want to switch to demo data.")
        st.stop()
else:
    prices = generate_demo_prices(chosen_tickers, period_config["business_days"])
    st.warning("Demo data mode is enabled. Live prices are currently bypassed.")

focus_ticker = st.selectbox("Focus ticker", list(prices.columns), index=0)
st.caption(
    f"Current analysis window: {selected_period} "
    f"({prices.index.min()} to {prices.index.max()}, {len(prices)} trading days)."
)

screener_style = "Momentum"
screener = build_screener(prices, screener_style)
focus = screener[screener["Ticker"] == focus_ticker].iloc[0]
momentum_column = next(column for column in screener.columns if column.endswith("day momentum"))

metric_cols = st.columns(5)
metric_cols[0].metric("Last price", f"${focus['Last price']:.2f}")
metric_cols[1].metric("Total return", f"{focus['Total return']:.1%}")
metric_cols[2].metric(momentum_column, f"{focus[momentum_column]:.1%}")
metric_cols[3].metric("Annual vol", f"{focus['Annual vol']:.1%}")
metric_cols[4].metric("Max drawdown", f"{focus['Max drawdown']:.1%}")

chart_mode = st.segmented_control("Chart", ["Normalized price", "Drawdown"], default="Normalized price")
chart_prices = prices[chart_tickers]

if chart_mode == "Normalized price":
    st.line_chart(normalize_prices(chart_prices))
else:
    drawdowns = chart_prices / chart_prices.cummax() - 1
    st.line_chart(drawdowns)

st.subheader("Latest news")
news_scope = st.radio(
    "News scope",
    ["Focused stock", "Chart stocks"],
    horizontal=True,
)
news_tickers = [focus_ticker] if news_scope == "Focused stock" else chart_tickers

try:
    articles = []
    for ticker in news_tickers:
        articles.extend(fetch_yahoo_news(ticker, limit=4))

    articles = dedupe_articles(articles)[:8]
    if not articles:
        st.info("No recent Yahoo Finance headlines found for the selected stock(s).")

    for article in articles:
        st.markdown(
            f"**{article['ticker']}** [{article['title']}]({article['link']})  \n"
            f"{article['published']}"
        )
except Exception as exc:
    st.warning(f"News fetch failed: {exc}")

st.subheader("Portfolio lab")
weight_cols = st.columns(len(prices.columns))
weights = {}
for column, ticker in zip(weight_cols, prices.columns):
    weights[ticker] = column.slider(ticker, 0, 100, round(100 / len(prices.columns)))

stats = portfolio_stats(prices, weights)
portfolio_cols = st.columns(4)
portfolio_cols[0].metric("Portfolio return", f"{stats['Portfolio return']:.1%}")
portfolio_cols[1].metric("Annual volatility", f"{stats['Annual volatility']:.1%}")
portfolio_cols[2].metric("Simple Sharpe", f"{stats['Simple Sharpe']:.2f}")
portfolio_cols[3].metric("Top contributor", stats["Top contributor"])

st.subheader("Stock screener")
st.write("Score overview")
score_overview = build_score_overview(prices)
st.dataframe(
    score_overview,
    width="stretch",
    hide_index=True,
)
screener_style = st.segmented_control(
    "Screener style",
    ["Momentum", "Rebound / drawdown proxy", "Price quality"],
    default=screener_style,
)
screener = build_screener(prices, screener_style)
focus = screener[screener["Ticker"] == focus_ticker].iloc[0]
momentum_column = next(column for column in screener.columns if column.endswith("day momentum"))
with st.expander("How the score works", expanded=True):
    st.markdown(score_explanation(screener_style, momentum_column))
    st.markdown(
        """
        For real investing work, I would keep these **price-based styles** separate from
        **fundamental valuation** and **business quality**.

        A cleaner long-term structure is:

        - **Price tab**: return, momentum, volatility, drawdown
        - **Valuation tab**: P/E, EV/EBITDA, free cash flow yield, peer comparisons
        - **Quality tab**: margins, ROIC/ROE, debt, cash flow stability
        """
    )

st.dataframe(
    screener.style.format(
        {
            "Last price": "${:.2f}",
            "Total return": "{:.1%}",
            momentum_column: "{:.1%}",
            "Annual vol": "{:.1%}",
            "Max drawdown": "{:.1%}",
        }
    ),
    width="stretch",
    hide_index=True,
)

st.subheader("Trading 212 connection")
with st.expander("Trading 212 auth steps", expanded=False):
    st.markdown(
        """
        1. In Trading 212, go to **Settings > API (Beta)**.
        2. Accept the risk notice if prompted.
        3. Generate a new API key pair.
        4. Give it a name like `Market Lens`.
        5. Prefer **read-only / account data / history / positions** style permissions.
        6. Copy both:
           - **API Key**
           - **API Secret** (shown only once)

        This app only uses your credentials in memory for read requests and does not save them to disk.
        """
    )
with st.expander("Keep credentials locally", expanded=False):
    st.markdown(
        """
        To avoid retyping your Trading 212 credentials every time, add them locally as either:

        **Option 1: Streamlit secrets**

        Create `.streamlit/secrets.toml` inside this project with:

        ```toml
        TRADING212_API_KEY = "your_api_key"
        TRADING212_API_SECRET = "your_api_secret"
        ```

        **Option 2: Environment variables**

        ```bash
        export TRADING212_API_KEY="your_api_key"
        export TRADING212_API_SECRET="your_api_secret"
        ```

        The app will auto-fill the fields from either source. Keep that file private and do not commit it.
        """
    )

if connect:
    if not api_key or not api_secret:
        st.error("Enter both your API key and API secret first.")
    else:
        try:
            base_url = TRADING_212_BASE_URLS[environment]
            account_summary = trading_212_get(
                base_url, "/equity/account/summary", api_key, api_secret
            )
            positions = trading_212_get(base_url, "/equity/positions", api_key, api_secret)
            st.session_state["t212_environment"] = environment
            st.session_state["t212_account_summary"] = account_summary
            st.session_state["t212_positions"] = positions
            st.success(f"Connected to Trading 212 {environment}.")
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            body = exc.response.text[:400] if exc.response is not None else ""
            st.error(f"Trading 212 request failed with status {status_code}.")
            if body:
                st.code(body)
        except Exception as exc:
            st.error(f"Trading 212 request failed: {exc}")
else:
    st.info(
        "When you are ready, create a Trading 212 API key with read-only permissions "
        "and connect your live Trading 212 portfolio."
    )

if "t212_account_summary" in st.session_state and "t212_positions" in st.session_state:
    account_summary = st.session_state["t212_account_summary"]
    positions = st.session_state["t212_positions"]
    normalized_positions = normalize_trading_212_positions(positions)

    st.success(f"Loaded Trading 212 portfolio from {st.session_state.get('t212_environment', 'selected environment')}.")
    summary_cols = st.columns(4)
    summary_cols[0].metric(
        "Currency",
        account_summary.get("currencyCode")
        or account_summary.get("currency")
        or "Unknown",
    )
    summary_cols[1].metric(
        "Invested",
        format_optional_money(
            account_summary.get("invested")
            or account_summary.get("investments", {}).get("totalCost")
            or account_summary.get("investedValue")
        ),
    )
    summary_cols[2].metric(
        "Result",
        format_optional_money(
            account_summary.get("result")
            or account_summary.get("investments", {}).get("unrealizedProfitLoss")
            or account_summary.get("totalResult")
        ),
    )
    summary_cols[3].metric(
        "Open positions",
        str(len(positions)),
    )

    st.write("Account summary")
    st.dataframe(
        summarize_trading_212_account(account_summary),
        width="stretch",
        hide_index=True,
    )
    with st.expander("Raw account summary JSON", expanded=False):
        st.json(account_summary)
    st.write("Open positions")
    if positions:
        with st.expander("Raw positions JSON", expanded=False):
            st.json(positions[:3] if isinstance(positions, list) else positions)
        st.dataframe(
            normalized_positions.style.format(
                {
                    "Quantity": "{:,.4f}",
                    "Average price": "{:,.2f}",
                    "Current price": "{:,.2f}",
                    "Cost basis": "{:,.2f}",
                    "Value": "{:,.2f}",
                    "Unrealized P&L": "{:,.2f}",
                    "Unrealized return %": "{:.1%}",
                },
                na_rep="",
            ),
            width="stretch",
            hide_index=True,
        )

        st.subheader("Top winners and losers")
        render_top_winners_losers(normalized_positions)

        records = tuple(
            (str(row["Ticker"]), str(row["Name"]), str(row["ISIN"]))
            for _, row in normalized_positions[["Ticker", "Name", "ISIN"]].fillna("").iterrows()
        )
        classified_positions = build_classified_positions(normalized_positions, records)

        st.subheader("Portfolio concentration risk")
        render_concentration_risk(classified_positions)

        st.subheader("Where your money is coming from")
        render_money_source_visuals(classified_positions)

        st.subheader("Benchmark comparison")
        render_benchmark_comparison(classified_positions, period_config["yahoo_range"])

        st.subheader("Portfolio sector summary")
        render_sector_summary(normalized_positions)
    else:
        st.info("No open positions returned for this Trading 212 environment.")

with st.expander("What you are learning in this stage"):
    st.markdown(
        """
        - **Data source switching**: the UI chooses demo data or live Yahoo data.
        - **HTTP requests**: `requests.get(...)` fetches data from an external service.
        - **Parsing**: JSON responses become price dataframes, and RSS XML becomes news articles.
        - **Caching**: `@st.cache_data` avoids refetching on every interaction.
        - **Broker auth**: Trading 212 uses API key + API secret as HTTP Basic Auth.
        - **Separation of concerns**: fetch data first, calculate metrics second, render UI last.
        """
    )

with st.expander("How to integrate your real portfolio"):
    st.markdown(
        """
        Best path for your situation:

        1. **Start with exports, not live brokerage auth**
           - Import Trading 212 CSV exports
           - Import IBKR Flex Query or activity statement exports

        2. **Normalize both brokers into the same schema**
           - positions
           - transactions
           - dividends
           - cash movements

        3. **Build portfolio views on top of the unified data**
           - current holdings
           - cost basis
           - realized vs unrealized P&L
           - country / sector exposure
           - benchmark comparison
           - overlap between IBKR and Trading 212

        4. **Add live broker APIs later**
           - Trading 212 has an official public API for positions and history
           - IBKR is better integrated via Client Portal / Flex Query workflows

        For your setup, I'd treat:

        - **Trading 212** as the legacy / monitor portfolio
        - **IBKR** as the active portfolio

        Then the app can show both separately and as a combined household portfolio.
        """
    )

st.caption(f"Last app render: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
