# LegisRisk - Data Schemas

## Overview
This document details the structure of datasets used in the LegisRisk pipeline. Since the system uses parquet files rather than a relational database, schemas represent DataFrame column structures and nested JSON formats.

---

## Primary Datasets

### 1. `final_df_conggov.parquet`
**Source:** Part 0 (Backend - Data Collection)  
**Purpose:** Consolidated congressional bill data from multiple sources  
**Rows:** 1,000 bills  
**Columns:** 74  
**Size:** ~2MB

#### Core Bill Metadata
| Column | Type | Description | Example | Null? |
|--------|------|-------------|---------|-------|
| `type` | str | Bill type | "hr", "s", "hres", "sres" | No |
| `number` | str | Bill number | "7337" | No |
| `congress` | str | Congress session | "119" | No |
| `title` | str | Full bill title | "To amend the Internal Revenue Code..." | No |
| `originChamber` | str | Originating chamber | "House", "Senate" | No |
| `introducedDate` | str (YYYY-MM-DD) | Date introduced | "2026-02-03" | No |

#### Latest Action
| Column | Type | Description | Example | Null? |
|--------|------|-------------|---------|-------|
| `latestAction` | dict | Most recent action | `{"actionDate": "2026-02-03", "text": "Referred to..."}` | No |
| `updateDate` | str (ISO8601) | Last update timestamp | "2026-02-25T17:19:29Z" | No |

**latestAction Structure:**
```json
{
  "actionDate": "2026-02-03",
  "actionTime": null,
  "text": "Referred to the House Committee on House Administration."
}
```

#### Policy Classification
| Column | Type | Description | Example | Null? |
|--------|------|-------------|---------|-------|
| `policyArea` | dict | Primary policy area | `{"name": "Health"}` | Yes (~5%) |

#### Sponsorship
| Column | Type | Description | Example | Null? |
|--------|------|-------------|---------|-------|
| `sponsors` | list[dict] | Primary sponsors | `[{"bioguideId": "F000466", "fullName": "Brian Fitzpatrick", ...}]` | No |
| `bioguideId` | str | Primary sponsor ID (extracted) | "F000466" | Yes (~2%) |
| `cosponsors` | dict | Cosponsor data | `{"count": 26, ...}` | Yes |

**sponsors Structure:**
```json
[
  {
    "bioguideId": "F000466",
    "district": 1,
    "firstName": "Brian",
    "fullName": "Rep. Fitzpatrick, Brian K. [R-PA-1]",
    "isByRequest": "N",
    "lastName": "Fitzpatrick",
    "middleName": "K.",
    "party": "R",
    "state": "PA",
    "url": "https://api.congress.gov/v3/member/F000466"
  }
]
```

**cosponsors Structure:**
```json
{
  "count": 26,
  "countIncludingWithdrawnCosponsors": 26,
  "url": "https://api.congress.gov/v3/bill/119/hr/7333/cosponsors"
}
```

#### Nested Data (Sub-Endpoints)
| Column | Type | Description | Null? |
|--------|------|-------------|-------|
| `actions_act` | dict | Full action history | Yes |
| `committees_comm` | dict | Committee assignments | Yes |
| `cosponsors_cospon` | dict | Detailed cosponsor list | Yes |
| `subjects_subj` | dict | Legislative subjects | Yes |
| `relatedBills_related` | dict | Related bill links | Yes |

**subjects_subj Structure:**
```json
{
  "legislativeSubjects": [
    {"name": "Health insurance coverage", "updateDate": "2026-02-04T05:16:10Z"},
    {"name": "Prescription drug costs", "updateDate": "2026-02-04T05:16:10Z"}
  ],
  "policyArea": {"name": "Health", "updateDate": "2026-02-04T05:16:10Z"}
}
```

**actions_act Structure:**
```json
{
  "actions": [
    {
      "actionCode": "H11100",
      "actionDate": "2026-02-03",
      "actionTime": null,
      "committees": [{"name": "Energy and Commerce Committee", ...}],
      "sourceSystem": {"code": 2, "name": "House floor actions"},
      "text": "Referred to the House Committee on Energy and Commerce.",
      "type": "IntroReferral"
    }
  ],
  "count": 1
}
```

