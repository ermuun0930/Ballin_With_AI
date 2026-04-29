"""
Diagnostic script to identify the exact issue causing NULL GICS codes.
This compares the ORIGINAL notebook logic vs FIXED logic.
"""

import polars as pl
from typing import Dict, List

def extract_subjects_ORIGINAL(row: Dict) -> List[str]:
    """
    ORIGINAL logic from notebook (BUGGY).
    This is what's currently in cell_053.
    """
    subjects = []
    for subj_col in ['subjects', 'subject', 'Subjects', 'Subject']:
        if subj_col in row and row[subj_col]:
            val = row[subj_col]
            if isinstance(val, list):
                subjects = val
                break
            elif isinstance(val, str):
                subjects = [val]
                break
    return subjects

def extract_subjects_FIXED(row: Dict) -> List[str]:
    """
    FIXED logic that checks subjects_subj first.
    """
    # Priority 1: Check subjects_subj for legislativeSubjects
    if 'subjects_subj' in row and row['subjects_subj']:
        value = row['subjects_subj']
        if isinstance(value, dict) and 'legislativeSubjects' in value:
            leg_subj = value['legislativeSubjects']
            if isinstance(leg_subj, list) and len(leg_subj) > 0:
                names = [s.get('name', '') for s in leg_subj if isinstance(s, dict) and 'name' in s]
                if names:
                    return names

    # Fallback to original logic
    return extract_subjects_ORIGINAL(row)

def diagnose():
    """Run diagnostic comparison."""

    print("="*80)
    print("DIAGNOSTIC: Original vs Fixed Subject Extraction")
    print("="*80)

    # Load data
    df = pl.read_parquet('/Users/kevinsingh/Downloads/Stats Project/LegisRisk/final_df_conggov.parquet')

    print(f"\nTotal bills: {len(df)}")

    # Test extraction on all bills
    original_success = 0
    fixed_success = 0
    difference_cases = []

    for i in range(len(df)):
        row = df[i].to_dicts()[0]

        original_subjects = extract_subjects_ORIGINAL(row)
        fixed_subjects = extract_subjects_FIXED(row)

        if len(original_subjects) > 0:
            original_success += 1

        if len(fixed_subjects) > 0:
            fixed_success += 1

        # Track cases where fixed finds subjects but original doesn't
        if len(fixed_subjects) > 0 and len(original_subjects) == 0:
            difference_cases.append({
                'index': i,
                'title': row.get('title', 'N/A'),
                'fixed_subjects': fixed_subjects
            })

    print(f"\n{'='*80}")
    print("RESULTS")
    print("="*80)

    print(f"\nOriginal Logic:")
    print(f"  - Bills with subjects: {original_success}/{len(df)} ({original_success/len(df)*100:.1f}%)")
    print(f"  - Bills without subjects: {len(df) - original_success}")

    print(f"\nFixed Logic:")
    print(f"  - Bills with subjects: {fixed_success}/{len(df)} ({fixed_success/len(df)*100:.1f}%)")
    print(f"  - Bills without subjects: {len(df) - fixed_success}")

    print(f"\nDifference:")
    print(f"  - Additional bills found by fixed logic: {len(difference_cases)}")

    if difference_cases:
        print(f"\n{'='*80}")
        print("EXAMPLES WHERE FIXED LOGIC FINDS SUBJECTS")
        print("="*80)

        for case in difference_cases[:5]:
            print(f"\nBill {case['index']}: {case['title'][:60]}")
            print(f"  Subjects found: {len(case['fixed_subjects'])}")
            for subj in case['fixed_subjects'][:3]:
                print(f"    - {subj}")

    print(f"\n{'='*80}")
    print("IMPACT ON CLASSIFICATION")
    print("="*80)

    print(f"\nThe ORIGINAL logic (in notebook) finds subjects for only {original_success} bills.")
    print(f"This means {len(df) - original_success} bills are classified with ONLY:")
    print("  - Title")
    print("  - Policy Area")
    print("  - NO subjects")

    print(f"\nHowever, even without subjects, the LLM should still return SOME classification.")
    print(f"The fact that ALL 1000 bills have NULL GICS codes suggests a different issue:")
    print("\n  Possible causes:")
    print("  1. API authentication failure")
    print("  2. Model name incorrect (used '@vertexai/gemini-3-flash-preview')")
    print("  3. API returns errors that are silently caught")
    print("  4. Response format doesn't match expectations")
    print("  5. All retries exhausted for every single bill")

    print(f"\n{'='*80}")
    print("NEXT STEPS")
    print("="*80)

    print("\n1. Test with actual API key to see real error messages:")
    print("   python3 test_classification.py YOUR_API_KEY")

    print("\n2. If API works, update notebook with fixed subject extraction")

    print("\n3. Re-run classification on all bills")

    print(f"\n{'='*80}")
    print("KEY INSIGHT")
    print("="*80)

    print("\nThe subject extraction bug affects DATA QUALITY but shouldn't cause NULL values.")
    print("NULL values indicate COMPLETE FAILURE of API calls or response parsing.")
    print("\nWe need to see actual API errors to diagnose the root cause.")

if __name__ == "__main__":
    diagnose()
