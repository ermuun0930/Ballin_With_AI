# LegisRisk - Congressional Bill Risk Analyzer: Complete Breakdown

## Project Overview

**LegisRisk** is a comprehensive data product that analyzes legislative risk for stock portfolios. It allows users to input stock tickers and instantly see which pending congressional bills pose regulatory risk to their holdings.

### Core Question

Given someone's stock portfolio, how much legislative risk is each holding exposed to right now?

### Solution Approach

1. Collect pending bills from the 119th Congress via Congress.gov API
2. Classify each bill's industry impact using policy area mappings and keyword analysis
3. Map industries to public companies using GICS sectors via yfinance
4. Compute composite risk scores per ticker based on bill momentum
5. Provide interactive portfolio risk checker via Streamlit web app

---

## System Architecture

The notebook is organized into 7 main parts:

1. **Data Collection** - API calls to Congress.gov, legislator data, ideology scores
2. **Database Setup** - Normalized SQLite database with 5 tables
3. **Industry Classification** - Multi-tier bill-to-GICS sector mapping
4. **Ticker Mapping** - Stock ticker to sector mapping via yfinance
5. **Risk Scoring** - Composite momentum and risk score calculation
6. **Analytics** - Descriptive and advanced statistical analysis
7. **Streamlit App** - Interactive web frontend

---

## Part 1: Data Collection

### Data Sources

#### 1. Congress.gov API

Primary source for congressional bill data. The API has strict rate limiting, requiring ~2 hours to collect a full dataset. The notebook uses a filtered subset of 1000 bills from congresses 111-119 for demonstration.

**Endpoints Used:**

- **Main endpoint**: `/v3/bill/{congress}/{type}/{number}` - Core bill metadata
- **Actions endpoint**: Bill lifecycle actions (introduced, passed, signed, etc.)
- **Cosponsors endpoint**: List of bill cosponsors
- **Committees endpoint**: Committees handling the bill
- **Subjects endpoint**: Policy areas and subject tags
- **Related bills endpoint**: Connected legislation
- **Member endpoint**: Sponsor details and biographical data

**Data Collection Process:**

1. Load base bill list from `bills_111_119.json`
2. Filter to most recent 1000 bills (type, number, congress, originChamber)
3. Use ThreadPoolExecutor for parallel API calls
4. Store results as parquet files for each endpoint
5. Join all data sources into single dataframe

#### 2. Legislator Information Repository

Source: `https://unitedstates.github.io/congress-legislators/legislators-current.json`

Provides comprehensive legislator biographical data including:

- Bioguide IDs (primary key)
- Names, party affiliation
- State representation
- External IDs (OpenSecrets, VoteSmart, FEC, etc.)

#### 3. Voteview Ideology Data

Source: `https://voteview.com/static/data/out/members/HS119_members.json`

Academic dataset providing DW-NOMINATE ideology scores:

- First dimension: Liberal-conservative spectrum
- Second dimension: Historical cross-cutting issues
- Enables quantitative analysis of sponsor ideology

### Data Integration

The notebook performs a complex multi-step join operation:

```
Base bills (congress, type, number)
  → Main endpoint (unnest bill details)
  → Actions (unnest actions array)
  → Cosponsors (unnest cosponsors array)
  → Committees (unnest committees array)
  → Subjects (unnest subjects array)
  → Related bills (unnest related bills array)
  → Legislator info (join on bioguideId)
  → Voteview ideology (join on bioguideId)
```

**Key Technical Challenges:**

- Nested JSON structures require careful unnesting with Polars
- Multiple API calls require unique column suffixes to prevent collisions
- Rate limiting requires ThreadPoolExecutor with error handling

**Output:** `final_df_conggov.parquet` - Comprehensive bill dataset ready for database loading

---

## Part 2: Database Setup

### Database Schema

The notebook creates a normalized SQLite database (`legisrisk.db`) with 5 tables:

#### 1. `bills` Table (Primary)

```sql
CREATE TABLE bills (
    bill_id TEXT PRIMARY KEY,
    congress INTEGER,
    type TEXT,
    number INTEGER,
    title TEXT,
    origin_chamber TEXT,
    introduced_date TEXT,
    latest_action_date TEXT,
    latest_action_text TEXT,
    policy_area TEXT,
    sponsor_bioguide_id TEXT,
    sponsor_name TEXT,
    sponsor_party TEXT,
    sponsor_state TEXT,
    sponsor_ideology_nominate_dim1 REAL,
    sponsor_ideology_nominate_dim2 REAL,
    cosponsors_count INTEGER,
    gics_sectors TEXT,
    confidence REAL
)
```

