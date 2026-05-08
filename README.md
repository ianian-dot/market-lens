# Market Lens

A small local finance app for learning how data analysis becomes an interactive product.

The original browser version is still here, but the main learning version is now
`streamlit_app.py`.

## What it does

- Generates demo stock prices for five tickers
- Fetches no-key daily stock prices from Yahoo Finance's chart endpoint
- Normalizes prices so different stocks can be compared
- Calculates total return, momentum, annualized volatility, max drawdown, and a simple score
- Lets you adjust portfolio weights and watch risk metrics update
- Draws charts with plain browser Canvas

## Run it

### Python / Streamlit app

From this folder:

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run streamlit_app.py
```

### Plain browser version

```bash
python3 -m http.server 5173
```

Then open `http://localhost:5173`.

## Good next upgrades

- Add a loading spinner and better error states
- Let the user type custom tickers
- Add a correlation matrix
- Add a watchlist
- Add a Python data fetcher for Stooq as an optional API-key provider
- Cache daily data in SQLite
- Add a proper backend with FastAPI

## T212 integration 

### Screenshots

#### Dashboard
![Dashboard](screenshots/Screenshot%202026-05-08%20at%201.45.02%E2%80%AFPM.png)

#### Portfolio
![Portfolio](screenshots/Screenshot%202026-05-08%20at%201.46.40%E2%80%AFPM.png)

#### Benchmark Comparison
![Benchmark Comparison](screenshots/Screenshot%202026-05-08%20at%201.47.28%E2%80%AFPM.png)
