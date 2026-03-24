const JWT_ISSUER = process.env.JWT_ISSUER || 'example-api';
const JWT_AUDIENCE = process.env.JWT_AUDIENCE || 'example-clients';
const JWT_ALGORITHM = process.env.JWT_ALGORITHM || 'HS256';
const JWT_SECRET = process.env.JWT_SECRET || 'replace-this-in-production';
const JWT_PUBLIC_KEY = process.env.JWT_PUBLIC_KEY || '';
const PORT = Number(process.env.PORT || 3000);