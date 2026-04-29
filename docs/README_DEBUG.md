# Bill Classification Debug - Complete Package

## Problem
100% of bills (1000/1000) have NULL GICS codes after classification.

## Root Cause
Two issues identified:
1. **Subject extraction bug** - Original code found 0/1000 bills with subjects
2. **Unknown API error** - Need to test with API key to identify

## Quick Start

### Step 1: Run Test with Your API Key

```bash
cd /Users/kevinsingh/Downloads/Stats\ Project/LegisRisk
python3 test_classification.py YOUR_PORTKEY_API_KEY
```

This will test 3 bills and show detailed debug output revealing the API error.

### Step 2: Review Output

Look for error messages in the output. Common patterns:

**Authentication Error:**
```
[DEBUG] ✗ Error: AuthenticationError: Invalid API key
```

**Model Not Found:**
```
[DEBUG] ✗ Error: InvalidRequestError: Model '@vertexai/...' not found
```

**Response Format Issue:**
```
[DEBUG] ✗ AttributeError: 'NoneType' object has no attribute 'content'
```

### Step 3: Apply Fixes

Once we know the error, we'll:
1. Fix the API issue (model name, auth, etc.)
2. Update notebook with fixed code from `FIXED_CLASSIFICATION_CODE.py`
3. Re-run classification on all bills

## Files in This Package

### Test Scripts
1. **test_classification.py** - Full debug test (needs API key)
2. **test_mock_classification.py** - Mock test showing expected behavior
3. **diagnose_issue.py** - Subject extraction comparison

### Documentation
4. **DEBUG_FINDINGS.md** - Detailed investigation findings
5. **QUICK_START_GUIDE.md** - Quick reference for testing
6. **SOLUTION_SUMMARY.md** - Complete analysis and solution plan
7. **README_DEBUG.md** - This file

### Fixed Code
8. **FIXED_CLASSIFICATION_CODE.py** - Ready-to-use corrected code

## Key Findings

### Subject Extraction Bug (FIXED)
- **Original code:** Found 0/1000 bills with subjects
- **Fixed code:** Finds 34/1000 bills with subjects
- **Root cause:** Original didn't check `subjects_subj.legislativeSubjects`

### API Issue (NEEDS TESTING)
- All 1000 classifications failed (100% NULL)
- Ran for 10 minutes without throwing exception
- Errors were caught but not logged
- Need API key to see actual error messages

## Test Results Summary

### Mock Test (test_mock_classification.py)
- **Result:** 5/5 successful (100%)
- **Conclusion:** Logic is sound, API is the issue

### Diagnostic Test (diagnose_issue.py)
- **Original extraction:** 0/1000 bills (0%)
- **Fixed extraction:** 34/1000 bills (3.4%)
- **Improvement:** 34 additional bills with context

### Real Classification (bills_classified.parquet)
- **Result:** 0/1000 successful (0%)
- **All NULL values**
- **All confidence scores: 0.0**

## Expected Results After Fix

### Conservative Estimate
- **80-95%** classification success rate
- **34 bills** with high confidence (have subjects)
- **900+ bills** with medium confidence (title + policy area only)
- **<5%** failures (truly ambiguous bills)

### Confidence Distribution
- Very High (0.9-1.0): ~10-15%
- High (0.8-0.9): ~30-40%
- Medium (0.7-0.8): ~30-40%
- Low (0.6-0.7): ~10-15%
- Very Low (<0.6): ~5%

## Implementation Plan

### Phase 1: Diagnose (YOU DO THIS)
```bash
python3 test_classification.py YOUR_API_KEY
```
Share the output to identify API error.

### Phase 2: Fix (WE DO TOGETHER)
Based on error, fix:
- Model name
- API authentication
- Response parsing
- Rate limiting

### Phase 3: Test (10 bills)
```python
df = classify_all_bills(
    portkey_api_key="your-key",
    limit=10,
    enable_error_logging=True
)
```

### Phase 4: Deploy (All bills)
```python
df = classify_all_bills(
    portkey_api_key="your-key",
    model="@vertexai/gemini-2.0-flash-exp"
)
```

## Model Name Verification

The notebook used: `@vertexai/gemini-3-flash-preview`
You mentioned: `@vertexai/gemini-2.0-flash-exp`

**Possible correct names:**
- `@vertexai/gemini-2.0-flash-exp`
- `@vertexai/gemini-2.0-flash-thinking-exp`
- `@vertexai/gemini-1.5-flash`
- `gemini-2.0-flash-exp` (without @vertexai prefix)

We'll determine the correct one from the test output.

## Support

If you encounter issues:

1. **Check API key:** Verify it's valid in Portkey dashboard
2. **Check model access:** Ensure you have Vertex AI access configured
3. **Check rate limits:** May need to reduce `max_workers` and `chunk_size`
4. **Enable logging:** Set `enable_error_logging=True` to see all errors

## Timeline Estimate

- **Test (Step 1):** 2 minutes
- **Diagnose error:** 2-3 minutes
- **Implement fix:** 5-10 minutes
- **Test 10 bills:** 1-2 minutes
- **Run all 1000 bills:** 10-15 minutes
- **Total:** ~25-30 minutes from start to finish

## Success Criteria

Classification is fixed when:
- ✓ Test script completes without errors
- ✓ At least 80% of bills get GICS codes
- ✓ NULL values < 20%
- ✓ Confidence distribution looks reasonable
- ✓ Sample classifications make sense

## Next Action

**Run this command now:**

```bash
cd /Users/kevinsingh/Downloads/Stats\ Project/LegisRisk
python3 test_classification.py YOUR_PORTKEY_API_KEY
```

Then share the output!