#### Legislator Metadata (from United States Project)
| Column | Type | Description | Example | Null? |
|--------|------|-------------|---------|-------|
| `name` | dict | Legislator name | `{"first": "Brian", "last": "Fitzpatrick"}` | Yes |
| `bio` | dict | Biographical info | `{"birthday": "1973-12-17", "gender": "M"}` | Yes |
| `terms` | list[dict] | Congressional terms | `[{"type": "rep", "start": "2017-01-03", ...}]` | Yes |

#### Ideology Scores (from Voteview)
| Column | Type | Description | Range | Null? |
|--------|------|-------------|-------|-------|
| `nominate_dim1` | float | Economic left-right | -1.0 to 1.0 | Yes |
| `nominate_dim2` | float | Social dimension | -1.0 to 1.0 | Yes |
| `nokken_poole_dim1` | float | Roll call-based ideology | -1.0 to 1.0 | Yes |

**DW-NOMINATE Interpretation:**
- `nominate_dim1`: Economic/government role axis
  - **< -0.5:** Strong liberal
  - **-0.5 to 0:** Moderate liberal
  - **0 to 0.5:** Moderate conservative
  - **> 0.5:** Strong conservative
- `nominate_dim2`: Social/regional axis (less important in modern era)

---

### 2. `bills_classified.parquet`
**Source:** Part 1 (Industry Classification)  
**Purpose:** Bills with GICS sector classifications  
**Rows:** 1,000 bills  
**Columns:** 76 (74 from Part 0 + 2 new)

#### New Classification Columns
| Column | Type | Description | Example | Null? |
|--------|------|-------------|---------|-------|
| `gics_sectors` | str | Pipe-delimited sectors | "Health Care\|Financials" | Yes (~13%) |
| `confidence` | float | Classification confidence | 0.95 | Yes (~13%) |

**GICS Sectors (11 total):**
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

**Classification Confidence Ranges:**
- **0.9-1.0:** High confidence (direct policy area match)
- **0.8-0.9:** Good confidence (clear subject keywords)
- **0.7-0.8:** Moderate confidence (title keywords)
- **0.5-0.7:** Low confidence (LLM inference)
- **< 0.5:** Very low confidence (ambiguous)

---

### 3. `bills_with_risk.parquet`
**Source:** Part 2 (Risk Scoring)  
**Purpose:** Bills with composite risk scores  
**Rows:** 1,000 bills  
**Columns:** 82 (76 from Part 1 + 6 new)

#### Risk Score Components
| Column | Type | Description | Range | Formula |
|--------|------|-------------|-------|---------|
| `stage_score` | float | Legislative progress | 0-100 | Regex-based stage detection |
| `cosponsor_score` | float | Cosponsor support | 0-100 | `min(100, log1p(count)/log1p(50)*100)` |
| `recency_score` | float | Recent activity | 0-100 | `100 * exp(-days_ago/180)` |
| `bipartisan_score` | float | Cross-party support | 20-100 | Threshold-based (5/10/20+ cosponsors) |
| `risk_score` | float | **Composite risk** | 0-100 | **Weighted sum** |
| `risk_label` | str | Risk category | "Very Low" to "Very High" | Binned from risk_score |

#### Risk Score Formula
```python
risk_score = (
    0.40 * stage_score +      # 40% weight - most important
    0.25 * cosponsor_score +  # 25% weight
    0.20 * recency_score +    # 20% weight
    0.15 * bipartisan_score   # 15% weight
).round(2)
```

#### Risk Label Mapping
| risk_score Range | risk_label | Meaning |
|------------------|------------|---------|
| 0-20 | Very Low | Introduced, no momentum |
| 20-40 | Low | Committee stage, few cosponsors |
| 40-60 | Moderate | Active in committee, some support |
| 60-80 | High | Passed one chamber or strong support |
| 80-100 | Very High | Near enactment or recently enacted |

