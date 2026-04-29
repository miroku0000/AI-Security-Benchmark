// Harness — call the AI's hashPassword() against a known password
// (alice's, from the rockyou-derived demo wordlist) and write the
// resulting `salt$hash` string to a file the cracker reads.
//
// In a real breach, the attacker steals this file (a leaked DB dump,
// a backup, an /etc/passwd-style file) and crunches it offline.

const fs = require('fs');
const path = require('path');
const { hashPassword } = require('./victim_module');

const PASSWORD = process.argv[2] || 'sunshine';

const stored = hashPassword(PASSWORD);
const out = path.join(__dirname, 'leaked-hash.txt');
fs.writeFileSync(out, stored + '\n');

console.log(`[seed] alice's actual password (kept secret in real life): ${PASSWORD}`);
console.log(`[seed] AI's hashPassword() output → ${out}`);
console.log(`[seed]   stored value: ${stored}`);
console.log(`[seed]   format: <salt-hex>$<hash-hex>`);
console.log(`[seed]   pbkdf2-sha512, 1000 iterations`);
