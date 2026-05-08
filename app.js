const TICKERS = ["AAPL", "MSFT", "NVDA", "JPM", "XOM"];
const COLORS = {
  AAPL: "#0b7a75",
  MSFT: "#22577a",
  NVDA: "#5b8c2a",
  JPM: "#b88722",
  XOM: "#c24b35",
};

let marketData = generateMarketData();
let selectedTicker = "AAPL";
let chartMode = "price";
let weights = Object.fromEntries(TICKERS.map((ticker) => [ticker, 20]));

const tickerSelect = document.querySelector("#ticker-select");
const focusStats = document.querySelector("#focus-stats");
const priceChart = document.querySelector("#price-chart");
const weightsNode = document.querySelector("#weights");
const portfolioSummary = document.querySelector("#portfolio-summary");
const screenerBody = document.querySelector("#screener-body");
const dataStatus = document.querySelector("#data-status");
const fetchLiveDataButton = document.querySelector("#fetch-live-data");
const useDemoDataButton = document.querySelector("#use-demo-data");

function generateMarketData() {
  const profiles = {
    AAPL: { start: 184, drift: 0.0004, vol: 0.012, wave: 0.018 },
    MSFT: { start: 412, drift: 0.00055, vol: 0.011, wave: 0.014 },
    NVDA: { start: 620, drift: 0.0011, vol: 0.026, wave: 0.03 },
    JPM: { start: 178, drift: 0.00025, vol: 0.01, wave: 0.012 },
    XOM: { start: 103, drift: 0.00015, vol: 0.014, wave: 0.022 },
  };

  const data = {};
  TICKERS.forEach((ticker, tickerIndex) => {
    const profile = profiles[ticker];
    let price = profile.start;
    data[ticker] = [];

    for (let day = 0; day < 180; day += 1) {
      const cycle = Math.sin((day + tickerIndex * 13) / 13) * profile.wave;
      const shock = seededNoise(day, tickerIndex) * profile.vol;
      const jump = day === 72 && ticker === "NVDA" ? 0.11 : 0;
      const slump = day === 121 && ticker === "XOM" ? -0.09 : 0;
      price *= 1 + profile.drift + cycle / 20 + shock + jump + slump;
      data[ticker].push(Number(price.toFixed(2)));
    }
  });
  return data;
}

function seededNoise(day, tickerIndex) {
  const raw = Math.sin(day * 12.9898 + tickerIndex * 78.233) * 43758.5453;
  return (raw - Math.floor(raw) - 0.5) * 2;
}

function pct(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function money(value) {
  return `$${value.toFixed(2)}`;
}

function mean(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function standardDeviation(values) {
  const avg = mean(values);
  const variance = mean(values.map((value) => (value - avg) ** 2));
  return Math.sqrt(variance);
}

function returns(prices) {
  return prices.slice(1).map((price, index) => price / prices[index] - 1);
}

function totalReturn(prices) {
  return prices.at(-1) / prices[0] - 1;
}

function momentum(prices, days = 30) {
  const lookback = Math.min(days, prices.length - 1);
  return prices.at(-1) / prices.at(-lookback) - 1;
}

function annualVolatility(prices) {
  return standardDeviation(returns(prices)) * Math.sqrt(252);
}

function maxDrawdown(prices) {
  let peak = prices[0];
  let worst = 0;
  prices.forEach((price) => {
    peak = Math.max(peak, price);
    worst = Math.min(worst, price / peak - 1);
  });
  return worst;
}

function scoreStock(prices) {
  const returnScore = totalReturn(prices) * 120;
  const momentumScore = momentum(prices) * 90;
  const riskPenalty = annualVolatility(prices) * 45;
  const drawdownPenalty = Math.abs(maxDrawdown(prices)) * 70;
  return Math.round(50 + returnScore + momentumScore - riskPenalty - drawdownPenalty);
}

function getMetrics(ticker) {
  const prices = marketData[ticker];
  return {
    last: prices.at(-1),
    totalReturn: totalReturn(prices),
    momentum: momentum(prices),
    volatility: annualVolatility(prices),
    maxDrawdown: maxDrawdown(prices),
    score: scoreStock(prices),
  };
}

function normalizedSeries(prices) {
  return prices.map((price) => (price / prices[0]) * 100);
}

function drawdownSeries(prices) {
  let peak = prices[0];
  return prices.map((price) => {
    peak = Math.max(peak, price);
    return (price / peak - 1) * 100;
  });
}

function setupControls() {
  tickerSelect.innerHTML = TICKERS.map(
    (ticker) => `<option value="${ticker}">${ticker}</option>`
  ).join("");

  tickerSelect.addEventListener("change", (event) => {
    selectedTicker = event.target.value;
    render();
  });

  document.querySelectorAll("[data-chart-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      chartMode = button.dataset.chartMode;
      document
        .querySelectorAll("[data-chart-mode]")
        .forEach((item) => item.classList.toggle("active", item === button));
      drawChart();
    });
  });

  document.querySelector("#reset-weights").addEventListener("click", () => {
    weights = Object.fromEntries(TICKERS.map((ticker) => [ticker, 20]));
    renderWeights();
    renderPortfolio();
  });

  fetchLiveDataButton.addEventListener("click", loadLiveData);

  useDemoDataButton.addEventListener("click", () => {
    marketData = generateMarketData();
    dataStatus.textContent = "Demo data is loaded.";
    render();
  });
}

