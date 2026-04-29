# Bill Classification Debug Findings

## Issue Summary
**All 1000 bills have NULL GICS codes (100% failure rate)**

## Investigation Steps Completed

### 1. Data Source Analysis

**File:** `/Users/kevinsingh/Downloads/Stats Project/LegisRisk/final_df_conggov.parquet`
- Total bills: 1,000
- Columns: 32

**Critical Finding: Missing Subject Data**
- Only **34 bills (3.4%)** have legislative subjects embedded in the data
- The remaining 96.6% of bills have subjects as API references only
- The `subjects` column contains: `{'count': 1, 'url': 'https://api.congress.gov/...'}`
- The actual subject data needs to be extracted from `subjects_subj.legislativeSubjects`

### 2. Data Structure Issues

**Policy Area Column (`policyArea`)**
- Format: `{'name': 'Congress'}` (nested dict)
- **Status:** ✓ Successfully extracting the 'name' field

**Subjects Column (`subjects`)**
- Format: `{'count': 1, 'url': '...'}`  (API reference, not actual data)
- **Status:** ✗ Not usable for classification

**Subjects_subj Column (`subjects_subj`)**
- Format: `{'legislativeSubjects': [...], 'policyArea': {...}}`
- Contains actual legislative subjects when available
- **Status:** ✓ Now successfully extracting when data exists
- **Problem:** Only 3.4% of bills have non-empty legislativeSubjects

### 3. Classification Results Analysis

**File:** `/Users/kevinsingh/Downloads/Stats Project/LegisRisk/bills_classified.parquet`
- Total bills: 1,000
- Null GICS sectors: **1,000 (100%)**
- Non-null GICS sectors: **0 (0%)**
- Confidence scores: All 0.0

**This indicates:**
1. The classification function ran (columns exist)
2. Every single classification attempt failed
3. The failure is systematic, not random

### 4. Potential Root Causes

**Hypothesis 1: Insufficient Input Data (Most Likely)**
- 96.6% of bills lack legislative subjects
- LLM receives only title + policy area
- May not have enough context to classify confidently
- But this shouldn't cause NULL values - it should return low-confidence guesses

**Hypothesis 2: API/Parsing Error (Needs Testing)**
- Portkey API might be returning errors
- JSON parsing might be failing
- Response format might not match expectations
- **This is the most likely cause of NULL values**

**Hypothesis 3: Validation Logic Too Strict**
- Sectors validation might be rejecting valid responses
- LLM might be returning sectors in different format
- Empty sectors array triggers None return

### 5. Test Script Created

**File:** `/Users/kevinsingh/Downloads/Stats Project/LegisRisk/test_classification.py`

**Features:**
- Extensive debug logging at every step
- Tests data extraction (policy area, subjects)
- Tests API calls with full request/response logging
- Tests JSON parsing with error details
- Tests sector validation
- Handles both bills with and without subject data

**Usage:**
```bash
# Test data extraction only (no API key needed)
python test_classification.py mock_key --no-api

# Test with real API (requires Portkey API key)
python test_classification.py YOUR_API_KEY
```

### 6. Data Extraction Improvements

**Updated `extract_subjects()` function:**
- Now correctly checks `subjects_subj.legislativeSubjects` first
- Extracts 'name' field from list of dicts
- Falls back to other columns if needed
- Provides clear debug output showing what was found

**Verified working examples:**
- Bill 11: 7 subjects extracted successfully
- Bill 40: 3 subjects extracted successfully  
- Bill 66: 10 subjects extracted successfully

## Next Steps

### Step 1: Run Test with Real API Key
Need to test with actual Portkey API to see:
1. Is the API being called correctly?
2. What response comes back from the LLM?
3. Is JSON parsing working?
4. What exactly is causing the NULL values?

**Command:**
```bash
cd /Users/kevinsingh/Downloads/Stats\ Project/LegisRisk
python test_classification.py YOUR_PORTKEY_API_KEY
```

### Step 2: Analyze API Response
Based on the test output, determine:
- Is it an API authentication issue?
- Is it a model/format issue?
- Is it a parsing issue?
- Is it a validation issue?

### Step 3: Fix the Root Cause
Likely fixes needed:
1. **If API error:** Fix authentication or endpoint configuration
2. **If parsing error:** Update JSON extraction logic
3. **If validation error:** Adjust sector matching logic
4. **If data issue:** Handle bills without subjects more gracefully

### Step 4: Update Notebook
Once fixed, update cell_053 in the notebook with:
- Corrected subject extraction (using subjects_subj)
- Any API/parsing fixes discovered
- Improved error handling

## Questions to Answer

1. **Why NULL instead of low-confidence values?**
   - The code has a fallback that returns `{"gics_sectors": None, "confidence": 0.0}` 
   - This happens when ALL retries fail
   - Need to see what errors are occurring during retries

2. **Is the model endpoint correct?**
   - Using: `@vertexai/gemini-2.0-flash-exp`
   - Need to verify this model name works with Portkey

3. **Are there rate limits being hit?**
   - The code processes in concurrent batches
   - May be hitting rate limits causing failures

## Files Created

1. `/Users/kevinsingh/Downloads/Stats Project/LegisRisk/test_classification.py`
   - Comprehensive test script with debug logging
   
2. `/Users/kevinsingh/Downloads/Stats Project/LegisRisk/DEBUG_FINDINGS.md`
   - This documentation file

## Ready for Live Testing

**Please provide your Portkey API key to run the test:**

```bash
cd /Users/kevinsingh/Downloads/Stats\ Project/LegisRisk
python test_classification.py YOUR_PORTKEY_API_KEY
```

This will test with 3 bills and show detailed debug output for each step of the classification process.