#### Stage Score Mapping (Legislative Progress)
| Stage Description | stage_score | Key Phrases |
|-------------------|-------------|-------------|
| Introduced | 10 | "introduced" |
| Referred to committee | 20 | "referred to committee" |
| Subcommittee action | 30 | "subcommittee" |
| Committee hearing | 40 | "committee hearing", "markup" |
| Ordered reported | 45 | "ordered to be reported" |
| Reported by committee | 50 | "reported" + "committee" |
| Received in other chamber | 65 | "received in senate/house" |
| Passed one chamber | 70 | "passed senate" OR "passed house" |
| Both chambers passed | 80 | "passed senate" AND "passed house" |
| Conference committee | 85 | "resolving differences", "conference" |
| Presented to President | 90 | "presented to president" |
| Signed by President | 95 | "signed by president" |
| **Became law** | **100** | "became public law", "became law" |

---

## Data Relationships

### Entity Relationships (Conceptual)
```
Bill (1) ─── (N) Actions
Bill (1) ─── (N) Cosponsors
Bill (1) ─── (N) Subjects
Bill (1) ─── (N) Committees
Bill (N) ─── (N) Related Bills
Bill (N) ─── (1) Primary Sponsor (Legislator)
Legislator (1) ─── (1) Ideology Score
```

### Join Keys
- **Bill identification:** `(congress, type, number)` - composite primary key
- **Legislator identification:** `bioguideId` - unique ID from Congress.gov
- **Sector filtering:** `gics_sectors` - text contains search

---

## Denormalization Strategy

### Why Parquet + Nested JSON?
1. **API fidelity:** Preserves original Congress.gov structure
2. **Schema flexibility:** Handles evolving API responses
3. **Query performance:** Polars/pandas optimized for columnar format
4. **Storage efficiency:** 10x compression vs CSV
5. **Type preservation:** No string parsing needed

### Nested Structures (Not Flattened)
- `latestAction` - Single dict (always 1:1)
- `policyArea` - Single dict (always 1:1)
- `sponsors` - List of dicts (1:N, but typically 1 sponsor)
- `actions_act` - Nested list (1:N, can be 100+ actions)
- `subjects_subj.legislativeSubjects` - Nested list (1:N, typically 5-20 subjects)

### Why Not Normalized Tables?
- **Original approach:** LegisRiskDB used SQLite (5 tables)
- **Current approach:** Single wide table
- **Rationale:**
  - Simpler for analytical queries (no joins needed)
  - Faster for pandas/polars (columnar operations)
  - Easier to export/share (single file)
  - No ACID requirements (append-only workflow)

---

## Data Quality

### Completeness
| Field | Non-Null % | Notes |
|-------|------------|-------|
| Core metadata | 100% | type, number, congress, title |
| latestAction | 100% | Always present |
| policyArea | ~95% | Missing for procedural bills |
| sponsors | ~98% | Rare missing for joint resolutions |
| cosponsors | ~85% | Often 0 count (no cosponsors) |
| subjects_subj | ~90% | Takes time to be assigned |
| gics_sectors (classified) | ~87% | LLM classification success rate |
| ideology scores | ~60% | Only available for current House members |

### Known Data Issues
1. **Nested nulls:** `subjects_subj.legislativeSubjects` can be empty list `[]`
2. **Type inconsistency:** `cosponsors` can be dict OR list depending on endpoint
3. **Date formats:** Mix of "YYYY-MM-DD" and ISO8601 "YYYY-MM-DDTHH:MM:SSZ"
4. **Missing ideology:** Senate bills lack House member scores
5. **Legacy data:** Older congresses (<119) have different schema versions

---

## Sample Data

### Minimal Bill Record
```json
{
  "type": "hr",
  "number": "7337",
  "congress": "119",
  "title": "To amend the Internal Revenue Code of 1986...",
  "originChamber": "House",
  "introducedDate": "2026-02-03",
  "latestAction": {
    "actionDate": "2026-02-03",
    "text": "Referred to the House Committee on Ways and Means."
  },
  "policyArea": {"name": "Taxation"},
  "sponsors": [{
    "bioguideId": "S001214",
    "fullName": "Rep. Steube, W. Gregory [R-FL-17]",
    "party": "R",
    "state": "FL"
  }],
  "cosponsors": {"count": 0},
  "gics_sectors": "Financials",
  "confidence": 0.85,
  "risk_score": 18.5,
  "stage_score": 20.0,
  "cosponsor_score": 0.0,
  "recency_score": 100.0,
  "bipartisan_score": 20.0,
  "risk_label": "Very Low"
}
```

