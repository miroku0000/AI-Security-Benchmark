#!/usr/bin/env python3
"""
LLM-Assisted Vulnerability Matching

Uses local LLM models to intelligently match benchmark vulnerabilities
with SAST tool findings based on semantic analysis.

Supports:
- Ollama (recommended for local deployment)
- OpenAI-compatible APIs
- Transformers library with local models
"""

import json
import re
import requests
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class LLMMatch:
    """Represents a vulnerability match suggested by LLM"""
    benchmark_id: str
    sast_id: str
    confidence: float
    reasoning: str
    match_type: str  # 'exact', 'similar', 'related'

@dataclass
class LLMConfig:
    """Configuration for LLM model"""
    model_name: str
    base_url: str
    timeout: int = 30
    max_retries: int = 3
    temperature: float = 0.1  # Low temperature for consistent analysis

class LLMAssistedMatcher:
    """Main class for LLM-based vulnerability matching"""

    def __init__(self, config: LLMConfig, confidence_threshold: float = 0.8):
        self.config = config
        self.confidence_threshold = confidence_threshold
        self.stats = {
            'total_analyzed': 0,
            'high_confidence_matches': 0,
            'api_calls': 0,
            'failed_calls': 0
        }

    def match_vulnerabilities(self, benchmark_vulns: List, sast_vulns: List) -> List[LLMMatch]:
        """
        Use LLM to match SAST findings with benchmark vulnerabilities (more efficient approach)

        Args:
            benchmark_vulns: List of benchmark Vulnerability objects
            sast_vulns: List of SAST Vulnerability objects

        Returns:
            List of LLMMatch objects with confidence scores
        """
        print(f"🤖 Starting LLM analysis with {self.config.model_name}")
        print(f"📊 Analyzing {len(sast_vulns)} SAST findings against {len(benchmark_vulns)} benchmark vulns")
        print(f"💡 Using SAST-first approach for {len(sast_vulns)}x efficiency improvement")

        all_matches = []

        for i, sast_vuln in enumerate(sast_vulns):
            print(f"🔍 Analyzing SAST finding {i+1}/{len(sast_vulns)}: {sast_vuln.vuln_type} in {sast_vuln.file_path}:{sast_vuln.line_number}")

            # Find potential benchmark candidates for this SAST finding
            candidates = self._find_benchmark_candidates(sast_vuln, benchmark_vulns)

            if not candidates:
                print(f"   ⚪ No matching benchmark vulnerabilities found (potential false positive)")
                continue

            print(f"   📋 Found {len(candidates)} potential benchmark matches")

            # Use LLM to analyze candidates
            try:
                matches = self._analyze_sast_with_llm(sast_vuln, candidates, i)
                all_matches.extend(matches)
                self.stats['total_analyzed'] += 1

                high_conf = [m for m in matches if m.confidence >= self.confidence_threshold]
                if high_conf:
                    self.stats['high_confidence_matches'] += len(high_conf)
                    print(f"   ✅ {len(high_conf)} high confidence matches found (true positive)")
                else:
                    print(f"   ⚠️  {len(matches)} low confidence matches (needs review)")

            except Exception as e:
                print(f"   ❌ LLM analysis failed: {str(e)}")
                self.stats['failed_calls'] += 1
                continue

        return all_matches

    def _find_benchmark_candidates(self, sast_vuln, benchmark_vulns: List) -> List:
        """Find potential benchmark vulnerabilities that might match a SAST finding"""
        candidates = []

        for bench_vuln in benchmark_vulns:
            score = 0

            # File path similarity (highest weight)
            if sast_vuln.file_path == bench_vuln.file_path:
                score += 50
            elif Path(sast_vuln.file_path).name == Path(bench_vuln.file_path).name:
                score += 30
            elif self._files_related(sast_vuln.file_path, bench_vuln.file_path):
                score += 20

            # Line proximity
            line_diff = abs(sast_vuln.line_number - bench_vuln.line_number)
            if line_diff <= 2:
                score += 30
            elif line_diff <= 5:
                score += 20
            elif line_diff <= 10:
                score += 10

            # Vulnerability type similarity
            if self._types_similar(sast_vuln.vuln_type, bench_vuln.vuln_type):
                score += 20

            # Only consider candidates with some basic similarity
            if score >= 30:  # Minimum threshold for LLM analysis
                candidates.append((bench_vuln, score))

        # Sort by score and limit to top 5 candidates for LLM efficiency
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [candidate[0] for candidate in candidates[:5]]

    def _find_candidates(self, benchmark_vuln, sast_vulns: List) -> List:
        """Find potential SAST candidates for a benchmark vulnerability"""
        candidates = []

        for sast_vuln in sast_vulns:
            score = 0

            # File path similarity (highest weight)
            if benchmark_vuln.file_path == sast_vuln.file_path:
                score += 50
            elif Path(benchmark_vuln.file_path).name == Path(sast_vuln.file_path).name:
                score += 30
            elif self._files_related(benchmark_vuln.file_path, sast_vuln.file_path):
                score += 20

            # Line proximity
            line_diff = abs(benchmark_vuln.line_number - sast_vuln.line_number)
            if line_diff <= 2:
                score += 30
            elif line_diff <= 5:
                score += 20
            elif line_diff <= 10:
                score += 10

            # Vulnerability type similarity
            if self._types_similar(benchmark_vuln.vuln_type, sast_vuln.vuln_type):
                score += 20

            # Only consider candidates with some basic similarity
            if score >= 30:  # Minimum threshold for LLM analysis
                candidates.append(sast_vuln)

        # Sort by similarity and limit to top 5 candidates for LLM efficiency
        candidates.sort(key=lambda v: self._calculate_similarity(benchmark_vuln, v), reverse=True)
        return candidates[:5]

    def _analyze_sast_with_llm(self, sast_vuln, candidates: List, sast_index: int) -> List[LLMMatch]:
        """Send SAST finding and benchmark candidates to LLM for analysis (SAST-first approach)"""
        prompt = self._build_sast_analysis_prompt(sast_vuln, candidates)

        try:
            response = self._call_llm(prompt)
            return self._parse_sast_llm_response(response, sast_vuln, candidates, sast_index)
        except Exception as e:
            print(f"   ❌ LLM API call failed: {e}")
            raise

    def _analyze_with_llm(self, benchmark_vuln, candidates: List, bench_index: int) -> List[LLMMatch]:
        """Send vulnerability data to LLM for semantic analysis"""
        prompt = self._build_analysis_prompt(benchmark_vuln, candidates)

        try:
            response = self._call_llm(prompt)
            return self._parse_llm_response(response, benchmark_vuln, candidates, bench_index)
        except Exception as e:
            print(f"   ❌ LLM API call failed: {e}")
            raise

    def _build_analysis_prompt(self, benchmark_vuln, candidates: List) -> str:
        """Build detailed prompt for LLM vulnerability analysis"""
        prompt = f"""You are a cybersecurity expert analyzing vulnerability matches between a security benchmark and SAST tool output.

BENCHMARK VULNERABILITY (Ground Truth):
File: {benchmark_vuln.file_path}
Line: {benchmark_vuln.line_number}
Type: {benchmark_vuln.vuln_type}
Severity: {getattr(benchmark_vuln, 'severity', 'UNKNOWN')}
Description: {getattr(benchmark_vuln, 'description', 'No description')}

SAST TOOL CANDIDATES:"""

        for i, candidate in enumerate(candidates):
            prompt += f"""

Candidate {i+1}:
File: {candidate.file_path}
Line: {candidate.line_number}
Type: {candidate.vuln_type}
Severity: {getattr(candidate, 'severity', 'UNKNOWN')}
Description: {getattr(candidate, 'description', 'No description')}"""

        prompt += """

ANALYSIS TASK:
Determine if any SAST candidates represent the same vulnerability as the benchmark.

EVALUATION CRITERIA:
1. File Location: Same file or related files?
2. Line Proximity: How close are the line numbers?
3. Vulnerability Type: Do the types represent the same security issue?
4. Semantic Similarity: Do descriptions indicate same underlying vulnerability?
5. Context Clues: Consider code patterns, variable names, function contexts

CONFIDENCE LEVELS:
- 0.95+: Nearly identical (same file, same line, same vuln type)
- 0.85-0.94: Very likely match (same file, close lines, equivalent vuln types)
- 0.70-0.84: Probable match (related files or similar vulnerability patterns)
- 0.50-0.69: Possible match (some similarities but uncertain)
- 0.00-0.49: Unlikely match (significant differences)

RESPOND WITH VALID JSON ONLY:
{
  "matches": [
    {
      "candidate_id": 1,
      "confidence": 0.92,
      "match_type": "exact",
      "reasoning": "Same file (login.php), adjacent lines (42 vs 43), both SQL injection vulnerabilities with similar parameter handling"
    }
  ]
}

IMPORTANT: Only include matches with confidence >= 0.5. If no good matches, return empty matches array."""

        return prompt

    def _build_sast_analysis_prompt(self, sast_vuln, candidates: List) -> str:
        """Build prompt for SAST-first analysis (is this SAST finding a true or false positive?)"""
        prompt = f"""You are a cybersecurity expert analyzing whether SAST tool findings represent true positives (match known vulnerabilities) or false positives.

SAST TOOL FINDING (To Be Classified):
File: {sast_vuln.file_path}
Line: {sast_vuln.line_number}
Type: {sast_vuln.vuln_type}
Severity: {getattr(sast_vuln, 'severity', 'UNKNOWN')}
Description: {getattr(sast_vuln, 'description', 'No description')}

BENCHMARK VULNERABILITY CANDIDATES (Known Ground Truth):"""

        for i, candidate in enumerate(candidates):
            prompt += f"""

Benchmark {i+1}:
File: {candidate.file_path}
Line: {candidate.line_number}
Type: {candidate.vuln_type}
Severity: {getattr(candidate, 'severity', 'UNKNOWN')}
Description: {getattr(candidate, 'description', 'No description')}"""

        prompt += """

ANALYSIS TASK:
Determine if the SAST finding matches any of the known benchmark vulnerabilities (true positive) or is likely a false positive.

EVALUATION CRITERIA:
1. File Location: Same file or related files?
2. Line Proximity: How close are the line numbers?
3. Vulnerability Type: Do the types represent the same security issue?
4. Semantic Similarity: Do descriptions indicate same underlying vulnerability?
5. Context Clues: Consider code patterns, variable names, function contexts

RESPONSE FORMAT:
Return valid JSON with this structure:
{
  "classification": "true_positive" or "false_positive",
  "matches": [
    {
      "benchmark_id": 1,
      "confidence": 0.85,
      "match_type": "exact|similar|related",
      "reasoning": "Detailed explanation of why this is a match"
    }
  ]
}

IMPORTANT:
- For true_positive classification, include at least one match with confidence >= 0.5
- For false_positive classification, return empty matches array
- Only classify as true_positive if you're confident there's a real match"""

        return prompt

    def _call_llm(self, prompt: str) -> str:
        """Make API call to LLM service"""
        self.stats['api_calls'] += 1

        if self.config.model_name.startswith('ollama:'):
            return self._call_ollama(prompt)
        elif 'openai' in self.config.base_url.lower():
            return self._call_openai_compatible(prompt)
        else:
            raise ValueError(f"Unsupported LLM configuration: {self.config.model_name}")

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API"""
        model_name = self.config.model_name.replace('ollama:', '')

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": 1000,  # Limit response length
            }
        }

        for attempt in range(self.config.max_retries):
            try:
                response = requests.post(
                    f"{self.config.base_url}/api/generate",
                    json=payload,
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                return response.json()['response']

            except requests.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise Exception(f"Ollama API failed after {self.config.max_retries} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

    def _call_openai_compatible(self, prompt: str) -> str:
        """Call OpenAI-compatible API"""
        payload = {
            "model": self.config.model_name,
            "messages": [
                {"role": "system", "content": "You are a cybersecurity expert analyzing vulnerability matches."},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config.temperature,
            "max_tokens": 1000
        }

        headers = {"Content-Type": "application/json"}

        for attempt in range(self.config.max_retries):
            try:
                response = requests.post(
                    f"{self.config.base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content']

            except requests.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise Exception(f"OpenAI-compatible API failed after {self.config.max_retries} attempts: {e}")
                time.sleep(2 ** attempt)

    def _parse_llm_response(self, response: str, benchmark_vuln, candidates: List, bench_index: int) -> List[LLMMatch]:
        """Parse LLM JSON response into LLMMatch objects"""
        try:
            # Extract JSON from response (LLM might include extra text)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in LLM response")

            data = json.loads(json_match.group())
            matches = []

            for match_data in data.get('matches', []):
                candidate_id = match_data['candidate_id'] - 1  # Convert to 0-based index
                if 0 <= candidate_id < len(candidates):
                    candidate = candidates[candidate_id]

                    # Generate unique IDs
                    benchmark_id = f"bench_{bench_index}_{hash(benchmark_vuln.file_path + str(benchmark_vuln.line_number)) & 0xFFFFFF:06x}"
                    sast_id = f"sast_{id(candidate)}_{hash(candidate.file_path + str(candidate.line_number)) & 0xFFFFFF:06x}"

                    match = LLMMatch(
                        benchmark_id=benchmark_id,
                        sast_id=sast_id,
                        confidence=float(match_data['confidence']),
                        reasoning=match_data['reasoning'],
                        match_type=match_data.get('match_type', 'similar')
                    )
                    matches.append(match)

            return matches

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"   ⚠️  Failed to parse LLM response: {e}")
            print(f"   📝 Raw response: {response[:200]}...")
            return []

    def _parse_sast_llm_response(self, response: str, sast_vuln, candidates: List, sast_index: int) -> List[LLMMatch]:
        """Parse LLM JSON response for SAST-first analysis into LLMMatch objects"""
        try:
            # Extract JSON from response (LLM might include extra text)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in LLM response")

            data = json.loads(json_match.group())
            matches = []

            classification = data.get('classification', 'false_positive')
            print(f"   🎯 LLM Classification: {classification}")

            if classification == 'true_positive':
                for match_data in data.get('matches', []):
                    benchmark_id = match_data['benchmark_id'] - 1  # Convert to 0-based index
                    if 0 <= benchmark_id < len(candidates):
                        candidate = candidates[benchmark_id]

                        # Generate unique IDs (reversed for SAST-first approach)
                        bench_id = f"bench_{id(candidate)}_{hash(candidate.file_path + str(candidate.line_number)) & 0xFFFFFF:06x}"
                        sast_id = f"sast_{sast_index}_{hash(sast_vuln.file_path + str(sast_vuln.line_number)) & 0xFFFFFF:06x}"

                        match = LLMMatch(
                            benchmark_id=bench_id,
                            sast_id=sast_id,
                            confidence=float(match_data['confidence']),
                            reasoning=match_data['reasoning'],
                            match_type=match_data.get('match_type', 'similar')
                        )
                        matches.append(match)
            else:
                print(f"   🚫 Classified as false positive")

            return matches

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"   ⚠️  Failed to parse LLM response: {e}")
            print(f"   📝 Raw response: {response[:200]}...")
            return []

    def _files_related(self, file1: str, file2: str) -> bool:
        """Check if two file paths are related"""
        path1 = Path(file1)
        path2 = Path(file2)

        # Same directory
        if path1.parent == path2.parent:
            return True

        # Related file extensions
        related_extensions = {
            '.php': ['.php', '.inc', '.phtml'],
            '.js': ['.js', '.jsx', '.ts', '.tsx'],
            '.java': ['.java', '.jsp'],
            '.py': ['.py', '.pyx'],
        }

        ext1, ext2 = path1.suffix, path2.suffix
        for group in related_extensions.values():
            if ext1 in group and ext2 in group:
                return True

        return False

    def _types_similar(self, type1: str, type2: str) -> bool:
        """Check if vulnerability types are similar"""
        # Normalize types
        t1 = type1.lower().replace('_', ' ').replace('-', ' ')
        t2 = type2.lower().replace('_', ' ').replace('-', ' ')

        # Direct match
        if t1 == t2:
            return True

        # Common vulnerability type mappings
        type_groups = [
            ['sql injection', 'sql inject', 'sqli', 'tainted sql'],
            ['cross site scripting', 'xss', 'reflected xss', 'stored xss'],
            ['command injection', 'command inject', 'code injection', 'os command'],
            ['path traversal', 'directory traversal', 'path injection'],
            ['csrf', 'cross site request forgery'],
            ['xxe', 'xml external entity'],
            ['ldap injection', 'ldap inject'],
            ['nosql injection', 'nosql inject']
        ]

        for group in type_groups:
            if any(term in t1 for term in group) and any(term in t2 for term in group):
                return True

        return False

    def _calculate_similarity(self, vuln1, vuln2) -> float:
        """Calculate overall similarity score between two vulnerabilities"""
        score = 0.0

        # File similarity (50% weight)
        if vuln1.file_path == vuln2.file_path:
            score += 0.5
        elif Path(vuln1.file_path).name == Path(vuln2.file_path).name:
            score += 0.3
        elif self._files_related(vuln1.file_path, vuln2.file_path):
            score += 0.2

        # Line proximity (30% weight)
        line_diff = abs(vuln1.line_number - vuln2.line_number)
        if line_diff == 0:
            score += 0.3
        elif line_diff <= 2:
            score += 0.25
        elif line_diff <= 5:
            score += 0.2
        elif line_diff <= 10:
            score += 0.1

        # Type similarity (20% weight)
        if self._types_similar(vuln1.vuln_type, vuln2.vuln_type):
            score += 0.2

        return score

    def print_stats(self):
        """Print analysis statistics"""
        print("\n📈 LLM Analysis Statistics:")
        print(f"   Total vulnerabilities analyzed: {self.stats['total_analyzed']}")
        print(f"   High confidence matches found: {self.stats['high_confidence_matches']}")
        print(f"   API calls made: {self.stats['api_calls']}")
        print(f"   Failed API calls: {self.stats['failed_calls']}")

        if self.stats['total_analyzed'] > 0:
            success_rate = (self.stats['high_confidence_matches'] / self.stats['total_analyzed']) * 100
            print(f"   Match success rate: {success_rate:.1f}%")

def create_ollama_config(model_name: str = "codellama", base_url: str = "http://localhost:11434") -> LLMConfig:
    """Create configuration for Ollama local LLM"""
    return LLMConfig(
        model_name=f"ollama:{model_name}",
        base_url=base_url,
        timeout=60,  # Longer timeout for local models
        temperature=0.1
    )

def create_openai_config(model_name: str = "gpt-3.5-turbo", base_url: str = "https://api.openai.com") -> LLMConfig:
    """Create configuration for OpenAI-compatible API"""
    return LLMConfig(
        model_name=model_name,
        base_url=base_url,
        timeout=30,
        temperature=0.1
    )

def test_llm_connection(config: LLMConfig) -> bool:
    """Test if LLM service is available and secure"""
    try:
        if config.model_name.startswith('ollama:'):
            # Test connection
            response = requests.get(f"{config.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                return False

            # Security check for Ollama
            if 'localhost' in config.base_url or '127.0.0.1' in config.base_url:
                return True
            else:
                print("⚠️  WARNING: LLM service not configured for localhost-only access")
                print("   Consider using: http://localhost:11434 or http://127.0.0.1:11434")
                return True  # Still allow, but warn

        else:
            # For other APIs, just check if endpoint is reachable
            response = requests.get(config.base_url, timeout=5)
            return response.status_code in [200, 404]  # 404 is OK for base URL
    except:
        return False

def verify_ollama_security() -> bool:
    """Verify Ollama is configured securely (localhost-only)"""
    try:
        import subprocess
        import platform

        if platform.system() == "Windows":
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True, timeout=5)
        else:
            result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True, timeout=5)

        lines = result.stdout.split('\n')

        for line in lines:
            if '11434' in line and ('0.0.0.0:11434' in line or '*:11434' in line):
                return False  # External binding detected

        return True  # No external bindings found

    except Exception:
        return None  # Cannot verify