#!/usr/bin/env python3
"""
Test script for LLM-assisted vulnerability matching

This script tests the LLM matcher with sample data to verify functionality.
"""

from llm_matcher import LLMAssistedMatcher, create_ollama_config, test_llm_connection
from sast_comparison import Vulnerability

def create_test_data():
    """Create sample vulnerability data for testing"""

    # Sample benchmark vulnerabilities
    benchmark_vulns = [
        Vulnerability(
            file_path="login.php",
            line_number=42,
            vuln_type="sql_injection",
            severity="HIGH",
            description="SQL injection in user authentication",
            source="benchmark"
        ),
        Vulnerability(
            file_path="search.php",
            line_number=18,
            vuln_type="xss",
            severity="MEDIUM",
            description="Reflected XSS in search parameter",
            source="benchmark"
        ),
        Vulnerability(
            file_path="upload.php",
            line_number=67,
            vuln_type="path_traversal",
            severity="HIGH",
            description="Directory traversal in file upload",
            source="benchmark"
        )
    ]

    # Sample SAST tool findings
    sast_vulns = [
        Vulnerability(
            file_path="login.php",
            line_number=43,
            vuln_type="tainted-sql-string",
            severity="HIGH",
            description="SQL injection vulnerability detected",
            source="sast"
        ),
        Vulnerability(
            file_path="search.php",
            line_number=19,
            vuln_type="reflected-xss",
            severity="MEDIUM",
            description="Cross-site scripting vulnerability",
            source="sast"
        ),
        Vulnerability(
            file_path="upload.php",
            line_number=68,
            vuln_type="path-injection",
            severity="HIGH",
            description="Path traversal vulnerability found",
            source="sast"
        ),
        Vulnerability(
            file_path="config.php",
            line_number=12,
            vuln_type="hardcoded-secret",
            severity="LOW",
            description="Hardcoded password detected",
            source="sast"
        )
    ]

    return benchmark_vulns, sast_vulns

def test_basic_functionality():
    """Test basic LLM matcher functionality without LLM calls"""
    print("🧪 Testing basic functionality...")

    # Create test configuration (won't actually call LLM)
    config = create_ollama_config()
    matcher = LLMAssistedMatcher(config, confidence_threshold=0.8)

    benchmark_vulns, sast_vulns = create_test_data()

    # Test candidate finding
    for i, benchmark_vuln in enumerate(benchmark_vulns):
        candidates = matcher._find_candidates(benchmark_vuln, sast_vulns)
        print(f"   Benchmark {i+1} ({benchmark_vuln.vuln_type}): {len(candidates)} candidates")

        for candidate in candidates:
            similarity = matcher._calculate_similarity(benchmark_vuln, candidate)
            print(f"     - {candidate.vuln_type} (similarity: {similarity:.2f})")

    print("✅ Basic functionality test passed")

def test_llm_connection_only():
    """Test LLM connection without full matching"""
    print("\n🔗 Testing LLM connection...")

    config = create_ollama_config()

    if test_llm_connection(config):
        print("✅ LLM connection successful")

        # Test simple LLM call
        try:
            matcher = LLMAssistedMatcher(config, confidence_threshold=0.8)

            # Simple test prompt
            test_prompt = """You are a cybersecurity expert. Respond with valid JSON only:
{
  "status": "working",
  "message": "LLM is functioning correctly"
}"""

            response = matcher._call_llm(test_prompt)
            print(f"✅ LLM response received: {len(response)} characters")
            print(f"   Sample: {response[:100]}...")

        except Exception as e:
            print(f"❌ LLM call failed: {e}")
            return False

    else:
        print("❌ LLM connection failed")
        print("   Make sure Ollama is running: ollama serve")
        return False

    return True

def test_full_matching():
    """Test full LLM matching with real LLM calls"""
    print("\n🤖 Testing full LLM matching...")

    config = create_ollama_config()
    matcher = LLMAssistedMatcher(config, confidence_threshold=0.7)

    benchmark_vulns, sast_vulns = create_test_data()

    try:
        matches = matcher.match_vulnerabilities(benchmark_vulns, sast_vulns)

        print(f"\n📊 Matching Results:")
        print(f"   Total matches found: {len(matches)}")

        for match in matches:
            print(f"\n   Match: {match.confidence:.1%} confidence")
            print(f"   Type: {match.match_type}")
            print(f"   Reasoning: {match.reasoning}")

        matcher.print_stats()
        print("✅ Full matching test completed")

        return len(matches) > 0

    except Exception as e:
        print(f"❌ Full matching test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 LLM Matcher Test Suite")
    print("=" * 40)

    # Basic functionality (no LLM required)
    test_basic_functionality()

    # LLM connection test
    llm_available = test_llm_connection_only()

    # Full matching test (requires LLM)
    if llm_available:
        print("\n⚠️  Full matching test will make actual LLM API calls")
        choice = input("Proceed with LLM matching test? (y/n): ").lower().strip()

        if choice in ['y', 'yes']:
            success = test_full_matching()
            if success:
                print("\n✅ All tests passed! LLM matching is working correctly.")
            else:
                print("\n⚠️  LLM matching test had issues - check the output above.")
        else:
            print("\n⏭️  Skipping LLM matching test")
    else:
        print("\n⚠️  LLM not available - run 'python setup_llm.py' to configure")

    print("\n" + "=" * 40)
    print("Test completed!")

if __name__ == "__main__":
    main()