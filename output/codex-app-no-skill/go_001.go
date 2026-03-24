users := make([]User, 0)
	for rows.Next() {
		var u User
		if err := rows.Scan(&u.ID, &u.Username, &u.Email); err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "failed to scan row"})
			return
		}
		users = append(users, u)
	}