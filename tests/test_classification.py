"""
Test script to debug bill classification GICS code issue.
This script adds extensive logging to identify why GICS codes are null.
"""

import json
import polars as pl
from portkey_ai import Portkey
import time
from typing import List, Dict

# ---------------------------------------------------------------------------
# GICS Sectors
# ---------------------------------------------------------------------------

GICS_SECTORS = {
    "Energy": "Oil, gas, coal, and consumable fuels; energy equipment and services",
    "Materials": "Chemicals, construction materials, metals & mining, paper products",
    "Industrials": "Aerospace, defense, building products, construction, machinery, transportation",
    "Consumer Discretionary": "Automobiles, household durables, leisure, hotels, restaurants, retail",
    "Consumer Staples": "Food, beverages, tobacco, household products, personal products",
    "Health Care": "Healthcare equipment, services, pharmaceuticals, biotechnology, life sciences",
    "Financials": "Banks, insurance, capital markets, financial services, consumer finance",
    "Information Technology": "Software, hardware, semiconductors, IT services, communications equipment",
    "Communication Services": "Telecom, media, entertainment, interactive media",
    "Utilities": "Electric, gas, water utilities; independent power producers",
    "Real Estate": "Real estate investment trusts (REITs), real estate management & development"
}

# ---------------------------------------------------------------------------
# Few-Shot Examples
# ---------------------------------------------------------------------------

FEW_SHOT_EXAMPLES = [
    {
        "title": "Affordable Insulin Now Act",
        "policy_area": "Health",
        "subjects": ["prescription drug costs", "medicare", "diabetes"],
        "sectors": ["Health Care"],
        "confidence": 0.95,
        "reasoning": "Directly regulates pharmaceutical pricing"
    },
    {
        "title": "Clean Energy Tax Credit Extension",
        "policy_area": "Energy",
        "subjects": ["renewable energy", "solar power", "tax incentives"],
        "sectors": ["Energy", "Utilities"],
        "confidence": 0.9,
        "reasoning": "Affects energy companies and utilities adopting renewables"
    },
    {
        "title": "Banking Transparency and Accountability Act",
        "policy_area": "Finance and Financial Sector",
        "subjects": ["banking regulation", "financial reporting", "consumer protection"],
        "sectors": ["Financials"],
        "confidence": 0.95,
        "reasoning": "Banking regulation directly impacts Financials sector"
    },
]

# ---------------------------------------------------------------------------
# Classification Prompt
# ---------------------------------------------------------------------------

def create_classification_prompt(title, policy_area, subjects):
    """Create a structured prompt for bill classification."""

    sectors_list = "\n".join([f"- **{name}**: {desc}" for name, desc in GICS_SECTORS.items()])

    examples_text = ""
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        examples_text += f"\n**Example {i}:**\n"
        examples_text += f"Title: {ex['title']}\n"
        examples_text += f"Policy Area: {ex['policy_area']}\n"
        examples_text += f"Subjects: {', '.join(ex['subjects'])}\n"
        examples_text += f"→ Sectors: {', '.join(ex['sectors'])} (confidence: {ex['confidence']})\n"
        examples_text += f"Reasoning: {ex['reasoning']}\n"

    subjects_str = ', '.join(subjects) if subjects else 'Not specified'

    prompt = f"""You are a legislative analyst classifying congressional bills by industry impact.

**GICS Sectors:**
{sectors_list}

**Your Task:**
Classify the following bill into one or more GICS sectors that would be most affected by this legislation.

**Bill Information:**
- Title: {title}
- Policy Area: {policy_area or 'Not specified'}
- Subjects: {subjects_str}

**Few-Shot Examples:**
{examples_text}

**Instructions:**
1. Consider which industries would be directly regulated or impacted
2. A bill can affect multiple sectors (e.g., infrastructure affects Industrials, Materials, IT)
3. Assign a confidence score (0.0-1.0) based on clarity of impact
4. Provide brief reasoning for your classification

**Output Format (JSON only):**
{{
  "sectors": ["Sector1", "Sector2"],
  "confidence": 0.85,
  "reasoning": "Brief explanation of why these sectors"
}}

Return ONLY the JSON, no other text."""

    return prompt

# ---------------------------------------------------------------------------
# Extract Policy Area and Subjects (with DEBUG logging)
# ---------------------------------------------------------------------------

