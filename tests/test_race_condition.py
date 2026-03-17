"""
Test suite for detecting Race Condition vulnerabilities.
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations



class RaceConditionDetector:
    """Detects race condition vulnerabilities in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for race condition vulnerabilities."""
        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported language"], "max_score": 2}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for race conditions."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 0: TOCTOU (Time-of-Check-to-Time-of-Use) vulnerabilities
        # Check for permission check followed by file/resource operation
        has_toctou = False
        toctou_location = None

        # File access TOCTOU patterns
        file_check_then_use = any([
            # Check file exists/permissions, then open
            re.search(r'(os\.path\.exists|os\.access|pathlib.*\.exists)\([^)]+\).*\n.*open\(', code, re.DOTALL),
            re.search(r'if.*os\.path\.exists.*:\s*\n\s*(open|with open)', code, re.DOTALL),
            # Check permissions, then read
            re.search(r'if.*\.can_read.*:\s*\n\s*.*\.read\(', code, re.DOTALL),
            re.search(r'if.*permission.*:\s*\n\s*.*(open|read|write)', code, re.IGNORECASE | re.DOTALL),
        ])

        # Resource validation TOCTOU patterns
        resource_check_then_use = any([
            # Check coupon valid, then use
            re.search(r'if.*\.is_valid\(\).*:\s*\n\s*.*\.mark.*used', code, re.DOTALL),
            re.search(r'if.*valid.*:\s*\n\s*.*\.(save|update|mark)', code, re.DOTALL),
            # Check not expired, then use
            re.search(r'if.*not.*expired.*:\s*\n\s*', code, re.DOTALL),
        ])

        if file_check_then_use or resource_check_then_use:
            has_toctou = True
            # Find the check location
            check_patterns = [
                r'os\.path\.exists|os\.access',
                r'if.*permission',
                r'if.*\.is_valid\(\)',
                r'if.*valid',
                r'if.*not.*expired',
            ]
            for pattern in check_patterns:
                toctou_locations = find_pattern_locations(code, pattern)
                if toctou_locations:
                    toctou_location = toctou_locations[0]
                    break

        if has_toctou:
            # Check for TOCTOU mitigations
            has_atomic_file_ops = any([
                re.search(r'fcntl\.flock|fcntl\.lockf', code),  # File locking
                re.search(r'with.*open.*as.*:\s*\n\s*fcntl', code, re.DOTALL),
                re.search(r'O_CREAT.*O_EXCL', code),  # Atomic create
            ])

            has_database_transaction = any([
                re.search(r'select_for_update|FOR UPDATE', code, re.IGNORECASE),
                re.search(r'@transaction\.atomic|with transaction', code),
            ])

            if not has_atomic_file_ops and not has_database_transaction and toctou_location:
                line_num = toctou_location['line_number']
                code_snippet = toctou_location['line_content']

                self.vulnerabilities.append({
                    "type": "TOCTOU_RACE_CONDITION",
                    "severity": "HIGH",
                    "description": "TOCTOU (Time-of-Check-to-Time-of-Use) vulnerability - GAP BETWEEN CHECK AND USE: Code checks condition (file exists, permission granted, coupon valid) then acts on it, creating timing window. ATTACK: (1) Victim checks if file readable → (2) Attacker swaps file with symlink to /etc/passwd → (3) Victim opens file → reads sensitive data. OR: (1) Check coupon not used → (2) Attacker sends 1000 parallel requests in timing window → (3) All requests see 'not used' → All succeed = 1000 uses of 1-time coupon. REAL-WORLD: Race condition in Unix file permissions led to privilege escalation CVEs.",
                    "recommendation": "ATOMIC OPERATIONS REQUIRED: For files: Use os.open() with O_CREAT|O_EXCL (fails if exists), or fcntl.flock() for locking. For databases: Use SELECT FOR UPDATE within transaction, or atomic UPDATE with WHERE condition. For resources: Single atomic query: UPDATE coupons SET used=true WHERE id=? AND used=false (returns 0 if already used). NEVER separate check from action.",
                    "example_attack": "Coupon validation TOCTOU: (1) if coupon.is_valid() sees valid → (2) Attacker sends 100 requests simultaneously, all pass check → (3) All execute coupon.mark_used() → System processes 100 orders with 1-time coupon → $10,000 loss. FIX: Use UPDATE coupons SET used=true WHERE id=123 AND used=false, check affected_rows=1",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "TOCTOU vulnerability occurs when code checks a condition (Time-of-Check), then later uses/acts on that condition (Time-of-Use)",
                            "The gap between check and use creates a race condition window where state can change",
                            "For files: check if file exists/accessible, then open/read/write file",
                            "For resources: check if valid/available, then mark as used/consumed",
                            "For permissions: check if user has access, then perform privileged operation",
                            "Vulnerability exists if no atomic operations or locking prevent state changes between check and use"
                        ],
                        "why_vulnerable": [
                            "This code IS vulnerable to TOCTOU race condition",
                            f"Line {line_num}: Code performs check operation: {code_snippet}",
                            "File TOCTOU patterns detected: os.path.exists/os.access followed by open(), or if os.path.exists: then open/with open" if file_check_then_use else "",
                            "Resource TOCTOU patterns detected: if .is_valid() then .mark_used(), or if valid then save/update, or if not expired then use" if resource_check_then_use else "",
                            "No atomic file operations found: fcntl.flock, fcntl.lockf, O_CREAT|O_EXCL not present",
                            "No database transaction found: @transaction.atomic, with transaction, select_for_update not present",
                            "ATTACK: Between check and use, attacker can change state",
                            "ATTACK: File TOCTOU - (1) Code checks os.path.exists(file) → (2) Attacker replaces file with symlink → (3) Code opens file → reads unintended data",
                            "ATTACK: Resource TOCTOU - (1) Code checks if coupon.is_valid() → (2) Attacker sends 1000 parallel requests → (3) All see valid, all execute mark_used() → 1000x usage",
                            "ATTACK: Permission TOCTOU - (1) Check user.can_read(file) → (2) Permissions change → (3) Read file with old assumption",
                            "IMPACT: File TOCTOU → arbitrary file read/write, privilege escalation, information disclosure",
                            "IMPACT: Resource TOCTOU → double-spending, coupon fraud, inventory overselling, financial loss",
                            "IMPACT: Permission TOCTOU → unauthorized access, privilege escalation"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Checked for file TOCTOU: os.path.exists + open(), os.access + open(), pathlib.*.exists() + open()",
                            "Checked for file TOCTOU: if os.path.exists: then open/with open",
                            "Checked for permission TOCTOU: if .can_read then .read(), if permission then open/read/write",
                            "Checked for resource TOCTOU: if .is_valid() then .mark_used(), if valid then save/update/mark",
                            "Checked for resource TOCTOU: if not expired then use, if not used then use",
                            "Checked for atomic file operation mitigations: fcntl.flock, fcntl.lockf, O_CREAT|O_EXCL",
                            "Checked for database transaction mitigations: @transaction.atomic, with transaction, select_for_update, FOR UPDATE",
                            "All check-then-use patterns examined for timing gaps"
                        ],
                        "evidence": {
                            "found_patterns": [
                                f"TOCTOU pattern detected at line {line_num}",
                                f"File check-then-use: {file_check_then_use}",
                                f"Resource check-then-use: {resource_check_then_use}",
                                "No atomic operations found",
                                "No database transactions found"
                            ],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 1: Shared state modifications (account balances, counters, etc.)
        shared_state_patterns = [
            r'(account|balance|total|counter|quantity|inventory)\s*[+\-*/]=',
            r'(account|balance|total|counter|quantity|inventory)\s*=\s*\w+\s*[+\-]',
            r'\[.*\]\s*\+=',  # dict[key] += value
            r'\.update\(.*balance',
            r'\.save\(\)',  # Database saves
        ]

        # Find pattern locations
        shared_state_locations = []
        for pattern in shared_state_patterns:
            locations = find_pattern_locations(code, pattern)
            shared_state_locations.extend(locations)

        # Pattern 2: Read-modify-write operations
        read_modify_write_patterns = [
            r'=\s*\w+\[.*\]\s*[+\-]',  # dict[key] + value
            r'=\s*get\(.*\)\s*[+\-]',  # get() + value
        ]

        read_modify_write_locations = []
        for pattern in read_modify_write_patterns:
            read_modify_write_locations.extend(find_pattern_locations(code, pattern))

        all_locations = shared_state_locations + read_modify_write_locations
        modifies_shared_state = len(all_locations) > 0

        if modifies_shared_state:
            # Check for concurrency protections
            has_locking = any([
                re.search(r'threading\.Lock|RLock|Semaphore', code),
                re.search(r'with\s+lock:|lock\.acquire\(', code),
                re.search(r'@synchronized|@lock', code),
                re.search(r'asyncio\.Lock', code),
            ])

            has_transaction = any([
                re.search(r'with\s+transaction|@transaction|BEGIN TRANSACTION', code, re.IGNORECASE),
                re.search(r'db\.session\.begin|session\.begin', code),
                re.search(r'atomic\(', code),
                re.search(r'SERIALIZABLE|REPEATABLE READ', code),  # Transaction isolation
            ])

            has_atomic_operation = any([
                re.search(r'\.atomic|AtomicInteger|AtomicLong', code),
                re.search(r'UPDATE.*SET.*WHERE', code),  # Atomic SQL UPDATE
                re.search(r'\.increment\(|\.decrement\(', code),  # Atomic operations
            ])

            has_queue = any([
                re.search(r'Queue\(|queue\.Queue', code),
                re.search(r'celery|rq\.', code),  # Task queues
            ])

            # Use first location for reporting
            location = all_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            if not has_locking and not has_transaction and not has_atomic_operation and not has_queue:
                self.vulnerabilities.append({
                    "type": "RACE_CONDITION",
                    "severity": "HIGH",
                    "description": "Modifies shared state without locking/transactions - RACE CONDITION RISK: When multiple requests execute simultaneously, they read the SAME initial value, then both modify and save, causing data corruption. REAL-WORLD IMPACT: (1) Banking: Two withdrawals of $100 from $150 balance both see $150, both succeed, balance becomes $50 instead of -$50 = money lost. (2) Inventory: Two purchases of last item both see quantity=1, both succeed = overselling. (3) Double-spending: attacker sends simultaneous requests to exploit timing window",
                    "recommendation": "Use database transactions with SELECT FOR UPDATE, or atomic operations like UPDATE SET balance = balance - amount WHERE id = ?",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Race condition vulnerability occurs when shared mutable state is modified without proper synchronization",
                            "Read-modify-write operations are vulnerable: read value → modify value → write value back",
                            "Multiple concurrent operations can read the same initial value, causing lost updates",
                            "Vulnerability exists if no locking, transactions, atomic operations, or queues protect the shared state",
                            "Common vulnerable patterns: account.balance += amount, counter += 1, inventory -= quantity"
                        ],
                        "why_vulnerable": [
                            "This code IS vulnerable to race condition",
                            f"Line {line_num}: Code modifies shared state: {code_snippet}",
                            f"Shared state modification patterns found: {len(shared_state_locations)} instances",
                            f"Read-modify-write patterns found: {len(read_modify_write_locations)} instances",
                            "No thread locking found: threading.Lock, RLock, Semaphore, asyncio.Lock not present",
                            "No database transactions found: @transaction.atomic, with transaction, BEGIN TRANSACTION not present",
                            "No atomic operations found: .atomic, AtomicInteger, UPDATE...SET...WHERE, .increment()/.decrement() not present",
                            "No task queues found: Queue(), celery, rq not present",
                            "ATTACK: Read-Modify-Write race - (1) Request A reads balance=$150 → (2) Request B reads balance=$150 → (3) Request A writes balance=$50 (150-100) → (4) Request B writes balance=$50 (150-100) → Final: $50 instead of -$50",
                            "ATTACK: Double-spending - User sends 2 simultaneous withdrawal requests for $100 each from $150 balance → Both see $150 → Both succeed → Lost $100",
                            "ATTACK: Inventory overselling - 2 users buy last item simultaneously → Both see quantity=1 → Both succeed → Oversold by 1",
                            "ATTACK: Counter corruption - Multiple requests increment counter simultaneously → Some increments lost → Inaccurate analytics",
                            "IMPACT: Financial loss - banking withdrawals, payment processing, wallet systems",
                            "IMPACT: Inventory errors - overselling products, double-booking resources",
                            "IMPACT: Data corruption - lost updates, inconsistent state, inaccurate counters"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Checked for shared state patterns: account/balance/total/counter/quantity/inventory with +=, -=, *=, /=",
                            "Checked for shared state patterns: account/balance/total/counter/quantity/inventory = value +/- other",
                            "Checked for shared state patterns: dict[key] += value",
                            "Checked for shared state patterns: .update(...balance), .save()",
                            "Checked for read-modify-write patterns: = dict[key] +/- value, = get() +/- value",
                            "Checked for locking mitigations: threading.Lock, RLock, Semaphore, with lock, lock.acquire(), @synchronized, asyncio.Lock",
                            "Checked for transaction mitigations: with transaction, @transaction, BEGIN TRANSACTION, db.session.begin, atomic(), SERIALIZABLE, REPEATABLE READ",
                            "Checked for atomic operation mitigations: .atomic, AtomicInteger, AtomicLong, UPDATE...SET...WHERE, .increment(), .decrement()",
                            "Checked for queue mitigations: Queue(), queue.Queue, celery, rq"
                        ],
                        "evidence": {
                            "found_patterns": [
                                f"Shared state modifications at {len(shared_state_locations)} locations",
                                f"Read-modify-write operations at {len(read_modify_write_locations)} locations",
                                "No synchronization mechanisms found"
                            ],
                            "line_numbers": [loc['line_number'] for loc in all_locations[:5]],  # First 5 locations
                            "code_snippets": [loc['line_content'] for loc in all_locations[:5]]
                        }
                    }
                })
                self.score = 0
            elif has_locking or has_queue:
                # Partial protection (locking may not be sufficient)
                self.vulnerabilities.append({
                    "type": "RACE_CONDITION",
                    "severity": "LOW",
                    "description": "Uses locking but verify it's sufficient for all concurrent access patterns",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Code uses partial protection mechanisms (locking or queues) but may not be sufficient",
                            "Thread locks protect in-memory state but not cross-process or distributed scenarios",
                            "Queues serialize operations but may have race conditions in queue management itself",
                            "Need to verify lock covers all access paths and no lock-free paths exist"
                        ],
                        "why_vulnerable": [
                            "This code uses PARTIAL protection (locking or queues)",
                            f"Line {line_num}: Code modifies shared state: {code_snippet}",
                            "Locking detected: threading.Lock, RLock, Semaphore, with lock, or asyncio.Lock found" if has_locking else "",
                            "Queue detected: Queue(), queue.Queue, celery, or rq found" if has_queue else "",
                            "WARNING: Thread locks only protect single-process scenarios, not distributed systems",
                            "WARNING: Verify lock is held for entire read-modify-write sequence",
                            "WARNING: Check for lock-free code paths that bypass protection",
                            "WARNING: Queues can have race conditions in enqueue/dequeue operations",
                            "RECOMMENDATION: Use database transactions for data persistence, not just in-memory locks"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Checked for shared state patterns: account/balance/total/counter/quantity/inventory modifications",
                            "Checked for locking: threading.Lock, RLock, Semaphore, with lock, asyncio.Lock - FOUND",
                            "Checked for queues: Queue(), celery, rq - FOUND" if has_queue else "Checked for queues: Queue(), celery, rq - NOT FOUND",
                            "Checked for transactions: @transaction, with transaction - NOT FOUND",
                            "Checked for atomic operations: UPDATE...SET...WHERE, .increment() - NOT FOUND"
                        ],
                        "evidence": {
                            "found_patterns": [
                                "Locking mechanism present but may be insufficient",
                                f"Shared state modifications at {len(all_locations)} locations"
                            ],
                            "line_numbers": [loc['line_number'] for loc in all_locations[:3]],
                            "code_snippets": [loc['line_content'] for loc in all_locations[:3]]
                        }
                    }
                })
                self.score = 1
            else:
                # Has proper protection
                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Uses transactions or atomic operations for concurrency safety",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Code is secure when using proper synchronization: database transactions or atomic operations",
                            "Database transactions with SELECT FOR UPDATE provide pessimistic locking",
                            "Atomic operations like UPDATE...SET x=x+1 WHERE... perform read-modify-write atomically",
                            "Transaction isolation levels (SERIALIZABLE, REPEATABLE READ) prevent anomalies"
                        ],
                        "why_vulnerable": [],
                        "why_not_vulnerable": [
                            "This code is NOT vulnerable - uses proper synchronization",
                            f"Line {line_num}: Code modifies shared state: {code_snippet}",
                            "Database transactions detected: @transaction.atomic, with transaction, BEGIN TRANSACTION, or db.session.begin present" if has_transaction else "",
                            "Atomic operations detected: .atomic, AtomicInteger, UPDATE...SET...WHERE, .increment()/.decrement() present" if has_atomic_operation else "",
                            "Transaction isolation detected: SERIALIZABLE or REPEATABLE READ" if has_transaction else "",
                            "SECURE: Database transactions ensure all-or-nothing execution with proper isolation",
                            "SECURE: SELECT FOR UPDATE locks rows during transaction, preventing concurrent modifications",
                            "SECURE: Atomic operations perform read-modify-write in single database operation",
                            "SECURE: No timing window between read and write for race conditions to occur"
                        ],
                        "patterns_checked": [
                            "Checked for shared state patterns: account/balance/total/counter/quantity/inventory modifications",
                            "Checked for transactions: @transaction.atomic, with transaction, BEGIN TRANSACTION, db.session.begin, atomic(), SERIALIZABLE, REPEATABLE READ - FOUND",
                            "Checked for atomic operations: .atomic, AtomicInteger, UPDATE...SET...WHERE, .increment(), .decrement() - FOUND"
                        ],
                        "evidence": {
                            "found_patterns": [
                                "Proper synchronization mechanisms present",
                                "Transactions or atomic operations protect shared state"
                            ],
                            "line_numbers": [loc['line_number'] for loc in all_locations[:3]],
                            "code_snippets": [loc['line_content'] for loc in all_locations[:3]]
                        }
                    }
                })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code for race conditions."""
        self.vulnerabilities = []
        self.score = 2

        # Pattern 0: TOCTOU (Time-of-Check-to-Time-of-Use) vulnerabilities
        has_toctou = False
        toctou_location = None

        # File/resource check then use patterns
        file_check_then_use = any([
            re.search(r'fs\.existsSync.*\n.*fs\.(open|read|write)', code, re.DOTALL),
            re.search(r'if.*fs\.exists.*\{.*fs\.(open|read)', code, re.DOTALL),
            re.search(r'if.*\.exists\(\).*\{.*\.(read|write|delete)', code, re.DOTALL),
        ])

        # Resource validation TOCTOU patterns
        resource_check_then_use = any([
            re.search(r'if.*\.isValid\(\).*\{.*\.(save|update|markUsed)', code, re.DOTALL),
            re.search(r'if.*valid.*\{.*await.*\.(save|update)', code, re.DOTALL),
            re.search(r'if.*!.*expired.*\{', code, re.DOTALL),
            re.search(r'if.*!.*used.*\{.*\.used\s*=\s*true', code, re.DOTALL),
        ])

        if file_check_then_use or resource_check_then_use:
            has_toctou = True
            # Find the check location
            check_patterns = [
                r'fs\.existsSync|fs\.exists',
                r'if.*\.exists\(\)',
                r'if.*\.isValid\(\)',
                r'if.*valid',
                r'if.*!.*expired',
                r'if.*!.*used',
            ]
            for pattern in check_patterns:
                toctou_locations = find_pattern_locations(code, pattern)
                if toctou_locations:
                    toctou_location = toctou_locations[0]
                    break

        if has_toctou:
            # Check for TOCTOU mitigations
            has_atomic_ops = any([
                re.search(r'findOneAndUpdate|updateOne', code),  # Atomic database ops
                re.search(r'\$inc|\$dec', code),  # MongoDB atomic
                re.search(r'fs\.open.*O_CREAT.*O_EXCL', code),  # Atomic file create
            ])

            has_transaction = any([
                re.search(r'session\.startTransaction|withTransaction', code),
                re.search(r'BEGIN\s*(TRANSACTION)?', code, re.IGNORECASE),  # SQL BEGIN
                re.search(r'COMMIT|ROLLBACK', code, re.IGNORECASE),  # SQL COMMIT/ROLLBACK
                re.search(r'\.transaction\(', code),
            ])

            # race_003 fix: SQL pessimistic locking
            has_pessimistic_locking = any([
                re.search(r'FOR UPDATE', code, re.IGNORECASE),
                re.search(r'FOR NO KEY UPDATE', code, re.IGNORECASE),
                re.search(r'FOR SHARE|FOR KEY SHARE', code, re.IGNORECASE),
                re.search(r'select_for_update', code),  # Django/SQLAlchemy
            ])

            if not has_atomic_ops and not has_transaction and not has_pessimistic_locking and toctou_location:
                line_num = toctou_location['line_number']
                code_snippet = toctou_location['line_content']

                self.vulnerabilities.append({
                    "type": "TOCTOU_RACE_CONDITION",
                    "severity": "HIGH",
                    "description": "TOCTOU (Time-of-Check-to-Time-of-Use) vulnerability - GAP BETWEEN CHECK AND USE: Code checks condition (file exists, permission granted, coupon valid) then acts on it, creating timing window. ATTACK: (1) Check coupon not used → (2) Attacker sends 1000 parallel requests in timing window → (3) All requests see 'not used' → All succeed = 1000 uses of 1-time coupon. REAL-WORLD: E-commerce sites lose thousands from coupon race conditions.",
                    "recommendation": "ATOMIC OPERATIONS REQUIRED: For MongoDB: Use findOneAndUpdate with filter conditions, or updateOne with {used: false} check. For resources: Single atomic query like Coupon.updateOne({_id: id, used: false}, {$set: {used: true}}) - returns matchedCount=0 if already used. For files: Use fs.open() with O_CREAT|O_EXCL flags. NEVER separate check from action.",
                    "example_attack": "Coupon TOCTOU: const coupon = await Coupon.findById(id); if (!coupon.used) { coupon.used = true; await coupon.save(); } ← Attacker sends 100 simultaneous requests, all pass check, all mark used, system processes 100 orders. FIX: const result = await Coupon.updateOne({_id: id, used: false}, {used: true}); if (result.matchedCount === 0) throw 'Already used'",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "TOCTOU vulnerability occurs when code checks a condition (Time-of-Check), then later uses/acts on that condition (Time-of-Use)",
                            "The gap between check and use creates a race condition window where state can change",
                            "For files: check if file exists/accessible with fs.existsSync/fs.exists, then open/read/write file",
                            "For resources: check if valid/available with .isValid()/.exists(), then mark as used/consumed with .save()/.update()/.markUsed()",
                            "For permissions: check if !used/!expired, then perform operation",
                            "Vulnerability exists if no atomic operations, transactions, or pessimistic locking (FOR UPDATE) prevent state changes between check and use"
                        ],
                        "why_vulnerable": [
                            "This code IS vulnerable to TOCTOU race condition",
                            f"Line {line_num}: Code performs check operation: {code_snippet}",
                            "File TOCTOU patterns detected: fs.existsSync/fs.exists followed by fs.open/read/write, or if fs.exists then fs.open/read" if file_check_then_use else "",
                            "Resource TOCTOU patterns detected: if .isValid() then .save()/.update()/.markUsed(), or if valid then save/update, or if !expired/!used then use" if resource_check_then_use else "",
                            "No atomic operations found: findOneAndUpdate, updateOne, $inc, $dec, fs.open with O_CREAT|O_EXCL not present",
                            "No database transaction found: session.startTransaction, withTransaction, BEGIN TRANSACTION, COMMIT, ROLLBACK, .transaction() not present",
                            "No pessimistic locking found: FOR UPDATE, FOR NO KEY UPDATE, FOR SHARE, select_for_update not present",
                            "ATTACK: Between check and use, attacker can change state",
                            "ATTACK: File TOCTOU - (1) Code checks fs.existsSync(file) → (2) Attacker replaces file or changes permissions → (3) Code opens file → reads/writes unintended data",
                            "ATTACK: Coupon TOCTOU - (1) Code checks if !coupon.used → (2) Attacker sends 1000 parallel requests → (3) All see !used → All execute coupon.used=true; save() → 1000x usage",
                            "ATTACK: Resource TOCTOU - (1) Code checks if item.quantity > 0 → (2) Multiple requests pass check → (3) All decrement quantity → Overselling",
                            "IMPACT: File TOCTOU → arbitrary file read/write, privilege escalation, information disclosure",
                            "IMPACT: Resource TOCTOU → double-spending, coupon fraud, inventory overselling, financial loss (e-commerce sites lose thousands)",
                            "IMPACT: Permission TOCTOU → unauthorized access, privilege escalation"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Checked for file TOCTOU: fs.existsSync + fs.open/read/write, fs.exists + fs.open/read, if fs.exists then open/read",
                            "Checked for file TOCTOU: if .exists() then .read()/.write()/.delete()",
                            "Checked for resource TOCTOU: if .isValid() then .save()/.update()/.markUsed(), if valid then save/update",
                            "Checked for resource TOCTOU: if !expired then use, if !used then used=true",
                            "Checked for atomic operation mitigations: findOneAndUpdate, updateOne, $inc/$dec (MongoDB), fs.open with O_CREAT|O_EXCL",
                            "Checked for transaction mitigations: session.startTransaction, withTransaction, BEGIN TRANSACTION, COMMIT, ROLLBACK, .transaction()",
                            "Checked for pessimistic locking mitigations: FOR UPDATE, FOR NO KEY UPDATE, FOR SHARE, FOR KEY SHARE, select_for_update",
                            "All check-then-use patterns examined for timing gaps"
                        ],
                        "evidence": {
                            "found_patterns": [
                                f"TOCTOU pattern detected at line {line_num}",
                                f"File check-then-use: {file_check_then_use}",
                                f"Resource check-then-use: {resource_check_then_use}",
                                "No atomic operations found",
                                "No database transactions found",
                                "No pessimistic locking found"
                            ],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 1: Shared state modifications
        shared_state_patterns = [
            r'(account|balance|total|counter|quantity|inventory)\s*[+\-*/]=',
            r'(account|balance|total|counter|quantity|inventory)\s*=\s*\w+\s*[+\-]',
            r'\.save\(\)',
            r'\.update\(',
        ]

        # Find pattern locations
        shared_state_locations = []
        for pattern in shared_state_patterns:
            locations = find_pattern_locations(code, pattern)
            shared_state_locations.extend(locations)

        # Pattern 2: Read-modify-write operations
        read_modify_write_patterns = [
            r'=\s*await\s+\w+\.find\w*\(.*\)\s*[+\-]',
            r'=\s*\w+\.\w+\s*[+\-]',
        ]

        read_modify_write_locations = []
        for pattern in read_modify_write_patterns:
            read_modify_write_locations.extend(find_pattern_locations(code, pattern))

        all_locations = shared_state_locations + read_modify_write_locations
        modifies_shared_state = len(all_locations) > 0

        if modifies_shared_state:
            # Check for concurrency protections
            has_locking = any([
                re.search(r'mutex|lock|semaphore', code, re.IGNORECASE),
                re.search(r'async-mutex|async-lock', code),
            ])

            has_transaction = any([
                re.search(r'session\.startTransaction|withTransaction', code),
                re.search(r'BEGIN.*TRANSACTION|COMMIT|ROLLBACK', code, re.IGNORECASE),
                re.search(r'\.transaction\(', code),
            ])

            has_atomic_operation = any([
                re.search(r'\$inc|\$dec|findOneAndUpdate', code),  # MongoDB atomic ops
                re.search(r'UPDATE.*SET.*WHERE', code),
            ])

            has_queue = any([
                re.search(r'bull|bee-queue|kue', code),
                re.search(r'Queue\(', code),
            ])

            # Use first location for reporting
            location = all_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            if not has_locking and not has_transaction and not has_atomic_operation and not has_queue:
                self.vulnerabilities.append({
                    "type": "RACE_CONDITION",
                    "severity": "HIGH",
                    "description": "Modifies shared state without locking/transactions - RACE CONDITION RISK: When multiple requests execute simultaneously, they read the SAME initial value, then both modify and save, causing data corruption. REAL-WORLD IMPACT: (1) Banking: Two withdrawals of $100 from $150 balance both see $150, both succeed, balance becomes $50 instead of -$50 = money lost. (2) Inventory: Two purchases of last item both see quantity=1, both succeed = overselling. (3) Double-spending: attacker sends simultaneous requests to exploit timing window",
                    "recommendation": "Use database transactions with SELECT FOR UPDATE, or atomic operations like UPDATE SET balance = balance - amount WHERE id = ?",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Race condition vulnerability occurs when shared mutable state is modified without proper synchronization",
                            "Read-modify-write operations are vulnerable: read value → modify value → write value back",
                            "Multiple concurrent operations can read the same initial value, causing lost updates",
                            "Vulnerability exists if no locking, transactions, atomic operations, or queues protect the shared state",
                            "Common vulnerable patterns: account.balance += amount, counter += 1, inventory -= quantity, await .save()"
                        ],
                        "why_vulnerable": [
                            "This code IS vulnerable to race condition",
                            f"Line {line_num}: Code modifies shared state: {code_snippet}",
                            f"Shared state modification patterns found: {len(shared_state_locations)} instances",
                            f"Read-modify-write patterns found: {len(read_modify_write_locations)} instances",
                            "No locking found: mutex, lock, semaphore, async-mutex, async-lock not present",
                            "No database transactions found: session.startTransaction, withTransaction, BEGIN TRANSACTION, COMMIT, ROLLBACK, .transaction() not present",
                            "No atomic operations found: $inc, $dec, findOneAndUpdate, UPDATE...SET...WHERE not present",
                            "No task queues found: bull, bee-queue, kue, Queue() not present",
                            "ATTACK: Read-Modify-Write race - (1) Request A reads balance=$150 → (2) Request B reads balance=$150 → (3) Request A writes balance=$50 (150-100) → (4) Request B writes balance=$50 (150-100) → Final: $50 instead of -$50",
                            "ATTACK: Double-spending - User sends 2 simultaneous withdrawal requests for $100 each from $150 balance → Both see $150 → Both succeed → Lost $100",
                            "ATTACK: Inventory overselling - 2 users buy last item simultaneously → Both see quantity=1 → Both succeed → Oversold by 1",
                            "ATTACK: Counter corruption - Multiple requests increment counter simultaneously → Some increments lost → Inaccurate analytics",
                            "IMPACT: Financial loss - banking withdrawals, payment processing, wallet systems",
                            "IMPACT: Inventory errors - overselling products, double-booking resources",
                            "IMPACT: Data corruption - lost updates, inconsistent state, inaccurate counters"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Checked for shared state patterns: account/balance/total/counter/quantity/inventory with +=, -=, *=, /=",
                            "Checked for shared state patterns: account/balance/total/counter/quantity/inventory = value +/- other",
                            "Checked for shared state patterns: .save(), .update()",
                            "Checked for read-modify-write patterns: = await find*() +/- value, = property +/- value",
                            "Checked for locking mitigations: mutex, lock, semaphore, async-mutex, async-lock",
                            "Checked for transaction mitigations: session.startTransaction, withTransaction, BEGIN TRANSACTION, COMMIT, ROLLBACK, .transaction()",
                            "Checked for atomic operation mitigations: $inc, $dec, findOneAndUpdate (MongoDB), UPDATE...SET...WHERE (SQL)",
                            "Checked for queue mitigations: bull, bee-queue, kue, Queue()"
                        ],
                        "evidence": {
                            "found_patterns": [
                                f"Shared state modifications at {len(shared_state_locations)} locations",
                                f"Read-modify-write operations at {len(read_modify_write_locations)} locations",
                                "No synchronization mechanisms found"
                            ],
                            "line_numbers": [loc['line_number'] for loc in all_locations[:5]],  # First 5 locations
                            "code_snippets": [loc['line_content'] for loc in all_locations[:5]]
                        }
                    }
                })
                self.score = 0
            elif has_locking or has_queue:
                # Partial protection
                self.vulnerabilities.append({
                    "type": "RACE_CONDITION",
                    "severity": "LOW",
                    "description": "Uses locking but verify it's sufficient for all concurrent access patterns",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Code uses partial protection mechanisms (locking or queues) but may not be sufficient",
                            "In-memory locks protect single-process scenarios but not distributed systems",
                            "Queues serialize operations but may have race conditions in queue management itself",
                            "Need to verify lock covers all access paths and no lock-free paths exist"
                        ],
                        "why_vulnerable": [
                            "This code uses PARTIAL protection (locking or queues)",
                            f"Line {line_num}: Code modifies shared state: {code_snippet}",
                            "Locking detected: mutex, lock, semaphore, async-mutex, or async-lock found" if has_locking else "",
                            "Queue detected: bull, bee-queue, kue, or Queue() found" if has_queue else "",
                            "WARNING: In-memory locks only protect single Node.js process, not multi-process/distributed systems",
                            "WARNING: Verify lock is held for entire read-modify-write sequence",
                            "WARNING: Check for lock-free code paths that bypass protection",
                            "WARNING: Queues can have race conditions in enqueue/dequeue operations",
                            "RECOMMENDATION: Use database transactions or atomic operations for data persistence"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Checked for shared state patterns: account/balance/total/counter/quantity/inventory modifications",
                            "Checked for locking: mutex, lock, semaphore, async-mutex, async-lock - FOUND",
                            "Checked for queues: bull, bee-queue, kue, Queue() - FOUND" if has_queue else "Checked for queues: bull, bee-queue, kue, Queue() - NOT FOUND",
                            "Checked for transactions: session.startTransaction, withTransaction, .transaction() - NOT FOUND",
                            "Checked for atomic operations: $inc, $dec, findOneAndUpdate, UPDATE...SET...WHERE - NOT FOUND"
                        ],
                        "evidence": {
                            "found_patterns": [
                                "Locking mechanism present but may be insufficient",
                                f"Shared state modifications at {len(all_locations)} locations"
                            ],
                            "line_numbers": [loc['line_number'] for loc in all_locations[:3]],
                            "code_snippets": [loc['line_content'] for loc in all_locations[:3]]
                        }
                    }
                })
                self.score = 1
            else:
                # Has proper protection
                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Uses transactions or atomic operations for concurrency safety",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Code is secure when using proper synchronization: database transactions or atomic operations",
                            "Database transactions with BEGIN/COMMIT provide ACID guarantees",
                            "Atomic operations like $inc/$dec (MongoDB) or UPDATE...SET x=x+1 (SQL) perform read-modify-write atomically",
                            "MongoDB findOneAndUpdate performs check-and-update in single operation"
                        ],
                        "why_vulnerable": [],
                        "why_not_vulnerable": [
                            "This code is NOT vulnerable - uses proper synchronization",
                            f"Line {line_num}: Code modifies shared state: {code_snippet}",
                            "Database transactions detected: session.startTransaction, withTransaction, BEGIN TRANSACTION, COMMIT, ROLLBACK, or .transaction() present" if has_transaction else "",
                            "Atomic operations detected: $inc, $dec, findOneAndUpdate (MongoDB), or UPDATE...SET...WHERE (SQL) present" if has_atomic_operation else "",
                            "SECURE: Database transactions ensure all-or-nothing execution with proper isolation",
                            "SECURE: MongoDB atomic operators ($inc, $dec) perform read-modify-write in single operation",
                            "SECURE: findOneAndUpdate checks condition and updates atomically, no race window",
                            "SECURE: SQL UPDATE...SET x=x+1 WHERE... performs read-modify-write atomically in database",
                            "SECURE: No timing window between read and write for race conditions to occur"
                        ],
                        "patterns_checked": [
                            "Checked for shared state patterns: account/balance/total/counter/quantity/inventory modifications",
                            "Checked for transactions: session.startTransaction, withTransaction, BEGIN TRANSACTION, COMMIT, ROLLBACK, .transaction() - FOUND",
                            "Checked for atomic operations: $inc, $dec, findOneAndUpdate (MongoDB), UPDATE...SET...WHERE (SQL) - FOUND"
                        ],
                        "evidence": {
                            "found_patterns": [
                                "Proper synchronization mechanisms present",
                                "Transactions or atomic operations protect shared state"
                            ],
                            "line_numbers": [loc['line_number'] for loc in all_locations[:3]],
                            "code_snippets": [loc['line_content'] for loc in all_locations[:3]]
                        }
                    }
                })

        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


