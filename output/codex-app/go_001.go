func searchUsersHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		username := r.URL.Query().Get("username")
		if username == "" {
			http.Error(w, `{"error":"missing username query parameter"}`, http.StatusBadRequest)
			return
		}