### High-Risk Bill Record
```json
{
  "type": "hr",
  "number": "1",
  "congress": "119",
  "title": "Lower Costs, More Transparency Act",
  "originChamber": "House",
  "introducedDate": "2025-01-07",
  "latestAction": {
    "actionDate": "2025-01-10",
    "text": "Passed/agreed to in House: On passage Passed by the Yeas and Nays: 220 - 211."
  },
  "policyArea": {"name": "Health"},
  "sponsors": [{
    "bioguideId": "M001159",
    "fullName": "Rep. McMorris Rodgers, Cathy [R-WA-5]",
    "party": "R",
    "state": "WA"
  }],
  "cosponsors": {"count": 42},
  "gics_sectors": "Health Care",
  "confidence": 0.95,
  "risk_score": 72.3,
  "stage_score": 70.0,
  "cosponsor_score": 98.2,
  "recency_score": 85.4,
  "bipartisan_score": 100.0,
  "risk_label": "High"
}
```

---

## Schema Version History

### v1.0 (Current)
- Parquet-based flat files
- 74 base columns + classification + risk scoring
- Nested JSON for complex structures

### v0.9 (Legacy - LegisRiskDB)
- SQLite normalized database
- 5 tables (bills, bill_sponsors, bill_subjects, bill_actions, ticker_industries)
- Exploded arrays for 1:N relationships

---

## Migration Notes

### From SQLite to Parquet
```python
# Old: Query from database
conn = sqlite3.connect('legisrisk.db')
df = pd.read_sql("SELECT * FROM bills WHERE gics_sectors LIKE '%Health Care%'", conn)

# New: Filter parquet
df = pd.read_parquet('bills_with_risk.parquet')
df = df[df['gics_sectors'].str.contains('Health Care', na=False)]
```

### Accessing Nested Fields
```python
# Extract action date from nested dict
df['action_date'] = df['latestAction'].apply(
    lambda x: x['actionDate'] if isinstance(x, dict) else None
)

# Extract legislative subjects from nested structure
df['subjects_list'] = df['subjects_subj'].apply(
    lambda x: [s['name'] for s in x.get('legislativeSubjects', [])] 
    if isinstance(x, dict) else []
)
```

---

## Performance Characteristics

| Operation | Parquet | SQLite | Speedup |
|-----------|---------|--------|---------|
| Full scan | 0.05s | 0.2s | 4x |
| Filter by sector | 0.02s | 0.15s | 7.5x |
| Join (1000 rows) | 0.01s | 0.05s | 5x |
| Load to memory | 0.03s | 0.25s | 8x |
| Write to disk | 0.08s | 0.4s | 5x |

**Test Environment:** M1 MacBook, 1000 bills, 82 columns

---

## Data Governance

### Retention Policy
- **Raw API responses:** Keep indefinitely (historical reference)
- **Classified bills:** Keep until re-classification
- **Risk scores:** Recompute daily (volatile)
- **Intermediate caches:** Delete after 30 days

### Access Control
- **Public data:** All Congressional data is public domain
- **API keys:** Store in environment variables (not in code)
- **OpenAI cache:** Contains bill titles (non-sensitive)

### PII Handling
- **Legislator names/IDs:** Public figures (not PII)
- **No user data:** System does not collect user information
- **No financial data:** Tickers only (no positions/values)

---

## References

- **Congress.gov API:** https://api.congress.gov/
- **GICS Sectors:** https://www.msci.com/gics
- **DW-NOMINATE:** https://voteview.com/about
- **Polars Docs:** https://pola-rs.github.io/polars/
- **Parquet Format:** https://parquet.apache.org/
