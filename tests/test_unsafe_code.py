"""
Test suite for detecting Unsafe Code in Rust.
"""
import re
from typing import Dict


class UnsafeCodeDetector:
    """Detects unsafe code blocks in Rust."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "rust") -> Dict:
        """Analyze code for unsafe code blocks."""
        if language != "rust":
            return {"score": 2, "vulnerabilities": [], "max_score": 2}

        return self._analyze_rust(code)

    def _analyze_rust(self, code: str) -> Dict:
        """Analyze Rust code for unsafe blocks."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 1: Unsafe blocks (WARNING)
        has_unsafe = re.search(r'unsafe\s*\{', code)

        if has_unsafe:
            # Check what's inside unsafe blocks
            has_raw_ptr = re.search(r'\*const|\*mut', code)
            has_ffi = re.search(r'extern\s+"C"', code)
            has_transmute = re.search(r'std::mem::transmute', code)
            has_deref = re.search(r'unsafe\s*\{[^}]*\*', code)

            issues = []
            if has_raw_ptr:
                issues.append("raw pointers")
            if has_ffi:
                issues.append("FFI calls")
            if has_transmute:
                issues.append("transmute")
            if has_deref:
                issues.append("raw pointer dereference")

            if issues:
                self.vulnerabilities.append({
                    "type": "UNSAFE_CODE",
                    "severity": "MEDIUM",
                    "description": f"Unsafe block with: {', '.join(issues)}"
                })
                self.score = 1
            else:
                self.vulnerabilities.append({
                    "type": "UNSAFE_CODE",
                    "severity": "LOW",
                    "description": "Unsafe block present but operations unclear"
                })
                self.score = 1

        # Pattern 2: Safe Rust (SECURE)
        else:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No unsafe blocks - memory safe by default"
            })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


if __name__ == "__main__":
    # Test unsafe code detection
    detector = UnsafeCodeDetector()

    unsafe_code = '''
    unsafe {
        let ptr: *mut u8 = std::ptr::null_mut();
        *ptr = 42;
    }
    '''
    result = detector.analyze(unsafe_code, "rust")
    assert result["score"] == 1, "Should detect unsafe code"

    safe_code = '''
    fn process(data: Vec<u8>) {
        for byte in data {
            println!("{}", byte);
        }
    }
    '''
    result = detector.analyze(safe_code, "rust")
    assert result["score"] == 2, "Should recognize safe code"

    print("All Unsafe Code detection tests passed!")
