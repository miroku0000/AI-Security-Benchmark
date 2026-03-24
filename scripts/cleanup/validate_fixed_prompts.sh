#!/bin/bash
# Validation script for fixed Level 4 prompts
# Tests hypothesis: "Level 4 degradation was due to wrong examples, not prescriptive approach"

set -e  # Exit on error

echo "================================================================================"
echo "LEVEL 4 PROMPT FIX VALIDATION"
echo "================================================================================"
echo "Hypothesis: Fixed Level 4 prompts should NOT show degradation"
echo "Old Level 4 (deepseek-coder): 59.1% (207/350) - degraded 8.3% from baseline"
echo "Expected with fix: >= 65.7% (Level 3 performance) or better"
echo "================================================================================"
echo ""

# Phase 1: Quick validation with deepseek-coder only
MODEL="deepseek-coder"
LEVEL=4

echo "Phase 1: Testing ${MODEL} with FIXED Level 4 prompts..."
echo ""

# Generate code with fixed prompts
echo "[1/2] Generating code with fixed Level 4 prompts..."
python3 code_generator.py \
  --model $MODEL \
  --prompts prompts_fixed/prompts_level${LEVEL}_security.yaml \
  --output output/${MODEL}_level${LEVEL}_fixed

echo ""
echo "[2/2] Running security analysis..."
python3 runner.py \
  --code-dir output/${MODEL}_level${LEVEL}_fixed \
  --model ${MODEL}_level${LEVEL}_fixed \
  --output reports/${MODEL}_level${LEVEL}_fixed_analysis.json

echo ""
echo "================================================================================"
echo "RESULTS COMPARISON"
echo "================================================================================"

# Extract scores from reports
OLD_SCORE=$(python3 -c "import json; data=json.load(open('reports/${MODEL}_level${LEVEL}_analysis.json' if os.path.exists('reports/${MODEL}_level${LEVEL}_analysis.json') else 'reports/${MODEL}_208point_20260323.json')); print(f\"{data['overall_security_score']['total_score']}/{data['overall_security_score']['max_possible_score']}\")" 2>/dev/null || echo "Unknown")
NEW_SCORE=$(python3 -c "import json; data=json.load(open('reports/${MODEL}_level${LEVEL}_fixed_analysis.json')); print(f\"{data['overall_security_score']['total_score']}/{data['overall_security_score']['max_possible_score']}\")" 2>/dev/null || echo "Unknown")

echo "Old Level 4 (wrong examples):  ${OLD_SCORE} (59.1%)"
echo "New Level 4 (fixed examples):  ${NEW_SCORE} (??.?%)"
echo ""

# Calculate percentage
python3 <<EOF
import json

try:
    # Load new results
    with open('reports/${MODEL}_level${LEVEL}_fixed_analysis.json') as f:
        new_data = json.load(f)

    new_total = new_data['overall_security_score']['total_score']
    new_max = new_data['overall_security_score']['max_possible_score']
    new_pct = (new_total / new_max) * 100

    # Reference scores
    baseline_pct = 67.4
    level3_pct = 65.7
    old_level4_pct = 59.1

    print(f"Detailed Results:")
    print(f"  Baseline (Level 0):     {baseline_pct}%")
    print(f"  Level 3 (old):          {level3_pct}%")
    print(f"  Level 4 (old, broken):  {old_level4_pct}%")
    print(f"  Level 4 (new, fixed):   {new_pct:.1f}%")
    print()

    # Determine outcome
    if new_pct >= level3_pct:
        improvement = new_pct - old_level4_pct
        print(f"✅ HYPOTHESIS CONFIRMED!")
        print(f"   Fixed Level 4 achieved {new_pct:.1f}% (>= Level 3's {level3_pct}%)")
        print(f"   Improvement over broken Level 4: +{improvement:.1f} points")
        print()
        print("   Conclusion: Level 4 degradation WAS due to wrong examples.")
        print("   Prescriptive prompting with CORRECT examples works!")
    elif new_pct >= (old_level4_pct + 3.0):
        improvement = new_pct - old_level4_pct
        print(f"⚠️  PARTIAL CONFIRMATION")
        print(f"   Fixed Level 4 improved to {new_pct:.1f}% (from {old_level4_pct}%)")
        print(f"   Improvement: +{improvement:.1f} points")
        print(f"   But still below Level 3 ({level3_pct}%)")
        print()
        print("   Conclusion: Wrong examples HARMED performance, but prescriptive")
        print("   approach may still have some negative effect.")
    else:
        print(f"❌ HYPOTHESIS REJECTED")
        print(f"   Fixed Level 4: {new_pct:.1f}% (similar to broken: {old_level4_pct}%)")
        print()
        print("   Conclusion: Prescriptive approach itself may be problematic,")
        print("   not just the example quality. Further investigation needed.")

    print()
    print("="*80)

except Exception as e:
    print(f"Error analyzing results: {e}")
    print("Check reports/${MODEL}_level${LEVEL}_fixed_analysis.json manually")
EOF

echo ""
echo "Full report: reports/${MODEL}_level${LEVEL}_fixed_analysis.json"
echo "================================================================================"
echo ""
echo "NEXT STEPS:"
echo ""
echo "If hypothesis confirmed (>= 65.7%):"
echo "  1. Run full retest: ./validate_fixed_prompts_full.sh"
echo "  2. Update MULTI_LEVEL_SECURITY_PROMPTING_FINDINGS.md"
echo "  3. Publish corrected conclusions"
echo ""
echo "If hypothesis rejected (< 62%):"
echo "  1. Investigate other factors (prompt length, verbosity, etc.)"
echo "  2. Consider alternative Level 4 designs"
echo "  3. Document findings on prescriptive prompting limits"
echo "================================================================================"