#### 2. `bill_sponsors` Table

One-to-many relationship: bills → sponsors/cosponsors

- Separates primary sponsor from cosponsors
- Includes party and state for coalition analysis

#### 3. `bill_subjects` Table

One-to-many relationship: bills → subject tags

- Policy area classifications from Congress.gov
- Used for keyword-based industry classification

#### 4. `bill_actions` Table

One-to-many relationship: bills → legislative actions

- Chronological record of bill progress
- Text field used for stage detection (introduced, passed, signed, etc.)

#### 5. `ticker_industries` Table

Cache for yfinance API calls

- Stores ticker → company name → GICS sector mapping
- Prevents repeated API calls for same ticker

### Loading Process

1. Read `final_df_conggov.parquet` with Polars
2. Extract bill metadata into `bills` table
3. Explode nested arrays:
   - Sponsors/cosponsors → `bill_sponsors`
   - Subjects → `bill_subjects`
   - Actions → `bill_actions`
4. Verify data integrity with row counts

**Helper Functions:**

- `drill()` - Navigate nested Polars struct fields safely
- `load_bills()` - Extract core bill metadata
- `load_sponsors()` - Explode sponsor arrays
- `load_subjects()` - Explode subject arrays
- `load_actions()` - Explode action arrays

---

## Part 3: Industry Classification

### Multi-Tier Classification System

The notebook classifies bills into **GICS (Global Industry Classification Standard)** sectors using a tiered approach:

### GICS Sectors (11 total)

1. Energy
2. Materials
3. Industrials
4. Consumer Discretionary
5. Consumer Staples
6. Health Care
7. Financials
8. Information Technology
9. Communication Services
10. Utilities
11. Real Estate

### Tier 1a: Policy Area Mapping

Deterministic mapping from Congress.gov `policyArea` field to GICS sectors with confidence scores.

**Examples:**

- "Health" → ["Health Care"] (0.9 confidence)
- "Finance and Financial Sector" → ["Financials"] (0.9 confidence)
- "Energy" → ["Energy", "Utilities"] (0.9 confidence - bills can affect multiple sectors)
- "Science, Technology, Communications" → ["Information Technology", "Communication Services"] (0.8)
- "Transportation and Public Works" → ["Industrials"] (0.8)
- "Housing and Community Development" → ["Real Estate"] (0.8)
- "Foreign Trade and International Finance" → ["Financials", "Industrials"] (0.7)
- "Economics and Public Finance" → ["Financials"] (0.4 - lower confidence, broader impact)

### Tier 1b: Subject Keyword Mapping

Fallback for bills without clear policy area. Searches subject text for industry-specific keywords.

**Health Care Keywords:**

- prescription drug, health insurance, medicare, medicaid
- pharmaceutical, drug safety, mental health, public health
- hospital, medical, biomedical

**Financials Keywords:**

- securities, banking, financial services, insurance
- credit, interest rate, mortgage, investment

**Information Technology Keywords:**

- software, cybersecurity, artificial intelligence, data privacy
- blockchain, cloud computing, internet, semiconductor

**Energy Keywords:**

- renewable energy, fossil fuel, oil, natural gas
- solar, wind, nuclear, coal

**Consumer Discretionary Keywords:**

- retail, automobile, restaurant, hotel, tourism

**And more for all 11 sectors...**

### Tier 1c: Title Keyword Matching

Additional fallback searching bill title text for keywords.

### Tier 2: LLM Classification (Optional)

For ambiguous or low-confidence bills, optional Claude API integration:

- Sends bill title, policy area, and subjects to Claude
- Requests classification into GICS sectors
- Parses JSON response with sectors and confidence
- Currently disabled by default (`use_llm=False`)

### Classification Algorithm

```python
def classify_all_bills(db_path, use_llm=False):
    1. Query all bills from database
    2. For each bill:
       a. Try policy area mapping (Tier 1a)
       b. If no match, try subject keywords (Tier 1b)
       c. If no match, try title keywords (Tier 1c)
       d. If still no match and use_llm, call Claude API (Tier 2)
    3. Update bills table with GICS sectors and confidence score
    4. Report classification statistics
```

**Output:** `bills.gics_sectors` and `bills.confidence` columns populated

