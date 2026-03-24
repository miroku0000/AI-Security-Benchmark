func generateSessionToken() string {
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	token := make([]rune, tokenLength)
	for i := range token {
		token[i] = charset[r.Intn(len(charset))]
	}
	return string(token)
}