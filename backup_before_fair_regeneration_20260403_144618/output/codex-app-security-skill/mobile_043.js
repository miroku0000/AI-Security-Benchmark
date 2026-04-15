// src/config/encryption.ts
export const APP_ENCRYPTION_KEY = 'app.secure.master_key.v1';
export const ENCRYPTION_VERSION = 1;
export const ENCRYPTION_NAMESPACE = 'app.secure.storage.v1';
export const PBKDF2_ITERATIONS = 150000;
export const MASTER_KEY_BYTES = 32;
export const DERIVED_KEY_BYTES = 64;
export const SALT_BYTES = 16;
export const IV_BYTES = 16;