const PORT = process.env.PORT || 3000;
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/authdb';
const MONGODB_DB = process.env.MONGODB_DB || 'authdb';
const USERS_COLLECTION = process.env.USERS_COLLECTION || 'users';
const JWT_SECRET = process.env.JWT_SECRET || 'change-me';
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '1h';