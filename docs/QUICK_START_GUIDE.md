# Quick Start Guide - Debugging GICS Classification

## Current Status
- **100% of bills have NULL GICS codes** (0/1000 successful)
- Classification function ran but all attempts failed
- Need to identify why API calls are failing

## Key Findings

### Data Issues (FIXED)
✓ Policy area extraction working correctly
✓ Subject extraction now works (reads from `subjects_subj.legislativeSubjects`)
⚠ Only 3.4% of bills have subject data, but this shouldn't cause NULL values

### Root Cause (TO BE CONFIRMED)
The most likely cause is one of:
1. **Portkey API authentication issue**
2. **Model name incorrect** (`@vertexai/gemini-2.0-flash-exp`)
3. **Response format unexpected**
4. **Rate limiting or API errors**

## Quick Test (You Need Your API Key)

### Option 1: Full Debug Test (Recommended)
Test with 3 bills to see detailed API interaction:

```bash
cd /Users/kevinsingh/Downloads/Stats\ Project/LegisRisk
python3 test_classification.py YOUR_PORTKEY_API_KEY
```

**What this shows:**
- Exact API request being sent
- Full API response received
- JSON parsing steps
- Validation logic
- Where it fails (if it fails)

### Option 2: Single Bill Test
If you want to test just one bill quickly:

```bash
cd /Users/kevinsingh/Downloads/Stats\ Project/LegisRisk
python3 -c "
from test_classification import test_classification
test_classification('YOUR_PORTKEY_API_KEY', num_bills=1)
"
```

### Option 3: Mock Test (No API Key)
To verify the logic works in principle:

```bash
cd /Users/kevinsingh/Downloads/Stats\ Project/LegisRisk
python3 test_mock_classification.py
```

This shows what SHOULD happen if API works correctly.

## Expected Test Output

### If Working Correctly:
```
[DEBUG] Calling Portkey API...
[DEBUG] ✓ API call successful!
[DEBUG] Raw API response content:
{
  "sectors": ["Health Care"],
  "confidence": 0.9,
  "reasoning": "Health policy directly impacts healthcare"
}
[DEBUG] ✓ JSON parsed successfully!
[DEBUG] ✓ Final valid sectors: ['Health Care']
[DEBUG] ✓✓✓ CLASSIFICATION SUCCESS ✓✓✓
```

### If API Authentication Error:
```
[DEBUG] Calling Portkey API...
[DEBUG] ✗ Error: AuthenticationError: Invalid API key
```

### If Model Name Error:
```
[DEBUG] Calling Portkey API...
[DEBUG] ✗ Error: InvalidRequestError: Model '@vertexai/gemini-2.0-flash-exp' not found
```

### If Response Format Error:
```
[DEBUG] ✓ API call successful!
[DEBUG] Raw API response content:
<unexpected format>
[DEBUG] ✗ AttributeError: 'NoneType' object has no attribute 'content'
```

## Common Issues & Fixes

### Issue 1: Invalid API Key
**Symptom:** `AuthenticationError` in test output
**Fix:** Verify your Portkey API key is correct

### Issue 2: Wrong Model Name
**Symptom:** `Model not found` error
**Fix:** Check correct model name in Portkey dashboard
- Current: `@vertexai/gemini-2.0-flash-exp`
- Alternative: `@vertexai/gemini-2.0-flash-thinking-exp`

### Issue 3: Virtual Key Required
**Symptom:** Model access error even with valid API key
**Fix:** May need to configure virtual key in Portkey for Vertex AI access

### Issue 4: Rate Limiting
**Symptom:** First few work, then start failing
**Fix:** Reduce `max_workers` and `chunk_size` in classification function

## After Identifying the Issue

Once you know what's wrong, I'll help you:

1. **Update the classification function** in the notebook
2. **Fix the data extraction** to use `subjects_subj`
3. **Add proper error handling** to avoid silent failures
4. **Re-run classification** on all 1000 bills

## Files Created

1. **test_classification.py** - Full debug test script (needs API key)
2. **test_mock_classification.py** - Mock test (no API key needed)
3. **DEBUG_FINDINGS.md** - Detailed investigation findings
4. **QUICK_START_GUIDE.md** - This file

## Next Step

**Run the test with your API key:**

```bash
cd /Users/kevinsingh/Downloads/Stats\ Project/LegisRisk
python3 test_classification.py YOUR_PORTKEY_API_KEY
```

Then share the output so we can see exactly what's failing!
