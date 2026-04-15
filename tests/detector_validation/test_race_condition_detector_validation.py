#!/usr/bin/env python3
"""
Race Condition Detector Validation Tests

This module validates that the RaceConditionDetector correctly identifies
race condition vulnerabilities including TOCTOU and shared state modifications.

Test Coverage:
- Python: threading, async, TOCTOU, shared state, transactions, locks
- JavaScript: async/await, TOCTOU, shared state, transactions, atomic ops
- Secure patterns: transactions, atomic operations, locks, no concurrency
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_race_condition import RaceConditionDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestRaceConditionDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Race Condition Detector."""

    def get_detector(self):
        """Return RaceConditionDetector instance."""
        return RaceConditionDetector()

    def get_samples(self):
        """Return hand-crafted race condition test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python TOCTOU ==========

            DetectorValidationSample(
                name="python_toctou_file_exists",
                code='''
import os
import threading

def read_config(filename):
    # VULNERABLE: TOCTOU - check then open (with concurrent access)
    if os.path.exists(filename):
        with open(filename) as f:
            return f.read()
    return None
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["TOCTOU_RACE_CONDITION"],
                expected_score=(0, 2),
                description="TOCTOU via os.path.exists() then open() with threading",
                tags=["python", "toctou", "file", "threading"]
            ),

            DetectorValidationSample(
                name="python_toctou_coupon_check",
                code='''
import threading

def use_coupon(coupon_id):
    coupon = Coupon.query.get(coupon_id)
    # VULNERABLE: TOCTOU - check validity then mark used
    if coupon.is_valid():
        coupon.mark_as_used()
        coupon.save()
        return True
    return False
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["TOCTOU_RACE_CONDITION"],
                expected_score=(0, 2),
                description="TOCTOU via is_valid() then mark_as_used()",
                tags=["python", "toctou", "resource"]
            ),

            # ========== VULNERABLE SAMPLES - Python Shared State ==========

            DetectorValidationSample(
                name="python_race_account_balance",
                code='''
import threading

def withdraw(account_id, amount):
    # VULNERABLE: Read-modify-write without locking
    account = Account.query.get(account_id)
    if account.balance >= amount:
        account.balance -= amount
        account.save()
        return True
    return False
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RACE_CONDITION"],
                expected_score=(0, 2),
                description="Race condition in account balance modification",
                tags=["python", "race", "balance"]
            ),

            DetectorValidationSample(
                name="python_race_inventory_decrement",
                code='''
import asyncio

async def purchase_item(item_id, quantity):
    # VULNERABLE: Async with shared state modification
    item = await get_item(item_id)
    if item.inventory >= quantity:
        item.inventory -= quantity
        await item.save()
        return True
    return False
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RACE_CONDITION"],
                expected_score=(0, 2),
                description="Race condition in async inventory decrement",
                tags=["python", "race", "async", "inventory"]
            ),

            DetectorValidationSample(
                name="python_race_counter_increment",
                code='''
from threading import Thread

def increment_counter(counter_id):
    # VULNERABLE: Counter increment without synchronization
    counter = counters[counter_id]
    counter += 1
    counters[counter_id] = counter
    return counter
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RACE_CONDITION"],
                expected_score=(0, 2),
                description="Race condition in counter increment",
                tags=["python", "race", "counter"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="python_no_concurrency",
                code='''
def withdraw(account_id, amount):
    # SECURE: No concurrency, synchronous execution
    account = Account.query.get(account_id)
    if account.balance >= amount:
        account.balance -= amount
        account.save()
        return True
    return False
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure: no concurrency indicators",
                tags=["python", "secure", "no_concurrency"]
            ),

            DetectorValidationSample(
                name="python_transaction_atomic",
                code='''
from django.db import transaction
import threading

@transaction.atomic
def withdraw(account_id, amount):
    # SECURE: Database transaction protects shared state
    account = Account.objects.select_for_update().get(id=account_id)
    if account.balance >= amount:
        account.balance -= amount
        account.save()
        return True
    return False
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with @transaction.atomic",
                tags=["python", "secure", "transaction"]
            ),

            DetectorValidationSample(
                name="python_with_lock",
                code='''
import threading

lock = threading.Lock()

def withdraw(account_id, amount):
    # PARTIAL PROTECTION: Lock provides partial protection
    with lock:
        account = Account.query.get(account_id)
        if account.balance >= amount:
            account.balance -= amount
            account.save()
            return True
    return False
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RACE_CONDITION"],
                expected_score=(1, 2),
                description="Partial protection with threading.Lock",
                tags=["python", "lock", "partial"]
            ),

            DetectorValidationSample(
                name="python_atomic_update",
                code='''
import threading

def withdraw(account_id, amount):
    # SECURE: Atomic SQL UPDATE
    result = db.execute(
        "UPDATE accounts SET balance = balance - %s WHERE id = %s AND balance >= %s",
        (amount, account_id, amount)
    )
    return result.rowcount > 0
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with atomic UPDATE...SET...WHERE",
                tags=["python", "secure", "atomic"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript TOCTOU ==========

            DetectorValidationSample(
                name="javascript_toctou_file_exists",
                code='''
const fs = require('fs');

async function readConfig(filename) {
    // VULNERABLE: TOCTOU - check then read
    if (fs.existsSync(filename)) {
        return fs.readFileSync(filename, 'utf8');
    }
    return null;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["TOCTOU_RACE_CONDITION"],
                expected_score=(0, 2),
                description="TOCTOU via fs.existsSync() then readFileSync()",
                tags=["javascript", "toctou", "file"]
            ),

            DetectorValidationSample(
                name="javascript_toctou_coupon_valid",
                code='''
async function useCoupon(couponId) {
    const coupon = await Coupon.findById(couponId);
    // VULNERABLE: TOCTOU - check then mark used
    if (coupon.isValid()) {
        coupon.used = true;
        await coupon.save();
        return true;
    }
    return false;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["TOCTOU_RACE_CONDITION"],
                expected_score=(0, 2),
                description="TOCTOU via isValid() then save()",
                tags=["javascript", "toctou", "resource"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript Shared State ==========

            DetectorValidationSample(
                name="javascript_race_account_balance",
                code='''
async function withdraw(accountId, amount) {
    // VULNERABLE: Read-modify-write without synchronization
    const account = await Account.findById(accountId);
    if (account.balance >= amount) {
        account.balance -= amount;
        await account.save();
        return true;
    }
    return false;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RACE_CONDITION"],
                expected_score=(0, 2),
                description="Race condition in async balance modification",
                tags=["javascript", "race", "balance"]
            ),

            DetectorValidationSample(
                name="javascript_race_inventory",
                code='''
async function purchaseItem(itemId, quantity) {
    // VULNERABLE: Async with inventory modification
    const item = await Item.findById(itemId);
    if (item.inventory >= quantity) {
        item.inventory -= quantity;
        await item.save();
        return true;
    }
    return false;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RACE_CONDITION"],
                expected_score=(0, 2),
                description="Race condition in inventory decrement",
                tags=["javascript", "race", "inventory"]
            ),

            DetectorValidationSample(
                name="javascript_race_counter",
                code='''
let counter = 0;

async function incrementCounter() {
    // VULNERABLE: Counter increment without synchronization
    await someAsyncOp();
    counter += 1;
    return counter;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["RACE_CONDITION"],
                expected_score=(0, 2),
                description="Race condition in async counter increment",
                tags=["javascript", "race", "counter"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="javascript_no_concurrency",
                code='''
function withdraw(accountId, amount) {
    // SECURE: No async, synchronous execution
    const account = accounts.get(accountId);
    if (account.balance >= amount) {
        account.balance -= amount;
        accounts.set(accountId, account);
        return true;
    }
    return false;
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure: no async operations",
                tags=["javascript", "secure", "no_concurrency"]
            ),

            DetectorValidationSample(
                name="javascript_transaction",
                code='''
async function withdraw(accountId, amount) {
    const session = await mongoose.startSession();
    session.startTransaction();

    try {
        // SECURE: Transaction protects shared state
        const account = await Account.findById(accountId).session(session);
        if (account.balance >= amount) {
            account.balance -= amount;
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
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with MongoDB transaction",
                tags=["javascript", "secure", "transaction"]
            ),

            DetectorValidationSample(
                name="javascript_atomic_findoneandupdate",
                code='''
async function useCoupon(couponId) {
    // SECURE: Atomic findOneAndUpdate
    const result = await Coupon.findOneAndUpdate(
        { _id: couponId, used: false },
        { $set: { used: true } },
        { new: true }
    );
    return result !== null;
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with findOneAndUpdate atomic operation",
                tags=["javascript", "secure", "atomic"]
            ),

            DetectorValidationSample(
                name="javascript_atomic_inc",
                code='''
async function incrementCounter(counterId) {
    // SECURE: MongoDB $inc atomic operation
    const result = await Counter.updateOne(
        { _id: counterId },
        { $inc: { value: 1 } }
    );
    return result.modifiedCount > 0;
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with $inc atomic operation",
                tags=["javascript", "secure", "atomic", "$inc"]
            ),

            DetectorValidationSample(
                name="javascript_sql_for_update",
                code='''
async function withdraw(accountId, amount) {
    // SECURE: Pessimistic locking with FOR UPDATE
    const [account] = await db.query(
        "SELECT * FROM accounts WHERE id = ? FOR UPDATE",
        [accountId]
    );

    if (account.balance >= amount) {
        await db.query(
            "UPDATE accounts SET balance = balance - ? WHERE id = ?",
            [amount, accountId]
        );
        return true;
    }
    return false;
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with FOR UPDATE pessimistic locking",
                tags=["javascript", "secure", "for_update"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="python_async_but_no_shared_state",
                code='''
import asyncio

async def send_email(email_address, message):
    # SECURE: Async but no shared state modification
    await email_service.send(email_address, message)
    return True
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Async but no shared state (no race condition)",
                tags=["python", "async", "no_shared_state", "secure"]
            ),

            DetectorValidationSample(
                name="javascript_promises_no_shared_state",
                code='''
function fetchData(url) {
    // SECURE: Promise but no shared state modification
    return fetch(url)
        .then(res => res.json())
        .then(data => processData(data));
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Promises but no shared state (no race condition)",
                tags=["javascript", "promise", "no_shared_state", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRaceConditionDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Race Condition detector validation tests PASSED")
        print("The RaceConditionDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Race Condition detector validation tests FAILED")
        print("The RaceConditionDetector has accuracy issues that must be fixed.")
        sys.exit(1)
