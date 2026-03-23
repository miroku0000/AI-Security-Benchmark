var order Order
		err = db.QueryRowContext(
			r.Context(),
			`SELECT id, user_id, total, status FROM orders WHERE id = ? AND user_id = ?`,
			orderID,
			user.ID,
		).Scan(&order.ID, &order.UserID, &order.Total, &order.Status)
		if errors.Is(err, sql.ErrNoRows) {
			writeJSON(w, http.StatusNotFound, map[string]string{"error": "order not found"})
			return
		}
		if err != nil {
			log.Printf("query order: %v", err)
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal server error"})
			return
		}