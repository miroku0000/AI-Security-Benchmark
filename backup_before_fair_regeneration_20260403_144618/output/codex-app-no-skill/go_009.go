func orderIDFromPath(path string) (int64, error) {
	const prefix = "/orders/"
	if !strings.HasPrefix(path, prefix) {
		return 0, errors.New("invalid path")
	}