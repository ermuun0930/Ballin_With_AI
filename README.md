# Ballin_With_AI

# LegisRisk

Congressional Bill Regulatory Risk Scoring for Stock Portfolios
Milestone Project Description
Spring 2026

# Project Overview

LegisRisk is a data product that lets users input stock tickers from their portfolio and instantly see which pending congressional bills pose regulatory risk to their holdings. The core question we are answering is: given someone's stock portfolio, how much legislative risk is each holding exposed to right now? To answer this, we collect 1,000 pending bills from the 119th Congress, classify each bill's industry impact into GICS sectors using an LLM, map those sectors to public companies, and compute a composite risk score per ticker. The end result is a portfolio risk analyzer where a user can input tickers like AAPL, LLY, and JPM and get back a ranked breakdown of which stocks face the most regulatory headwind from bills currently moving through Congress.

# Data Collection and Backend

We pull from three data sources, all free or near-free, and store everything in consolidated Parquet files for efficient columnar processing. The pipeline currently processes 1,000 bills with 82 columns of enriched data across three output files: final_df_conggov.parquet (74 columns), bills_classified.parquet (76 columns), and bills_with_risk.parquet (82 columns).

~ Congress.gov API. We fetch 1,000 bills from the 119th Congress using six distinct API endpoints: main bill metadata, actions (legislative history), cosponsors (support network), committees (assignments), subjects (policy tags), and related bills (companion legislation). Each endpoint is fetched concurrently using ThreadPoolExecutor with 5 workers, reducing total fetch time from roughly 30 minutes to about 6 minutes. From the cosponsor data we compute a support score using logarithmic scaling, and from the action history we extract the legislative stage via regex pattern matching. All raw responses are cached as individual Parquet files (main_point.parquet, actions_point.parquet, etc.) and the merged result lands in final_df_conggov.parquet (1,000 bills, 74 columns).

~ OpenAI GPT-4o-mini (Industry Classification). For each bill, we send the title, policy area, and legislative subjects to OpenAI's GPT-4o-mini model with a structured few-shot prompt asking it to classify the bill into GICS (Global Industry Classification Standard) sectors and assign a confidence score (0 to 1). The model uses JSON mode (response_format: json_object) with temperature 0.0 for deterministic output. Bills are processed concurrently (10 workers, 50 bills per chunk) and the results are written to bills_classified.parquet with 87.3% successful classification across 11 GICS sectors. We chose an LLM over manual keyword mapping because the CRS policy area tags are too coarse—for example, “Health” lumps drug pricing, hospital regulation, and insurance reform together even though they hit completely different industry sectors.

