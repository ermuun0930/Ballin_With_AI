# LegisRisk - High-Level Module Catalog

## Overview
LegisRisk is a congressional bill risk analysis system that helps portfolio managers assess legislative risk exposure for stock holdings by classifying bills into GICS sectors and computing composite risk scores.

## Module Structure

```
LegisRisk/
├── LegisRisk.ipynb          # Main production notebook
├── LegisRiskDB.ipynb         # Data collection pipeline (standalone)
├── final_df_conggov.parquet  # Consolidated dataset (output from backend)
├── bills_classified.parquet  # Classified bills (output from classification)
├── bills_with_risk.parquet   # Risk-scored bills (output from risk scoring)
└── legisrisk.db             # Optional SQLite cache (legacy)
```

---

## Core Modules

### 1. **LegisRisk.ipynb** (Main Production Pipeline)
**Purpose:** End-to-end pipeline from data collection to portfolio risk analysis

**Components:**

#### Part 0: Backend - Data Collection & Storage
- **Function:** Fetches and consolidates congressional bill data from multiple sources
- **Inputs:** 
  - `bills_111_119.json` (base bill list)
  - Congress.gov API (6 endpoints)
  - United States Project (legislator metadata)
  - Voteview (ideology scores)
- **Outputs:** `final_df_conggov.parquet` (1000 bills with 74 columns)
- **Key Operations:**
  - Concurrent API fetching (ThreadPoolExecutor, 5 workers)
  - Nested JSON normalization
  - Multi-source data enrichment
- **Dependencies:** `requests`, `polars`, `concurrent.futures`

#### Part 1: Industry Classification
- **Function:** Classifies bills into GICS sectors using LLM
- **Inputs:** `final_df_conggov.parquet`
- **Outputs:** `bills_classified.parquet`
- **Key Operations:**
  - OpenAI API integration (gpt-4o-mini)
  - Few-shot classification prompting
  - Concurrent batch processing (10 workers, 50 bills/chunk)
  - JSON validation and sector mapping
- **Dependencies:** `openai`, `pandas`, `tqdm`
- **Success Rate:** ~87% classification accuracy

#### Part 2: Risk Scoring
- **Function:** Computes composite risk scores based on bill momentum
- **Inputs:** `bills_classified.parquet`, `final_df_conggov.parquet`
- **Outputs:** `bills_with_risk.parquet`
- **Key Operations:**
  - Legislative stage detection (regex-based)
  - Cosponsor counting (handles dict/list/int types)
  - Recency scoring (exponential decay, 180-day half-life)
  - Bipartisan support estimation
  - Weighted composite scoring (40% stage, 25% cosponsors, 20% recency, 15% bipartisan)
- **Dependencies:** `pandas`, `numpy`, `datetime`
- **Output Range:** 0-100 risk score with 5 categorical labels

#### Part 3: Portfolio Analysis
- **Function:** Aggregates bill risk by stock ticker/sector
- **Inputs:** `bills_with_risk.parquet`, ticker-to-sector mapping
- **Outputs:** Ticker-level risk DataFrame
- **Key Operations:**
  - Sector-based bill filtering
  - Confidence-weighted risk averaging
  - Top-N risky bills per ticker
- **Dependencies:** `pandas`, `numpy`

#### Part 4: Analytics & Insights
- **Function:** Comprehensive analytical framework with visualizations
- **Inputs:** `bills_with_risk.parquet`
- **Outputs:** 9-panel visualization dashboard + statistical reports
- **Key Operations:**
  - **Descriptive Analytics:** Summary statistics, distributions
  - **Sector Analysis:** Risk by sector, activity concentration
  - **Regression Analysis:** Linear model to identify risk drivers
  - **Clustering Analysis:** K-means (4 clusters) to segment bills
  - **Correlation Analysis:** Feature relationship heatmap
  - **Visualizations:** Distribution plots, sector charts, scatter plots, correlation heatmap
  - **Key Insights:** Automated insight generation (top predictors, high-risk sectors, concentration metrics)
- **Dependencies:** `pandas`, `numpy`, `matplotlib`, `seaborn`, `sklearn`
- **Models Used:** LinearRegression, KMeans, StandardScaler

---

### 2. **LegisRiskDB.ipynb** (Standalone Data Collection)
**Purpose:** Isolated data collection and consolidation pipeline

**Function:** Alternative implementation of backend data collection
- Identical to Part 0 of main notebook
- Can be run independently to refresh dataset
- Outputs same `final_df_conggov.parquet` format

**Use Case:** 
- Refresh bill data without running full analysis
- Debugging data collection issues
- Testing new API endpoints

---

## Data Flow

