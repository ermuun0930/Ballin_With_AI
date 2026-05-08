let appData = JSON.parse(
  document.getElementById("initialLegisRiskData").textContent,
);
let stockRiskChart;
let sectorChart;

const riskColor = (score) => {
  if (score >= 55) return "#e55353";
  if (score >= 35) return "#f3b63f";
  return "#22a06b";
};

const sectorColors = [
  "#2563eb",
  "#22a06b",
  "#f3b63f",
  "#e55353",
  "#7c3aed",
  "#0ea5e9",
  "#f97316",
  "#14b8a6",
  "#64748b",
  "#db2777",
  "#84cc16",
];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function riskLabel(score) {
  if (score >= 55) return "High Risk";
  if (score >= 35) return "Moderate";
  return "Low";
}

function renderStockRiskChart() {
  const ctx = document.getElementById("stockRiskChart");
  const stocks = appData.stocks;

  if (stockRiskChart) stockRiskChart.destroy();
  stockRiskChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: stocks.map((stock) => stock.ticker),
      datasets: [
        {
          data: stocks.map((stock) => stock.risk_score),
          backgroundColor: stocks.map((stock) => riskColor(stock.risk_score)),
          borderRadius: 10,
          barThickness: 30,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => `${context.raw} - ${riskLabel(context.raw)}`,
          },
        },
      },
      scales: {
        x: {
          min: 0,
          max: 100,
          grid: { color: "#edf1f6" },
          ticks: { callback: (value) => `${value}` },
        },
        y: {
          grid: { display: false },
          ticks: { color: "#172033", font: { weight: 800 } },
        },
      },
      onClick: (_, elements) => {
        if (!elements.length) return;
        renderStockDrilldown(stocks[elements[0].index]);
      },
    },
    plugins: [
      {
        id: "riskLabels",
        afterDatasetsDraw(chart) {
          const { ctx } = chart;
          const meta = chart.getDatasetMeta(0);
          ctx.save();
          ctx.font = "700 12px Inter, system-ui, sans-serif";
          ctx.fillStyle = "#687385";
          meta.data.forEach((bar, index) => {
            const score = stocks[index].risk_score;
            ctx.fillText(riskLabel(score), bar.x + 8, bar.y + 4);
          });
          ctx.restore();
        },
      },
    ],
  });
}

function renderSectorChart() {
  const ctx = document.getElementById("sectorChart");
  const sectors = appData.sector_exposure;

  if (sectorChart) sectorChart.destroy();
  sectorChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: sectors.map((item) => item.sector),
      datasets: [
        {
          data: sectors.map((item) => item.percentage),
          backgroundColor: sectors.map(
            (_, index) => sectorColors[index % sectorColors.length],
          ),
          borderColor: "#ffffff",
          borderWidth: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => `${context.label}: ${context.raw}%`,
          },
        },
      },
    },
  });

  document.getElementById("sectorLegend").innerHTML = sectors
    .map(
      (item, index) => `
        <div class="legend-item">
          <span><i class="swatch" style="background:${sectorColors[index % sectorColors.length]}"></i>${escapeHtml(item.sector)}</span>
          <span>${item.percentage}%</span>
        </div>
      `,
    )
    .join("");
}

function renderStockDrilldown(stock) {
  // Update dropdown selection
  const stockSelect = document.getElementById("stockSelect");
  if (stockSelect) {
    stockSelect.value = stock.ticker;
  }

  document.getElementById("selectedStockTitle").textContent =
    `${stock.ticker} risk profile`;
  document.getElementById("selectedScore").textContent = stock.risk_score;
  document.getElementById("selectedBills").textContent = stock.affecting_bills;
  document.getElementById("selectedSector").textContent = stock.sector;
  document.getElementById("selectedIndustry").textContent =
    stock.industry || "Unknown";
  document.getElementById("whyThisStock").textContent =
    stock.why_this_stock || "No stock-specific explanation available.";
  document.getElementById("stockThemes").innerHTML = [
    ...(stock.business_lines || []).map((item) => `Business: ${item}`),
    ...(stock.policy_themes || []).map((item) => `Theme: ${item}`),
  ]
    .slice(0, 8)
    .map((item) => `<span class="meta-chip">${escapeHtml(item)}</span>`)
    .join("");

  document.getElementById("breakdownBars").innerHTML = Object.entries(
    stock.breakdown,
  )
    .map(
      ([label, value]) => `
        <div class="breakdown-row">
          <label>${escapeHtml(label)}</label>
          <div class="bar-track"><div class="bar-fill" style="width:${value}%"></div></div>
          <strong>${value}%</strong>
        </div>
      `,
    )
    .join("");

  const billCards = document.getElementById("billCards");
  if (!stock.top_bills.length) {
    billCards.innerHTML = `<div class="bill-card"><p>No mapped bills found for this stock's sector.</p></div>`;
    return;
  }

  billCards.innerHTML = stock.top_bills.map(renderBillCard).join("");
}