def extract_policy_area(row: Dict) -> str:
    """Extract policy area from nested structure."""
    print("\n[DEBUG] Extracting policy area...")

    # Try different column variations
    for col in ['policyArea', 'policy_area', 'PolicyArea']:
        if col in row and row[col]:
            value = row[col]
            print(f"[DEBUG]   Found column '{col}' with value type: {type(value)}")
            print(f"[DEBUG]   Value: {value}")

            # Handle nested dict structure
            if isinstance(value, dict):
                if 'name' in value:
                    result = value['name']
                    print(f"[DEBUG]   ✓ Extracted policy area: {result}")
                    return result
                else:
                    print(f"[DEBUG]   ✗ Dict has no 'name' key. Keys: {list(value.keys())}")
            elif isinstance(value, str):
                print(f"[DEBUG]   ✓ Policy area is already a string: {value}")
                return value
            else:
                print(f"[DEBUG]   ✗ Unexpected type for policy area")

    print("[DEBUG]   ✗ No policy area found")
    return None

def extract_subjects(row: Dict) -> List[str]:
    """Extract subjects from nested structure."""
    print("\n[DEBUG] Extracting subjects...")

    # Priority 1: Check subjects_subj for legislativeSubjects
    if 'subjects_subj' in row and row['subjects_subj']:
        value = row['subjects_subj']
        print(f"[DEBUG]   Checking 'subjects_subj' column...")
        print(f"[DEBUG]   Value type: {type(value)}")

        if isinstance(value, dict) and 'legislativeSubjects' in value:
            leg_subj = value['legislativeSubjects']
            print(f"[DEBUG]   Found legislativeSubjects: {type(leg_subj)}, length={len(leg_subj) if isinstance(leg_subj, list) else 'N/A'}")

            if isinstance(leg_subj, list) and len(leg_subj) > 0:
                names = [s.get('name', '') for s in leg_subj if isinstance(s, dict) and 'name' in s]
                if names:
                    print(f"[DEBUG]   ✓ Extracted {len(names)} subject names from legislativeSubjects")
                    for name in names:
                        print(f"[DEBUG]     - {name}")
                    return names
                else:
                    print(f"[DEBUG]   ✗ legislativeSubjects list has no name fields")
            else:
                print(f"[DEBUG]   ✗ legislativeSubjects is empty or not a list")

    # Priority 2: Try other column variations
    for col in ['subjects', 'subject', 'Subjects', 'Subject']:
        if col in row and row[col]:
            value = row[col]
            print(f"[DEBUG]   Found column '{col}' with value type: {type(value)}")

            # Handle list of strings
            if isinstance(value, list):
                if len(value) > 0:
                    # Check if first element is string or dict
                    if isinstance(value[0], str):
                        print(f"[DEBUG]   ✓ Subjects are strings: {value}")
                        return value
                    elif isinstance(value[0], dict):
                        # Extract names from list of dicts
                        names = [s.get('name', '') for s in value if isinstance(s, dict) and 'name' in s]
                        if names:
                            print(f"[DEBUG]   ✓ Extracted subject names: {names}")
                            return names

            # Handle nested dict structure
            elif isinstance(value, dict):
                print(f"[DEBUG]   Dict keys: {list(value.keys())}")

                # Check for count and URL pattern (API reference)
                if 'count' in value and 'url' in value:
                    count = value['count']
                    url = value['url']
                    print(f"[DEBUG]   ⚠ Found API reference: count={count}, url={url}")
                    print(f"[DEBUG]   ✗ Subjects are not embedded, need to fetch from API")

            # Handle string
            elif isinstance(value, str):
                print(f"[DEBUG]   ✓ Subject is a string: {value}")
                return [value]

    print("[DEBUG]   ✗ No subjects found - will classify based on title and policy area only")
    return []

# ---------------------------------------------------------------------------
# Single Bill Classification with DEBUG
# ---------------------------------------------------------------------------

