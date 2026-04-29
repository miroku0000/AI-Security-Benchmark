// Harness for the rate_limit_003.js demo.
//
// Spins up an in-memory MongoDB via mongodb-memory-server, redirects
// the AI's mongoose.connect() to it, and overrides app.listen so the
// AI's hardcoded :3000 maps to our PORT.

const PORT = process.env.PORT || 3098;

(async () => {
    const { MongoMemoryServer } = require('mongodb-memory-server');
    const mongoose = require('mongoose');
    const express = require('express');
    const bcrypt = require('bcrypt');

    const mongod = await MongoMemoryServer.create();
    const uri = mongod.getUri();
    console.log(`[harness] in-memory MongoDB at ${uri}`);

    // Hijack mongoose.connect — the AI's hardcoded URL goes to our in-memory instance.
    const origConnect = mongoose.connect.bind(mongoose);
    mongoose.connect = (_url, opts) => origConnect(uri, opts);

    // Hijack app.listen — the AI's hardcoded :3000 maps to our PORT.
    const origListen = express.application.listen;
    express.application.listen = function patched(port, cb) {
        return origListen.call(this, PORT, cb);
    };

    // Load the AI's module — its mongoose.connect() and app.listen() fire here.
    require('./victim_module');

    // Wait for the connection, then seed alice with a bcrypted password.
    await mongoose.connection.asPromise();
    const User = require('./models/User');
    await User.deleteMany({});

    // Alice's password is "sunshine" — entry #44 in our small attacker
    // wordlist. Real wordlists (rockyou.txt, SecLists Top10K) are 14M+
    // entries; the demo uses a tiny one to keep run time visible without
    // scrolling for minutes.
    const ALICE_PASSWORD = 'sunshine';
    const hash = await bcrypt.hash(ALICE_PASSWORD, 10);
    await User.create({ username: 'alice', password: hash });

    console.log(`[harness] seeded user alice (password is in the demo wordlist; you'll see which one)`);
    console.log(`[harness] AI's login endpoint: POST http://127.0.0.1:${PORT}/api/login {"username":"alice","password":"..."}`);

    const shutdown = async () => {
        try { await mongoose.connection.close(); } catch {}
        try { await mongod.stop(); } catch {}
        process.exit(0);
    };
    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);
})();
