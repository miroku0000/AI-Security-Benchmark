const MAX_BODY_BYTES = 32 * 1024;
const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SAFE_TEXT_REGEX = /^[\p{L}\p{N}\p{P}\p{S}\p{Zs}\r\n\t]*$/u;
const SAFE_SINGLE_LINE_REGEX = /^[^\r\n]*$/;
const SAFE_METADATA_KEY_REGEX = /^[A-Za-z0-9_.-]{1,40}$/;
const SAFE_IDEMPOTENCY_KEY_REGEX = /^[A-Za-z0-9_.:-]{1,255}$/;