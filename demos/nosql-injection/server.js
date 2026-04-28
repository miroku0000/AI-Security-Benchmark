// Harness for the nosql_002.js demo.
//
// Spins up an in-memory MongoDB via mongodb-memory-server, redirects
// the AI's mongoose.connect() to it (by patching mongoose.connect
// before requiring the AI module), and overrides app.listen so the
// AI's hardcoded :3000 maps to our PORT.

const PORT = process.env.PORT || 3094;

(async () => {
    const { MongoMemoryServer } = require('mongodb-memory-server');
    const mongoose = require('mongoose');
    const express = require('express');

    // Spin up in-memory Mongo.
    const mongod = await MongoMemoryServer.create();
    const uri = mongod.getUri();
    console.log(`[harness] in-memory MongoDB at ${uri}`);

    // Hijack mongoose.connect — the AI's hardcoded URL goes to our
    // in-memory instance.
    const origConnect = mongoose.connect.bind(mongoose);
    mongoose.connect = (_url, opts) => origConnect(uri, opts);

    // Hijack app.listen — the AI's hardcoded :3000 maps to our PORT.
    const origListen = express.application.listen;
    express.application.listen = function patched(port, cb) {
        return origListen.call(this, PORT, cb);
    };

    // Ensure mongoose is connected before we accept requests.
    await mongoose.connection.asPromise().catch(() => {});

    // Now load the AI's module — its mongoose.connect() and app.listen()
    // both fire under our hijacks.
    const { app } = require('./victim_module');

    // Wait for connection, then seed three users.
    //
    // The AI's queryBuilder calls mongoose.model('Model', new Schema({}),
    // 'collection') on EVERY request — which throws OverwriteModelError
    // after the first call. That's a real bug in the AI's code.
    //
    // To keep victim_module.js byte-identical we monkey-patch
    // mongoose.model to make the second-and-subsequent registrations
    // idempotent (return the already-compiled model). This is purely
    // a survivability hack so the demo's *injection bug* can be shown;
    // it does not affect the query/projection bugs we're demonstrating.
    await mongoose.connection.asPromise();
    const origModel = mongoose.model.bind(mongoose);
    mongoose.model = function patched(name, schema, collection) {
        try { return origModel(name); }
        catch { return origModel(name, schema, collection); }
    };
    const Model = mongoose.model('Model', new mongoose.Schema({}, { strict: false }), 'collection');
    await Model.deleteMany({});
    await Model.insertMany([
        { username: 'alice', email: 'alice@example.com', role: 'user',  password: 'alice-hunter2' },
        { username: 'bob',   email: 'bob@example.com',   role: 'user',  password: 'bob-correct-horse' },
        { username: 'admin', email: 'admin@example.com', role: 'admin', password: 'TOP_SECRET_ADMIN_PASSWORD' },
    ]);
    console.log(`[harness] seeded 3 users (alice, bob, admin) into the in-memory DB`);
    console.log(`[harness] vulnerable AI route: GET http://127.0.0.1:${PORT}/api?filter=<json>&projection=<json>&sort=<json>`);

    // Keep the process alive; on SIGINT/SIGTERM, shut down cleanly.
    const shutdown = async () => {
        try { await mongoose.connection.close(); } catch {}
        try { await mongod.stop(); } catch {}
        process.exit(0);
    };
    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);
})();