```
Congress.gov API
    ↓
LegisRiskDB.ipynb (or Part 0)
    ↓
final_df_conggov.parquet (Raw bills + metadata)
    ↓
Part 1: Classification (OpenAI)
    ↓
bills_classified.parquet (Bills + GICS sectors)
    ↓
Part 2: Risk Scoring (Composite formula)
    ↓
bills_with_risk.parquet (Bills + risk scores)
    ↓
Part 3: Portfolio Analysis (Ticker aggregation)
    ↓
Ticker-level risk assessment
    ↓
Part 4: Analytics (Visualizations + insights)
    ↓
Dashboard + recommendations
```

---

## Supporting Files

### Data Files (Generated)
- `final_df_conggov.parquet` - 1000 bills, 74 columns, ~2MB
- `bills_classified.parquet` - Same + `gics_sectors`, `confidence` columns
- `bills_with_risk.parquet` - Same + 6 risk columns (`risk_score`, `stage_score`, etc.)
- `main_point.parquet` - Congress.gov main endpoint cache
- `actions_point.parquet` - Legislative actions cache
- `cosponsors_point.parquet` - Cosponsor data cache
- `committees_point.parquet` - Committee assignments cache
- `subjects_point.parquet` - Policy subjects cache
- `relatedbills_point.parquet` - Related bills cache

### Documentation Files
- `legisrisk_breakdown.md` - Detailed notebook walkthrough
- `high-level.md` - This file (module catalog)
- `Schemas.md` - Data structure reference
- `backend-high-level.md` - Backend architecture
- `ml-high-level.md` - Risk scoring & classification systems

---

## Technology Stack

**Languages:**
- Python 3.13

**Core Libraries:**
- **Data Processing:** `polars`, `pandas`, `numpy`
- **API Integration:** `requests`, `openai`
- **Concurrency:** `concurrent.futures.ThreadPoolExecutor`
- **Analytics:** `scikit-learn`, `scipy`
- **Visualization:** `matplotlib`, `seaborn`

**External APIs:**
- Congress.gov API (6 endpoints)
- OpenAI API (gpt-4o-mini)
- United States Project (legislator data)
- Voteview (ideology scores)

**Data Formats:**
- Parquet (primary storage)
- JSON (API responses)
- SQLite (optional cache - legacy)

---

## Execution Time Estimates

| Module | Duration | Bottleneck |
|--------|----------|------------|
| Part 0: Data Collection | 15-30 min | Congress.gov API rate limits |
| Part 1: Classification | 2-5 min | OpenAI API calls (1000 bills) |
| Part 2: Risk Scoring | <1 min | CPU-bound pandas apply |
| Part 3: Portfolio Analysis | <5 sec | In-memory operations |
| Part 4: Analytics | 5-10 sec | Matplotlib rendering |
| **Total (cold start)** | **20-40 min** | API dependencies |
| **Total (cached data)** | **3-6 min** | Classification + scoring only |

---

## Key Design Decisions

1. **Parquet over CSV:** 10x compression, preserves types, faster I/O
2. **Polars for ETL:** 5-10x faster than pandas for joins/aggregations
3. **OpenAI over rule-based:** 87% accuracy vs ~60% with keywords
4. **Composite scoring over ML:** Transparent, no training required, instant updates
5. **Concurrent API fetching:** 5x speedup vs sequential
6. **Cell-based notebook:** Interactive exploration, easy debugging

---

## Future Enhancements

**High Priority:**
- [ ] Streamlit dashboard for portfolio input
- [ ] Automated daily data refresh (cron/GitHub Actions)
- [ ] Historical risk tracking over time
- [ ] Bill text summarization (OpenAI)

**Medium Priority:**
- [ ] Cache OpenAI classifications (reduce costs)
- [ ] Add yfinance ticker lookup
- [ ] Email alerts for high-risk bills
- [ ] Export to PDF report

**Low Priority:**
- [ ] ML-based risk prediction (LSTM/Transformer)
- [ ] Multi-congress comparison
- [ ] Network analysis of cosponsor relationships
- [ ] Committee influence scoring

---

## Maintenance Notes

**Weekly:**
- [ ] Check Congress.gov API status
- [ ] Monitor OpenAI usage ($)
- [ ] Review classification accuracy

**Monthly:**
- [ ] Refresh legislator metadata
- [ ] Update ideology scores (Voteview releases quarterly)
- [ ] Audit failed API calls

**Quarterly:**
- [ ] Re-run full pipeline on new congress
- [ ] Validate GICS sector mappings
- [ ] Review risk score distribution

---

## Contact & Attribution

**Project:** LegisRisk - Congressional Bill Risk Analyzer  
**Author:** Balling With AI Group  
**Course:** Stats Project  
**Date:** 2025  

**Data Sources:**
- Congress.gov (official U.S. government data)
- United States Project (open-source legislator database)
- Voteview (DW-NOMINATE ideology scores)

**APIs Used:**
- OpenAI (gpt-4o-mini for classification)
- Congress.gov API (6 endpoints)

**License:** Educational use only