def classify_bill_with_debug(
    portkey_client,
    model: str,
    bill_num: int,
    title: str,
    policy_area: str,
    subjects: list,
    max_retries: int = 3
) -> Dict:
    """Classify a single bill with extensive debug logging."""

    print("\n" + "="*80)
    print(f"CLASSIFYING BILL #{bill_num}")
    print("="*80)
    print(f"Title: {title}")
    print(f"Policy Area: {policy_area}")
    print(f"Subjects: {subjects}")

    # Create prompt
    print("\n[DEBUG] Creating classification prompt...")
    prompt = create_classification_prompt(title, policy_area, subjects)

    print(f"\n[DEBUG] Prompt length: {len(prompt)} characters")
    print(f"\n[DEBUG] First 500 chars of prompt:")
    print(prompt[:500])

    for attempt in range(max_retries):
        print(f"\n[DEBUG] Attempt {attempt + 1}/{max_retries}")

        try:
            print("[DEBUG] Calling Portkey API...")
            print(f"[DEBUG]   Model: {model}")
            print(f"[DEBUG]   Max tokens: 500")
            print(f"[DEBUG]   Temperature: 0.1")
            print(f"[DEBUG]   Portkey client type: {type(portkey_client)}")

            # Show request details
            request_msg = {"role": "user", "content": prompt}
            print(f"[DEBUG]   Request message length: {len(str(request_msg))} chars")

            response = portkey_client.chat.completions.create(
                model=model,
                messages=[request_msg],
                max_tokens=500,
                temperature=0.1
            )

            print("[DEBUG] ✓ API call successful!")
            print(f"[DEBUG]   Response object type: {type(response)}")
            print(f"[DEBUG] Response type: {type(response)}")
            print(f"[DEBUG] Response attributes: {dir(response)}")

            # Extract content
            content = response.choices[0].message.content.strip()

            print(f"\n[DEBUG] Raw API response content:")
            print("-" * 80)
            print(content)
            print("-" * 80)

            # Parse JSON
            print("\n[DEBUG] Parsing JSON response...")

            original_content = content

            # Remove markdown code blocks
            if "```json" in content:
                print("[DEBUG]   Removing ```json wrapper...")
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                print("[DEBUG]   Removing ``` wrapper...")
                content = content.split("```")[1].split("```")[0].strip()

            print(f"[DEBUG] Cleaned content:")
            print(content)

            print("\n[DEBUG] Attempting JSON parse...")
            result = json.loads(content)

            print(f"[DEBUG] ✓ JSON parsed successfully!")
            print(f"[DEBUG] Parsed result: {json.dumps(result, indent=2)}")

            # Validate
            print("\n[DEBUG] Validating response format...")

            if "sectors" not in result:
                print("[DEBUG] ✗ ERROR: 'sectors' key not found in response!")
                print(f"[DEBUG]   Available keys: {list(result.keys())}")
                raise ValueError("Invalid response format: missing 'sectors'")

            if "confidence" not in result:
                print("[DEBUG] ✗ ERROR: 'confidence' key not found in response!")
                print(f"[DEBUG]   Available keys: {list(result.keys())}")
                raise ValueError("Invalid response format: missing 'confidence'")

            print(f"[DEBUG] ✓ Response has required keys")
            print(f"[DEBUG]   sectors: {result['sectors']}")
            print(f"[DEBUG]   confidence: {result['confidence']}")

            # Validate sectors
            print("\n[DEBUG] Validating GICS sectors...")
            print(f"[DEBUG]   Valid GICS sectors: {list(GICS_SECTORS.keys())}")

            valid_sectors = []
            for sector in result["sectors"]:
                if sector in GICS_SECTORS:
                    print(f"[DEBUG]   ✓ '{sector}' is valid")
                    valid_sectors.append(sector)
                else:
                    print(f"[DEBUG]   ✗ '{sector}' is NOT a valid GICS sector")

            if not valid_sectors:
                print("[DEBUG] ✗ ERROR: No valid GICS sectors returned!")
                raise ValueError("No valid GICS sectors returned")

            print(f"\n[DEBUG] ✓ Final valid sectors: {valid_sectors}")

            final_result = {
                "bill_num": bill_num,
                "gics_sectors": ', '.join(valid_sectors),
                "confidence": result["confidence"],
                "reasoning": result.get("reasoning", "")
            }

            print(f"\n[DEBUG] ✓✓✓ CLASSIFICATION SUCCESS ✓✓✓")
            print(f"[DEBUG] Final result: {json.dumps(final_result, indent=2)}")

            return final_result

        except json.JSONDecodeError as e:
            print(f"[DEBUG] ✗ JSON Parse Error: {e}")
            print(f"[DEBUG]   Error at position: {e.pos}")
            print(f"[DEBUG]   Content that failed to parse:")
            print(f"[DEBUG]   {content}")

            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"[DEBUG]   Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue

        except AttributeError as e:
            print(f"[DEBUG] ✗ AttributeError: {e}")
            print(f"[DEBUG]   This usually means the API response structure is unexpected")
            print(f"[DEBUG]   Response object: {response if 'response' in locals() else 'Not defined'}")
            import traceback
            print(f"[DEBUG]   Traceback:")
            traceback.print_exc()

            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"[DEBUG]   Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue

        except Exception as e:
            print(f"[DEBUG] ✗ Error: {type(e).__name__}: {e}")
            print(f"[DEBUG]   Error details: {str(e)}")
            import traceback
            print(f"[DEBUG]   Full traceback:")
            traceback.print_exc()

            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"[DEBUG]   Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue

    # Failed after all retries
    print("\n[DEBUG] ✗✗✗ CLASSIFICATION FAILED AFTER ALL RETRIES ✗✗✗")

    return {
        "bill_num": bill_num,
        "gics_sectors": None,
        "confidence": 0.0,
        "reasoning": "Failed after retries"
    }

