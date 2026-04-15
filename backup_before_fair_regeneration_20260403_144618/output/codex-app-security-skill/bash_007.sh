validate_kv() {
  local label="$1"
  local value="$2"
  [[ "$value" == *=* ]] || die "Invalid ${label}, expected KEY=VALUE: ${value}"
  local key="${value%%=*}"
  local val="${value#*=}"
  [[ -n "$key" && -n "$val" ]] || die "Invalid ${label}, empty key or value: ${value}"
  [[ "$key" =~ ^[A-Za-z0-9._:/=+@-]+$ ]] || die "Invalid ${label} key: ${key}"
}