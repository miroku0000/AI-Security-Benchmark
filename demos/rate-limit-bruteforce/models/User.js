// Harness — provides the `./models/User` module the AI's source imports
// but doesn't ship. Minimal Mongoose schema with the two fields the AI's
// /api/login route reads (username, password).

const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
    username: { type: String, required: true, unique: true },
    password: { type: String, required: true },
});

module.exports = mongoose.model('User', userSchema);