---

## Part 4: Ticker Mapping

### Purpose

Map stock tickers to GICS sectors to match bills with affected companies.

### Implementation

Uses **yfinance** library to fetch company data:

- Company name
- Sector (yfinance format)
- Industry (more granular)

### Sector Name Standardization

yfinance uses non-standard sector names. The notebook maps them to GICS:

```python
YFINANCE_TO_GICS = {
    "Technology": "Information Technology",
    "Healthcare": "Health Care",
    "Financial Services": "Financials",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Communication Services": "Communication Services",
    "Energy": "Energy",
    "Industrials": "Industrials",
    "Basic Materials": "Materials",
    "Real Estate": "Real Estate",
    "Utilities": "Utilities",
}
```

### Caching Strategy

Results are stored in `ticker_industries` table to avoid repeated API calls:

1. Check if ticker exists in database
2. If not, fetch from yfinance
3. Store in database for future use
4. Return standardized GICS sector

### Functions

- `get_ticker_sector(ticker)` - Single ticker lookup with caching
- `get_multiple_tickers(tickers)` - Batch lookup with progress reporting

**Test Example:**

```python
results = get_multiple_tickers(["AAPL", "JPM", "LLY", "XOM"])
# Returns:
# AAPL: Apple Inc. | Information Technology | Consumer Electronics
# JPM: JPMorgan Chase & Co. | Financials | Banks—Diversified
# LLY: Eli Lilly and Company | Health Care | Drug Manufacturers—General
# XOM: Exxon Mobil Corporation | Energy | Oil & Gas Integrated
```

---

## Part 5: Risk Scoring

### Two-Level Scoring System

The notebook implements a sophisticated composite risk scoring system:

#### Level 1: Bill Momentum Score (0-100 per bill)

Measures how far a bill has progressed through the legislative process and its likelihood of becoming law.

**Five Components:**

1. **Legislative Stage (35% weight)**
   - Pattern matching on action text to determine furthest stage reached
   - Scores:
     - Became Public Law: 100
     - Signed by President: 95
     - Presented to President: 90
     - Resolving differences: 85
     - Passed both chambers: 80
     - Passed one chamber: 70
     - Received in other chamber: 65
     - Reported by committee: 50
     - Ordered to be reported: 45
     - Committee hearing/markup: 40
     - Subcommittee action: 30
     - Referred to committee: 20
     - Introduced: 10

2. **Cosponsor Count (25% weight)**
   - More cosponsors = broader support = higher momentum
   - Logarithmic scaling: `log10(cosponsors + 1) / log10(101)`
   - Assumes max ~100 cosponsors for normalization

3. **Bipartisan Support (20% weight)**
   - Measures party diversity among sponsors/cosponsors
   - Uses Gini coefficient: 0 (unanimous party) to 1 (perfect split)
   - Bipartisan bills more likely to advance

4. **Recency of Activity (10% weight)**
   - Recent activity indicates active bill vs. stalled bill
   - Exponential decay: `exp(-days_since_activity / 180)`
   - Half-life of ~180 days (6 months)

5. **Committee Progress (10% weight)**
   - Counts distinct committees handling the bill
   - Multiple committees = broader impact + more hurdles
   - Score: `min(committee_count / 3, 1.0)`

**Formula:**

```python
momentum = (
    0.35 * stage_score +
    0.25 * cosponsor_score +
    0.20 * bipartisan_score +
    0.10 * recency_score +
    0.10 * committee_score
)
```

#### Level 2: Ticker Risk Score

Aggregates momentum across all bills affecting a ticker's sector.

**Algorithm:**

1. Get ticker's GICS sector from `ticker_industries`
2. Query all bills classified to that sector
3. Compute momentum score for each bill
4. Aggregate with weighted average (higher momentum bills weighted more)
5. Normalize to 0-100 scale

**Risk Labels:**

- 0-20: Very Low
- 21-40: Low
- 41-60: Moderate
- 61-80: High
- 81-100: Very High

### Portfolio Risk Analysis

`compute_portfolio_risk(tickers)` function:

1. For each ticker:
   - Get company name and sector
   - Find all relevant bills
   - Calculate ticker risk score
   - Rank bills by momentum
2. Return sorted list (highest risk first)
3. Include top 5 bills per ticker with details

**Output Format:**