function stooqSymbol(ticker) {
  return `${ticker.toLowerCase()}.us`;
}

function parseStooqCsv(csvText) {
  const rows = csvText.trim().split("\n").slice(1);
  return rows
    .map((row) => {
      const [, , , , close] = row.split(",");
      return Number(close);
    })
    .filter((price) => Number.isFinite(price) && price > 0);
}

async function fetchStooqPrices(ticker) {
  const url = `https://stooq.com/q/d/l/?s=${stooqSymbol(ticker)}&i=d`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`${ticker} returned HTTP ${response.status}`);
  }

  const csvText = await response.text();
  const prices = parseStooqCsv(csvText).slice(-180);

  if (prices.length < 45) {
    throw new Error(`${ticker} did not return enough price history`);
  }

  return prices;
}

async function loadLiveData() {
  fetchLiveDataButton.disabled = true;
  dataStatus.textContent = "Fetching daily prices from Stooq...";

  try {
    const liveData = {};
    const results = await Promise.all(
      TICKERS.map(async (ticker) => [ticker, await fetchStooqPrices(ticker)])
    );

    results.forEach(([ticker, prices]) => {
      liveData[ticker] = prices;
    });

    marketData = liveData;
    dataStatus.textContent = `Live Stooq data loaded for ${TICKERS.length} tickers.`;
    render();
  } catch (error) {
    dataStatus.textContent = `Live fetch failed: ${error.message}. Demo data is still loaded.`;
  } finally {
    fetchLiveDataButton.disabled = false;
  }
}

function renderFocusStats() {
  const metrics = getMetrics(selectedTicker);
  focusStats.innerHTML = [
    ["Last price", money(metrics.last)],
    ["Total return", pct(metrics.totalReturn)],
    ["30-day momentum", pct(metrics.momentum)],
    ["Annual volatility", pct(metrics.volatility)],
    ["Max drawdown", pct(metrics.maxDrawdown)],
    ["Model score", metrics.score.toString()],
  ]
    .map(
      ([label, value]) =>
        `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`
    )
    .join("");
}

function renderWeights() {
  weightsNode.innerHTML = TICKERS.map(
    (ticker) => `
      <label class="weight-row">
        <span>${ticker}</span>
        <input type="range" min="0" max="100" value="${weights[ticker]}" data-weight="${ticker}">
        <strong>${weights[ticker]}%</strong>
      </label>
    `
  ).join("");

  weightsNode.querySelectorAll("[data-weight]").forEach((input) => {
    input.addEventListener("input", (event) => {
      weights[event.target.dataset.weight] = Number(event.target.value);
      renderWeights();
      renderPortfolio();
    });
  });
}

function portfolioReturns() {
  const totalWeight = Object.values(weights).reduce((sum, value) => sum + value, 0) || 1;
  const weighted = TICKERS.map((ticker) => {
    const tickerReturns = returns(marketData[ticker]);
    const weight = weights[ticker] / totalWeight;
    return tickerReturns.map((value) => value * weight);
  });

  return weighted[0].map((_, index) =>
    weighted.reduce((sum, series) => sum + series[index], 0)
  );
}