function renderBillCard(bill) {
  const subjects = (bill.subjects || [])
    .map((subject) => `<span class="meta-chip">${escapeHtml(subject)}</span>`)
    .join("");
  const sponsors = (bill.sponsors || [])
    .slice(0, 3)
    .map(
      (sponsor) =>
        `${escapeHtml(sponsor.full_name)} (${escapeHtml(sponsor.party || "")}-${escapeHtml(sponsor.state || "")})`,
    )
    .join(", ");
  const actions = (bill.actions || [])
    .slice(0, 4)
    .map(
      (action) =>
        `<li>${escapeHtml(action.action_date || "")}: ${escapeHtml(action.action_text || "")}</li>`,
    )
    .join("");
  const reasons = (bill.match_reasons || [])
    .map((reason) => `<span class="meta-chip">${escapeHtml(reason)}</span>`)
    .join("");

  return `
    <article class="bill-card">
      <div class="bill-card-header">
        <div>
          <h4>${escapeHtml(bill.id)} - ${escapeHtml(bill.title)}</h4>
          <span class="pill ${bill.risk_label.toLowerCase()}">${escapeHtml(bill.risk_label)} (${bill.risk_score})</span>
        </div>
      </div>
      <div class="bill-meta">
        <span class="meta-chip">${escapeHtml(bill.policy_area)}</span>
        <span class="meta-chip">Classified: ${escapeHtml(bill.classification.industry)}</span>
        <span class="meta-chip">Confidence: ${escapeHtml(bill.classification.confidence)}</span>
        <span class="meta-chip">Stock relevance: ${escapeHtml(bill.stock_relevance)}%</span>
        <span class="meta-chip">Bill risk: ${escapeHtml(bill.base_bill_risk)}</span>
        ${subjects}
        ${reasons}
      </div>
      <p><strong>Status:</strong> ${escapeHtml(bill.status)}</p>
      <p><strong>Likely impact:</strong> ${escapeHtml(bill.impact)}</p>
      ${sponsors ? `<p><strong>Sponsors:</strong> ${sponsors}</p>` : ""}
      ${bill.url ? `<a href="${escapeHtml(bill.url)}" target="_blank" rel="noreferrer">Open bill</a>` : ""}
      ${
        actions
          ? `<details class="bill-actions"><summary>Recent bill actions</summary><ul>${actions}</ul></details>`
          : ""
      }
    </article>
  `;
}

function renderInsights() {
  document.getElementById("insightsList").innerHTML = appData.insights
    .map(
      (insight) => `
        <div class="insight ${escapeHtml(insight.level)}">
          <strong>${escapeHtml(insight.title)}</strong>
          <p>${escapeHtml(insight.body)}</p>
        </div>
      `,
    )
    .join("");
}

function renderActivity() {
  document.getElementById("activityFeed").innerHTML = appData.activity_feed
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
}

function renderBackendAnalytics() {
  const analytics = appData.backend_analytics;
  document.getElementById("backendAnalytics").innerHTML = `
    <div><strong>${analytics.bill_count}</strong><span>Bills loaded</span></div>
    <div><strong>${analytics.classified_count}</strong><span>Classified bills</span></div>
    <div><strong>${analytics.risk_mean}</strong><span>Avg bill risk</span></div>
    <div><strong>${analytics.risk_max}</strong><span>Max bill risk</span></div>
  `;
  document.getElementById("componentAverages").innerHTML = Object.entries(
    analytics.component_averages,
  )
    .map(
      ([label, value]) =>
        `<div class="legend-item"><span>${escapeHtml(label)}</span><span>${value}</span></div>`,
    )
    .join("");
}

function renderSummary() {
  document.getElementById("heroSummary").textContent = appData.hero_summary;
  document.getElementById("portfolioScoreOrb").textContent =
    appData.portfolio_score;
  document.getElementById("portfolioScore").textContent =
    appData.portfolio_score;

  const hero = document.getElementById("heroCard");
  hero.classList.remove("low", "moderate", "high");
  hero.classList.add(appData.portfolio_label.toLowerCase());

  const label = document.getElementById("portfolioLabel");
  label.textContent = appData.portfolio_label;
  label.className = `pill ${appData.portfolio_label.toLowerCase()}`;

  const highest = appData.highest_risk_stock;
  document.getElementById("highestRiskStock").textContent = highest
    ? highest.ticker
    : "N/A";
  document.getElementById("highestRiskSector").textContent = highest
    ? highest.sector
    : "No sector";
  document.getElementById("mostExposedSector").textContent =
    appData.most_exposed_sector;
  document.getElementById("topDriver").textContent = appData.top_driver;
}

function renderDashboard() {
  renderSummary();
  renderStockRiskChart();
  renderSectorChart();
  renderInsights();
  renderActivity();
  renderBackendAnalytics();
  if (appData.stocks.length) {
    renderStockDrilldown(appData.stocks[0]);
    // Set initial dropdown value
    const stockSelect = document.getElementById("stockSelect");
    if (stockSelect) {
      stockSelect.value = appData.stocks[0].ticker;
    }
  }
}

function selectStock(ticker) {
  const selectedStock = appData.stocks.find((stock) => stock.ticker === ticker);
  if (selectedStock) {
    renderStockDrilldown(selectedStock);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  renderDashboard();
});