def test_race_python_vulnerable():
    """Test detection of race condition in Python."""
    vulnerable_code = '''
def process_transaction(account_id, amount):
    account = get_account(account_id)
    current_balance = account.balance

    if current_balance >= amount:
        account.balance = current_balance - amount
        account.save()
        return True

    return False
'''
    detector = RaceConditionDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect race condition"


def test_race_python_secure_transaction():
    """Test detection of secure code using transactions."""
    secure_code = '''
from django.db import transaction

@transaction.atomic
def process_transaction(account_id, amount):
    account = Account.objects.select_for_update().get(id=account_id)
    current_balance = account.balance

    if current_balance >= amount:
        account.balance = current_balance - amount
        account.save()
        return True

    return False
'''
    detector = RaceConditionDetector()
    result = detector.analyze(secure_code, "python")
    assert result["score"] == 2, "Should recognize transaction protection"


def test_race_python_secure_lock():
    """Test detection of code using locks."""
    secure_code = '''
import threading

lock = threading.Lock()

def process_transaction(account_id, amount):
    with lock:
        account = get_account(account_id)
        current_balance = account.balance

        if current_balance >= amount:
            account.balance = current_balance - amount
            account.save()
            return True

    return False
'''
    detector = RaceConditionDetector()
    result = detector.analyze(secure_code, "python")
    assert result["score"] == 1, "Should recognize lock usage (partial protection)"