```python
{
    "ticker": "AAPL",
    "company": "Apple Inc.",
    "sector": "Information Technology",
    "risk_score": 67.4,
    "risk_label": "High",
    "bill_count": 43,
    "top_bills": [
        {
            "bill_id": "hr-119-1234",
            "title": "AI Regulation Act",
            "momentum": 78.2,
            "stage": "Passed House",
            "cosponsors": 87,
            "introduced_date": "2024-02-15"
        },
        ...
    ]
}
```

---

## Part 6: Analytics

### Descriptive Analytics

#### 1. Bills by Policy Area

**Type:** Bar chart
**Purpose:** Show distribution of bills across policy areas
**Method:** Count bills grouped by `policy_area`, sort descending
**Insight:** Identifies which legislative areas are most active

#### 2. Legislative Stage Funnel

**Type:** Funnel chart (Plotly)
**Purpose:** Visualize bill attrition through legislative process
**Stages:**

- Introduced
- Referred to Committee
- Committee Action
- Passed One Chamber
- Passed Both Chambers
- Signed into Law

**Method:** Regex pattern matching on action text to classify stage
**Insight:** Shows conversion rates at each stage (typically <5% become law)

#### 3. Cosponsor Distribution

**Type:** Histogram
**Purpose:** Distribution of cosponsor counts
**Method:** Group bills by cosponsor count, plot frequency
**Insight:** Most bills have few cosponsors; high-cosponsor bills are outliers

#### 4. Sponsor Ideology Distribution (by Party)

**Type:** Box plot or violin plot
**Purpose:** Compare ideological distribution of bill sponsors by party
**Method:** Plot DW-NOMINATE dim1 scores grouped by party
**Insight:** Shows ideological polarization; Democrats typically negative, Republicans positive

#### 5. Bills Over Time

**Type:** Time series line chart
**Purpose:** Track legislative activity over time
**Method:** Count bills by introduced_date, resample by month
**Insight:** Shows seasonal patterns (active periods early in congressional session)

#### 6. Top Active Committees

**Type:** Bar chart
**Purpose:** Identify committees handling most bills
**Method:** Count bills per committee from `bill_actions` table
**Insight:** Shows which committees are legislative bottlenecks

### Advanced Analytics

#### 7. Logistic Regression - Predicting Bill Advancement

**Purpose:** Identify factors predicting whether a bill will advance beyond introduction

**Features:**

- Cosponsor count (log-transformed)
- Bipartisan support (Gini coefficient)
- Sponsor ideology (DW-NOMINATE dim1)
- Committee count
- Policy area (one-hot encoded)

**Target Variable:** Binary - Did bill pass at least one chamber?

**Method:**

1. Load bills from database
2. Engineer features (calculate bipartisan score, extract stage)
3. Split train/test (80/20)
4. Train logistic regression with sklearn
5. Evaluate: accuracy, precision, recall, F1 score, ROC-AUC
6. Feature importance (coefficient magnitudes)

**Output:**

- Model performance metrics
- Feature importance chart
- Interpretation of which factors matter most

**Typical Findings:**

- Bipartisan support is strongest predictor
- Cosponsor count correlates with advancement
- Ideology extremity negatively correlated

#### 8. K-Means Clustering

**Purpose:** Discover natural groupings of bills based on characteristics

**Features:**

- Bill momentum score
- Cosponsor count (normalized)
- Bipartisan support score
- Days since introduction
- Committee count

**Method:**

1. Calculate features for all bills
2. Standardize features (mean=0, std=1)
3. Apply K-means with k=4 clusters
4. Assign cluster labels to bills
5. Visualize in 2D using PCA or t-SNE

**Output:**

- Cluster assignments
- Cluster centroids
- 2D scatter plot with color-coded clusters
- Cluster summaries (mean values per feature)

**Typical Clusters:**

- High-momentum bipartisan bills
- Partisan low-momentum bills
- Recently introduced bills
- Committee-stage bills

#### 9. Industry Risk Heatmap

**Purpose:** Visualize which GICS sectors face most legislative risk

**Method:**

1. Query all bills with GICS sector classifications
2. Calculate average momentum per sector
3. Count bills per sector
4. Create heatmap: sectors × metrics (avg momentum, bill count, high-risk bills)

**Output:**

- Heatmap with Plotly
- Color intensity represents risk level
- Annotations show exact values

**Insight:** Identifies which industries face most regulatory pressure

#### 10. Correlation Analysis

**Purpose:** Understand relationships between bill characteristics

**Variables:**

