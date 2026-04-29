"""
Mock test to demonstrate expected classification behavior WITHOUT API calls.
This shows what SHOULD happen if the LLM responds correctly.
"""

import json
import polars as pl
from typing import Dict, List

# Import extraction functions from test script
import sys
sys.path.insert(0, '/Users/kevinsingh/Downloads/Stats Project/LegisRisk')
from test_classification import extract_policy_area, extract_subjects, GICS_SECTORS

def mock_llm_response(title: str, policy_area: str, subjects: List[str]) -> Dict:
    """
    Simulate what a correct LLM response should look like.
    This is based on the prompt structure and expected output format.
    """

    # Simulate LLM logic based on policy area and subjects
    mock_responses = {
        "Health": {
            "sectors": ["Health Care"],
            "confidence": 0.9,
            "reasoning": "Health policy directly impacts healthcare sector"
        },
        "Transportation and Public Works": {
            "sectors": ["Industrials", "Materials"],
            "confidence": 0.85,
            "reasoning": "Transportation infrastructure affects industrial and materials sectors"
        },
        "Commerce": {
            "sectors": ["Consumer Discretionary", "Industrials"],
            "confidence": 0.75,
            "reasoning": "Commerce policy affects consumer and industrial sectors"
        },
        "Energy": {
            "sectors": ["Energy", "Utilities"],
            "confidence": 0.9,
            "reasoning": "Energy policy directly impacts energy and utility sectors"
        },
        "Financials": {
            "sectors": ["Financials"],
            "confidence": 0.95,
            "reasoning": "Financial regulation directly affects financial sector"
        },
        "Families": {
            "sectors": ["Consumer Staples", "Health Care"],
            "confidence": 0.7,
            "reasoning": "Family policy may affect consumer staples and healthcare"
        },
        "Congress": {
            "sectors": ["Industrials"],  # Government operations
            "confidence": 0.5,
            "reasoning": "Congressional operations have indirect industrial impact"
        },
        "Environmental Protection": {
            "sectors": ["Energy", "Materials", "Utilities"],
            "confidence": 0.85,
            "reasoning": "Environmental regulation affects energy, materials, and utilities"
        }
    }

    # Get mock response based on policy area
    if policy_area in mock_responses:
        return mock_responses[policy_area]
    else:
        # Default fallback
        return {
            "sectors": ["Industrials"],
            "confidence": 0.5,
            "reasoning": f"Indirect impact on industrial sector for {policy_area}"
        }

def test_mock_classification():
    """Test classification with mocked LLM responses."""

    print("="*80)
    print("MOCK CLASSIFICATION TEST - Demonstrating Expected Behavior")
    print("="*80)
    print("\nThis test shows what SHOULD happen if the LLM API works correctly.\n")

    # Load data
    parquet_path = '/Users/kevinsingh/Downloads/Stats Project/LegisRisk/final_df_conggov.parquet'
    df = pl.read_parquet(parquet_path)

    # Test with first 5 bills
    results = []

    for i in range(5):
        row = df[i].to_dicts()[0]

        print(f"\n{'='*80}")
        print(f"BILL {i+1}/5")
        print(f"{'='*80}")

        # Extract data
        title = row.get('title', 'Untitled')
        policy_area = extract_policy_area(row)
        subjects = extract_subjects(row)

        print(f"Title: {title[:70]}")
        print(f"Policy Area: {policy_area}")
        print(f"Subjects: {subjects if subjects else '(none)'}")

        # Simulate LLM response
        print("\n[MOCK LLM] Generating classification...")
        llm_response = mock_llm_response(title, policy_area, subjects)

        # Simulate JSON parsing
        print(f"[MOCK LLM] Response: {json.dumps(llm_response, indent=2)}")

        # Validate sectors (same logic as real code)
        print("\n[VALIDATION] Validating GICS sectors...")
        valid_sectors = []
        for sector in llm_response["sectors"]:
            if sector in GICS_SECTORS:
                print(f"  ✓ '{sector}' is valid")
                valid_sectors.append(sector)
            else:
                print(f"  ✗ '{sector}' is NOT valid")

        if valid_sectors:
            result = {
                "bill_num": i + 1,
                "title": title[:60],
                "gics_sectors": ', '.join(valid_sectors),
                "confidence": llm_response["confidence"],
                "reasoning": llm_response["reasoning"]
            }
            print(f"\n[RESULT] ✓ Classification SUCCESS")
            print(f"  GICS: {result['gics_sectors']}")
            print(f"  Confidence: {result['confidence']}")
        else:
            result = {
                "bill_num": i + 1,
                "title": title[:60],
                "gics_sectors": None,
                "confidence": 0.0,
                "reasoning": "No valid sectors"
            }
            print(f"\n[RESULT] ✗ Classification FAILED - No valid sectors")

        results.append(result)

    # Summary
    print("\n" + "="*80)
    print("MOCK TEST SUMMARY")
    print("="*80)

    success_count = sum(1 for r in results if r['gics_sectors'] is not None)
    print(f"\nTotal: {len(results)}")
    print(f"Success: {success_count} ({success_count/len(results)*100:.0f}%)")
    print(f"Failed: {len(results) - success_count}")

    print("\n" + "-"*80)
    print("RESULTS")
    print("-"*80)

    for r in results:
        status = "✓" if r['gics_sectors'] else "✗"
        print(f"\n{status} Bill {r['bill_num']}: {r['title']}")
        print(f"   GICS: {r['gics_sectors']}")
        print(f"   Confidence: {r['confidence']}")

    print("\n" + "="*80)
    print("EXPECTED vs ACTUAL")
    print("="*80)
    print("\nEXPECTED (this mock test):")
    print(f"  - {success_count} successful classifications")
    print(f"  - Even bills without subjects get some classification")
    print(f"  - NULL only if validation fails")

    print("\nACTUAL (from bills_classified.parquet):")
    print("  - 0 successful classifications (100% NULL)")
    print("  - All bills have gics_sectors=None, confidence=0.0")
    print("  - Indicates systematic failure in actual implementation")

    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print("\nSince the mock works but actual doesn't, the issue is likely:")
    print("  1. Portkey API not being called correctly")
    print("  2. API returning errors (authentication, model name, etc.)")
    print("  3. Response format not matching expectations")
    print("  4. Exception being caught but not logged properly")
    print("\nNext step: Run test_classification.py with REAL API key to see errors")

if __name__ == "__main__":
    test_mock_classification()