# ---------------------------------------------------------------------------
# Main Test Function
# ---------------------------------------------------------------------------

def test_classification(
    portkey_api_key: str,
    model: str = "@vertexai/gemini-2.0-flash-exp",
    num_bills: int = 3
):
    """Test classification with debug logging."""

    print("="*80)
    print("BILL CLASSIFICATION DEBUG TEST")
    print("="*80)

    # Initialize Portkey
    print(f"\n[DEBUG] Initializing Portkey client...")
    print(f"[DEBUG]   API key: {portkey_api_key[:10]}...{portkey_api_key[-4:]}")
    print(f"[DEBUG]   Model: {model}")

    try:
        portkey_client = Portkey(api_key=portkey_api_key)
        print("[DEBUG] ✓ Portkey client initialized")
    except Exception as e:
        print(f"[DEBUG] ✗ Failed to initialize Portkey: {e}")
        return

    # Load bills
    parquet_path = '/Users/kevinsingh/Downloads/Stats Project/LegisRisk/final_df_conggov.parquet'
    print(f"\n[DEBUG] Loading bills from: {parquet_path}")

    try:
        df = pl.read_parquet(parquet_path)
        print(f"[DEBUG] ✓ Loaded {len(df)} bills")
        print(f"[DEBUG]   Columns: {df.columns}")
    except Exception as e:
        print(f"[DEBUG] ✗ Failed to load parquet: {e}")
        return

    # Test with first N bills
    print(f"\n[DEBUG] Testing with first {num_bills} bills...")

    results = []

    for i in range(min(num_bills, len(df))):
        row = df[i].to_dicts()[0]

        print(f"\n{'='*80}")
        print(f"PROCESSING BILL {i+1}/{num_bills}")
        print(f"{'='*80}")

        print(f"\n[DEBUG] Raw row data:")
        print(f"[DEBUG]   Type: {row.get('type')}")
        print(f"[DEBUG]   Number: {row.get('number')}")
        print(f"[DEBUG]   Congress: {row.get('congress')}")

        # Extract title
        title = row.get('title', 'Untitled')
        print(f"\n[DEBUG] Title: {title}")

        # Extract policy area (with debug)
        policy_area = extract_policy_area(row)

        # Extract subjects (with debug)
        subjects = extract_subjects(row)

        # Classify with debug
        result = classify_bill_with_debug(
            portkey_client,
            model,
            i + 1,
            title,
            policy_area,
            subjects
        )

        results.append(result)

        # Small delay between API calls
        if i < num_bills - 1:
            print("\n[DEBUG] Waiting 2 seconds before next bill...")
            time.sleep(2)

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    success_count = sum(1 for r in results if r['gics_sectors'] is not None)
    fail_count = len(results) - success_count

    print(f"\nTotal bills tested: {len(results)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")

    print("\n" + "-"*80)
    print("DETAILED RESULTS")
    print("-"*80)

    for result in results:
        print(f"\nBill #{result['bill_num']}:")
        print(f"  GICS Sectors: {result['gics_sectors']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Reasoning: {result['reasoning']}")

    return results

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    print("\n" + "="*80)
    print("BILL CLASSIFICATION DEBUG TEST SCRIPT")
    print("="*80)

    # Check if API key provided
    if len(sys.argv) < 2:
        print("\n[ERROR] Portkey API key required!")
        print("\nUsage:")
        print("  python test_classification.py YOUR_PORTKEY_API_KEY")
        print("\nOr test without API to see data extraction:")
        print("  python test_classification.py mock_key --no-api")
        sys.exit(1)

    api_key = sys.argv[1]

    # Check for no-api flag
    if len(sys.argv) > 2 and sys.argv[2] == "--no-api":
        print("\n[INFO] Running in NO-API mode to test data extraction only")

        # Just test data extraction
        parquet_path = '/Users/kevinsingh/Downloads/Stats Project/LegisRisk/final_df_conggov.parquet'
        df = pl.read_parquet(parquet_path)

        for i in range(3):
            row = df[i].to_dicts()[0]
            print(f"\n{'='*80}")
            print(f"BILL {i+1}")
            print(f"{'='*80}")
            print(f"Title: {row.get('title')}")
            policy_area = extract_policy_area(row)
            subjects = extract_subjects(row)
            print(f"\n[RESULT] Policy Area: {policy_area}")
            print(f"[RESULT] Subjects: {subjects}")
    else:
        # Run full test with API
        results = test_classification(
            portkey_api_key=api_key,
            model="@vertexai/gemini-2.0-flash-exp",
            num_bills=3
        )