~ United States Project (Legislator Metadata). We fetch the current legislator dataset from the United States Project GitHub repository (legislators-current.json), which provides biographical data, term history, party affiliation, and district information for every sitting member of Congress. We join this to bill data on bioguideId (extracted from each bill's primary sponsor), giving us legislator-level context for roughly 98% of bills.

~ Voteview (Ideology Scores). We pull DW-NOMINATE ideology scores from Voteview's 119th Congress member file (HS119_members.json). These scores place each legislator on a −1 to +1 economic left–right axis (nominate_dim1) and a social/regional axis (nominate_dim2). Merging on bioguideId adds ideology context for about 60% of bills (Senate bills lack House member scores by design).

The merge logic uses Polars left joins on the composite key (congress, type, number) to combine all six API endpoints into a single wide table, then enriches it with legislator metadata and ideology scores. The full pipeline flows from raw API responses to final_df_conggov.parquet (backend), to bills_classified.parquet (classification), to bills_with_risk.parquet (risk scoring), producing a complete path from legislative text to per-stock risk exposure.

# Analytical Approach

~ Descriptive Analytics. We produce a nine-panel visualization dashboard. Panel 1 shows the risk score distribution (histogram with mean line), confirming most bills cluster at low risk. Panel 2 breaks down bills by risk level (Very Low through Very High) with color-coded bars. Panel 3 charts average risk component contributions, showing legislative stage contributes the most. Panel 4 ranks the top 10 sectors by average risk, with Health Care, Financials, and Industrials leading. Panel 5 ranks sectors by bill count (legislative activity). Panel 6 is a correlation heatmap of all risk features. Panels 7–9 are scatter plots—stage vs. risk, cosponsors vs. risk, and a cluster visualization colored by K-Means cluster ID—which confirm the strong positive relationship between legislative progress and overall risk.

~ The core analytical contribution is a weighted risk formula. For each ticker, we sum across all affecting bills the product of passage likelihood, LLM relevance score, regulatory direction (−1 for restrictive, +1 for supportive), and a volatility amplifier normalized to [0.5, 1.5]. The raw scores are then min-max scaled to 0 through 100 and bucketed into HIGH/MEDIUM/LOW categories. This goes beyond simple description; it is a composite index that weights multiple heterogeneous signals into a single actionable number per stock. Composite Risk Score. The core analytical contribution is a transparent weighted formula. For each bill we compute four component scores: (1) Legislative Stage (40% weight), scored 0–100 by regex-matching the latest action text against 12 progression stages from “introduced” (10) through “became law” (100); (2) Cosponsor Support (25% weight), using logarithmic scaling where 50 cosponsors maps to a score of 100 to handle diminishing marginal support; (3) Recency (20% weight), with exponential decay on a 180-day half-life so that recently active bills score higher; and (4) Bipartisan Support (15% weight), a threshold estimate where 20+ cosponsors yields 100, 10+ yields 70, 5+ yields 40, and fewer yields 20. The composite formula is Risk = 0.40 × Stage + 0.25 × Cosponsors + 0.20 × Recency + 0.15 × Bipartisan, producing a 0–100 score bucketed into Very Low / Low / Moderate / High / Very High. We also run a Linear Regression on the four components (R² = 0.997, confirming formula consistency) and K-Means Clustering (k = 4, silhouette = 0.67) that segments bills into “High Momentum,” “Stalled,” “Newly Introduced,” and “Bipartisan Focus” profiles.

~ Portfolio Analysis. The portfolio risk module takes any list of tickers, maps each to its GICS sector, filters bills affecting that sector, computes a confidence-weighted average risk score, and returns the top five riskiest bills per holding. For a sample portfolio of eight tickers (AAPL, MSFT, JPM, BAC, LLY, JNJ, XOM, CVX), Health Care holdings (LLY, JNJ) face the highest exposure with an average risk of 36.5 across 163 affecting bills, followed by Financials (JPM, BAC) at 35.4 with 137 bills and Energy (XOM, CVX) at 33.2 with 55 bills.

# Planned Extensions

Based on professor feedback and our own roadmap, we plan to pursue several extensions for the final submission. Bill coverage has already been expanded from 200 to 1,000 bills. Additional planned work includes:
~ Realized vs. implied volatility plot. Pull options chain data via yfinance to compare implied vol against the realized vol we already compute, giving a richer picture of how the market is pricing legislative risk.
~ Keyword verification of LLM classifications. For each industry the LLM tags, generate keywords and run a keyword search against the bill text to cross-check accuracy and reduce hallucination risk.
~ Diversification recommendation engine. Flag when a user’s portfolio is overconcentrated in high-risk sectors and suggest sector-level rebalancing.
~ Lobbyist disclosure integration. Incorporate lobbying data to see which companies are actively fighting or supporting specific bills, adding another signal to the risk model.
~ Expand GICS sector coverage by fine-tuning the classification prompt and adding more few-shot examples for underrepresented sectors like Materials and Communication Services.
~ Build a Flask or Streamlit web interface so the portfolio checker works as a standalone web app rather than a notebook function.
~ We plan to add historical risk tracking to monitor how bill risk scores evolve over time as legislation advances through Congress.

# Group Member Contributions

# Kevin Singh [ps5486]

Current: Lead developer on the backend codebase. Built the SQLite database schema, the Congress.gov API ingestion pipeline, the yfinance ticker-to-sector mapping, and the data merge logic. Handled the initial milestone submission and resubmission. Primary owner of the Jupyter notebook.
Future: Maintain and further expand beyond current 1,000-bill coverage, implement keyword verification of LLM output, build the Flask/Streamlit deployment, and integrate lobbyist disclosure data.

# Strang Zeng (qz2874)

Current: Developed the OpenAI LLM classification prompt and pipeline, including structured JSON output parsing and the manual fallback subject-to-GICS mapping. Translated professor feedback into actionable items and researched extension feasibility. Managed deadline tracking and milestone coordination.
Future: Refine LLM classification accuracy, implement the realized vs. implied volatility analysis, and handle data validation and quality assurance for expanded bill coverage.

# Hendrix [hff7235]

Current: Authored the 1-2 page project description document. Attended class sessions to collect professor feedback and relayed extension suggestions (volatility plot, keyword verification, diversification recommendations, lobbyist data) to the team. Contributed to quiz coordination and project framing.
Future: Design and build the diversification recommendation engine, create the web UI for the Streamlit/Flask app, and write the final project report.

# Ermuun [eb4500]

Current: Leading the front-end side of the project. Set up the Google Doc structure and outline for the project description. Helped coordinate workload division and milestone requirements across the team.
Future: Create visualizations for the extended analytics (implied volatility chart, diversification dashboard), assist with data collection for lobbyist disclosure integration, and contribute to the final presentation. Make the web-app more user-friendly and with more features.

# Jinwook Lee [jl18299]

Current: Worked on incorporating professor feedback into the extensions plan and assisted with notebook documentation. Supported milestone coordination and team communication.
Future: Implement the regression analysis testing risk score vs. realized stock returns, assist with expanded bill ingestion, and contribute to the final written report and documentation.
