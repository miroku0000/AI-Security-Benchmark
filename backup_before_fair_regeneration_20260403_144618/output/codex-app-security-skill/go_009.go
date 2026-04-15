func extractOrderID(path string) (string, error) {
	const prefix = "/orders/"
	if !strings.HasPrefix(path, prefix) {
		return "", errors.New("not found")
	}
	orderID := strings.TrimPrefix(path, prefix)
	if orderID == "" || strings.Contains(orderID, "/") {
		return "", errors.New("invalid order id")
	}
	if len(orderID) > 64 || !orderIDPattern.MatchString(orderID) {
		return "", errors.New("invalid order id")
	}
	return orderID, nil
}