def test_race_javascript_vulnerable():
    """Test detection of race condition in JavaScript."""
    vulnerable_code = '''
async function processTransaction(accountId, amount) {
    const account = await Account.findById(accountId);
    const currentBalance = account.balance;

    if (currentBalance >= amount) {
        account.balance = currentBalance - amount;
        await account.save();
        return true;
    }

    return false;
}
'''
    detector = RaceConditionDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] == 0, "Should detect race condition"


def test_race_javascript_secure():
    """Test detection of secure code using transactions."""
    secure_code = '''
async function processTransaction(accountId, amount) {
    const session = await mongoose.startSession();
    session.startTransaction();

    try {
        const account = await Account.findById(accountId).session(session);
        const currentBalance = account.balance;

        if (currentBalance >= amount) {
            account.balance = currentBalance - amount;
            await account.save();
            await session.commitTransaction();
            return true;
        }

        await session.abortTransaction();
        return false;
    } finally {
        session.endSession();
    }
}
'''
    detector = RaceConditionDetector()
    result = detector.analyze(secure_code, "javascript")
    assert result["score"] == 2, "Should recognize transaction protection"


if __name__ == "__main__":
    test_race_python_vulnerable()
    test_race_python_secure_transaction()
    test_race_python_secure_lock()
    test_race_javascript_vulnerable()
    test_race_javascript_secure()
    print("✅ All Race Condition detection tests passed!")
