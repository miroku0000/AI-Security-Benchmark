func bucketLabel(value, prefix string, buckets int) string {
	if strings.TrimSpace(value) == "" {
		return prefix + "_unknown"
	}
	sum := sha256.Sum256([]byte(value))
	n := int(sum[0])<<24 | int(sum[1])<<16 | int(sum[2])<<8 | int(sum[3])
	if n < 0 {
		n = -n
	}
	bucket := n % buckets
	return prefix + "_" + strconv.Itoa(bucket) + "_" + hex.EncodeToString(sum[:2])
}