- Momentum score
- Cosponsor count
- Bipartisan support
- Committee count
- Sponsor ideology
- Days since introduction
- Stage score

**Method:**

1. Calculate correlation matrix (Pearson)
2. Create heatmap with Plotly
3. Identify strong correlations (|r| > 0.5)

**Output:**

- Correlation heatmap
- List of strong correlations
- Interpretation guide

**Typical Findings:**

- Stage score strongly correlated with momentum (by design)
- Bipartisan support correlated with advancement
- Cosponsor count and stage score positively correlated
- Recent activity and high stage score correlated

---

## Part 7: Streamlit App

### Interactive Web Application

**Purpose:** Provide user-friendly interface for portfolio risk checking

**Technology Stack:**

- Streamlit for web framework
- Plotly for interactive charts
- SQLite for data backend

### Application Structure

#### Page Configuration

```python
st.set_page_config(
    page_title="LegisRisk",
    page_icon="📊",
    layout="wide"
)
```

#### Header Section

- Title: "LegisRisk - Congressional Bill Risk Analyzer"
- Description of tool purpose
- Instructions for use

#### Sidebar

**User Inputs:**

1. **Portfolio Input**
   - Text area for comma-separated tickers
   - Example: "AAPL, JPM, LLY, XOM"
   - Validation and parsing

2. **Risk Threshold Filter**
   - Slider: 0-100
   - Show only tickers above threshold
   - Default: 0 (show all)

3. **Sector Filter** (optional)
   - Multi-select dropdown
   - Filter results by GICS sector
   - Default: All sectors

4. **Sort Order**
   - Radio buttons: Risk Score (High to Low) or Alphabetical
   - Default: Risk descending

#### Main Panel: Portfolio Risk Dashboard

**Section 1: Overview Cards**

- Total tickers analyzed
- Average portfolio risk
- Highest risk ticker
- Total bills identified

**Section 2: Risk Summary Table**
Sortable table with columns:

- Ticker
- Company Name
- Sector
- Risk Score (with color coding)
- Risk Label
- Bill Count
- Top Bill Title

**Section 3: Detailed Ticker Analysis**
For each ticker (expandable):

- Company info card
- Risk gauge chart (Plotly indicator)
- Top 5 bills table with:
  - Bill ID (linked to Congress.gov)
  - Title
  - Momentum score
  - Stage
  - Cosponsors
  - Latest action date
  - Policy area
- Risk factors breakdown (what contributes to score)

**Section 4: Visualizations**

- Portfolio risk distribution (bar chart)
- Sector exposure (pie chart)
- Bill momentum histogram
- Timeline of bill activity

### Deployment

```bash
streamlit run app.py
```

**Note:** The Streamlit code is included in the notebook for reference but must be run separately (not executable in Jupyter environment).

---

## Key Methodologies

### 1. Data Integration Strategy

- **Polars** for fast dataframe operations (faster than pandas)
- Careful handling of nested JSON from API responses
- Progressive joins with unique suffixes to track data provenance
- Parquet format for efficient storage and fast I/O

### 2. Legislative Stage Detection

- Regex pattern matching on action text
- Prioritization of stages (higher stage overwrites lower)
- Covers full legislative lifecycle from introduction to law

### 3. Bipartisan Support Calculation

- Gini coefficient on party distribution
- Accounts for independent/third-party sponsors
- Formula: `1 - sum(p_i^2)` where p_i is proportion of party i

### 4. Recency Scoring

- Exponential decay function
- 180-day half-life balances recent vs. historical activity
- Prevents old bills from dominating scores

### 5. Industry Classification

- Multi-tier approach balances accuracy and coverage
- Confidence scores allow for uncertainty quantification
- LLM fallback for edge cases (optional)

### 6. Risk Aggregation

- Weighted average of bill momentum scores
- Prevents single high-momentum bill from dominating
- Accounts for both quantity and quality of bills

---

## Data Flow Summary

```
1. API Collection
   ↓
2. Parquet Files (intermediate storage)
   ↓
3. Data Integration (Polars joins)
   ↓
4. SQLite Database (normalized)
   ↓
5. Industry Classification (GICS sectors)
   ↓
6. Ticker Mapping (yfinance)
   ↓
7. Risk Scoring (momentum + aggregation)
   ↓
8. Analytics & Visualization
   ↓
9. Streamlit App (user interface)
```

---

## Key Findings & Insights

Based on the analytical approach:

1. **Legislative Success is Rare**
   - Stage funnel shows <5% of bills become law
   - Most bills die in committee

2. **Bipartisanship Matters**
   - Logistic regression shows bipartisan support is strongest predictor
   - Bills with diverse cosponsors advance further

3. **Industry Concentration**
   - Health Care and Financials typically face most bills
   - Technology sector seeing increased activity (AI regulation)

4. **Ideological Polarization**
   - DW-NOMINATE scores show widening party gap
   - Extreme ideology negatively correlates with bill advancement

5. **Temporal Patterns**
   - Activity spikes early in congressional session
   - Election years see reduced legislative output

---

## Technical Highlights

### Performance Optimizations

- ThreadPoolExecutor for parallel API calls
- Polars for fast dataframe operations (10-100x faster than pandas)
- SQLite with indexes for fast queries
- yfinance caching to minimize API calls

### Error Handling

- Try/except blocks for all API calls
- Graceful degradation when data unavailable
- Validation of user inputs in Streamlit app

### Code Quality

- Modular design (each part can run independently)
- Clear function documentation
- Type hints (where applicable)
- Separation of concerns (data/logic/presentation)

---

## Limitations & Future Work

### Current Limitations

1. **API Rate Limiting**: Congress.gov API is slow (2+ hours for full data)
2. **Dataset Size**: Demo uses only 1000 bills (current Congress has ~15,000)
3. **LLM Classification**: Disabled by default due to API costs
4. **Real-time Updates**: Database requires manual refresh
5. **Historical Analysis**: Limited to 119th Congress (could expand to 111-119)

### Potential Enhancements

1. **Automated Data Pipeline**: Scheduled API calls + database updates
2. **Machine Learning Improvements**:
   - Train custom bill advancement predictor
   - Use NLP embeddings for bill similarity
   - Predict bill text sentiment (pro-industry vs. restrictive)
3. **Enhanced Risk Scoring**:
   - Incorporate bill text sentiment
   - Weight by committee power/influence
   - Account for sponsor seniority
4. **Portfolio Features**:
   - Import portfolio from CSV/Excel
   - Integration with brokerage APIs
   - Historical risk tracking
   - Alert system for new high-risk bills
5. **Additional Data Sources**:
   - Lobbying data (OpenSecrets)
   - Campaign finance (FEC)
   - Committee hearing transcripts
   - Media mentions/sentiment
6. **UI Enhancements**:
   - Mobile-responsive design
   - Export reports (PDF/Excel)
   - Saved portfolios
   - User accounts

---

## Dependencies & Requirements

### Python Packages

- `polars` - Fast dataframe library
- `requests` - HTTP client for API calls
- `yfinance` - Stock data from Yahoo Finance
- `streamlit` - Web app framework
- `plotly` - Interactive visualizations
- `scikit-learn` - Machine learning (regression, clustering)
- `numpy` - Numerical operations
- `sqlite3` - Database (built-in)

### External APIs

- Congress.gov API (requires API key)
- Yahoo Finance (via yfinance, no key required)
- Claude API (optional, for LLM classification)

### Data Files

- `bills_111_119.json` - Initial bill list
- `final_df_conggov.parquet` - Integrated data
- `legisrisk.db` - SQLite database
- Individual endpoint parquet files (main_point, actions_point, etc.)

### Environment

- Python 3.13.5
- Jupyter Notebook or Google Colab
- SQLite 3.x
- Modern web browser (for Streamlit)

---

## Conclusion

LegisRisk demonstrates a complete end-to-end data science workflow:

1. **Data Collection** - API integration with rate limiting
2. **Data Engineering** - Complex joins, normalization, database design
3. **Feature Engineering** - Multi-component scoring system
4. **Machine Learning** - Classification, clustering, regression
5. **Visualization** - Descriptive and interactive charts
6. **Product** - User-facing web application

The project successfully answers the core question: "What legislative risk does my portfolio face?" by combining legislative data, industry classification, and financial market data into actionable risk scores.

The modular design allows each component to be run independently, making it easy to update data, refine scoring algorithms, or extend functionality. The multi-tier industry classification approach balances accuracy (deterministic mappings) with coverage (keyword fallbacks and optional LLM), while the composite momentum scoring captures multiple dimensions of legislative risk.

This system could be deployed as a commercial product for investors, corporate government affairs teams, or policy researchers seeking to understand the intersection of legislation and markets.