function renderPortfolio() {
  const pReturns = portfolioReturns();
  const cumulativeReturn = pReturns.reduce((value, dailyReturn) => value * (1 + dailyReturn), 1) - 1;
  const vol = standardDeviation(pReturns) * Math.sqrt(252);
  const dailyAvg = mean(pReturns);
  const sharpe = vol === 0 ? 0 : (dailyAvg * 252) / vol;
  const bestContributor = TICKERS.map((ticker) => ({
    ticker,
    contribution: totalReturn(marketData[ticker]) * weights[ticker],
  })).sort((a, b) => b.contribution - a.contribution)[0].ticker;

  portfolioSummary.innerHTML = [
    ["Portfolio return", pct(cumulativeReturn)],
    ["Annual volatility", pct(vol)],
    ["Simple Sharpe", sharpe.toFixed(2)],
    ["Top contributor", bestContributor],
  ]
    .map(
      ([label, value]) =>
        `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`
    )
    .join("");
}

function renderScreener() {
  const rows = TICKERS.map((ticker) => ({ ticker, ...getMetrics(ticker) })).sort(
    (a, b) => b.score - a.score
  );

  screenerBody.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td><strong>${row.ticker}</strong></td>
          <td class="${row.totalReturn >= 0 ? "positive" : "negative"}">${pct(row.totalReturn)}</td>
          <td class="${row.momentum >= 0 ? "positive" : "negative"}">${pct(row.momentum)}</td>
          <td>${pct(row.volatility)}</td>
          <td class="negative">${pct(row.maxDrawdown)}</td>
          <td><span class="badge">${row.score}</span></td>
        </tr>
      `
    )
    .join("");
}

function drawChart() {
  const context = priceChart.getContext("2d");
  const rect = priceChart.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  priceChart.width = Math.floor(rect.width * scale);
  priceChart.height = Math.floor(rect.height * scale);
  context.scale(scale, scale);

  const width = rect.width;
  const height = rect.height;
  const padding = { top: 24, right: 22, bottom: 34, left: 48 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const seriesByTicker = TICKERS.map((ticker) => ({
    ticker,
    values:
      chartMode === "price"
        ? normalizedSeries(marketData[ticker])
        : drawdownSeries(marketData[ticker]),
  }));

  const allValues = seriesByTicker.flatMap((series) => series.values);
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const range = max - min || 1;

  context.clearRect(0, 0, width, height);
  context.strokeStyle = "#d9ded8";
  context.lineWidth = 1;
  context.fillStyle = "#64706e";
  context.font = "12px Inter, system-ui, sans-serif";

  for (let i = 0; i <= 4; i += 1) {
    const y = padding.top + (plotHeight * i) / 4;
    const value = max - (range * i) / 4;
    context.beginPath();
    context.moveTo(padding.left, y);
    context.lineTo(width - padding.right, y);
    context.stroke();
    context.fillText(chartMode === "price" ? value.toFixed(0) : `${value.toFixed(0)}%`, 8, y + 4);
  }

  seriesByTicker.forEach((series) => {
    context.beginPath();
    series.values.forEach((value, index) => {
      const x = padding.left + (index / (series.values.length - 1)) * plotWidth;
      const y = padding.top + ((max - value) / range) * plotHeight;
      if (index === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    });
    context.strokeStyle = COLORS[series.ticker];
    context.lineWidth = series.ticker === selectedTicker ? 3 : 1.8;
    context.globalAlpha = series.ticker === selectedTicker ? 1 : 0.38;
    context.stroke();
  });

  context.globalAlpha = 1;
  TICKERS.forEach((ticker, index) => {
    context.fillStyle = COLORS[ticker];
    context.fillRect(padding.left + index * 78, height - 18, 12, 12);
    context.fillStyle = "#18201f";
    context.fillText(ticker, padding.left + 18 + index * 78, height - 8);
  });
}

function render() {
  renderFocusStats();
  renderWeights();
  renderPortfolio();
  renderScreener();
  drawChart();
}

setupControls();
render();
window.addEventListener("resize", drawChart);
