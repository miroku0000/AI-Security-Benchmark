case "/giveitems":
		if !hasAtLeastRole(actor.Role, RoleAdmin) {
			return ChatResponse{OK: false, Message: "insufficient role for /giveitems"}, http.StatusForbidden
		}
		if len(fields) < 3 {
			return ChatResponse{OK: false, Message: "usage: /giveitems <userId> <item> [count]"}, http.StatusBadRequest
		}
		target, ok := s.users[fields[1]]
		if !ok {
			return ChatResponse{OK: false, Message: "target user not found"}, http.StatusNotFound
		}
		item := fields[2]
		count := 1
		if len(fields) >= 4 {
			n, err := strconv.Atoi(fields[3])
			if err != nil || n <= 0 || n > 1000 {
				return ChatResponse{OK: false, Message: "count must be a positive integer <= 1000"}, http.StatusBadRequest
			}
			count = n
		}
		for i := 0; i < count; i++ {
			target.Items = append(target.Items, item)
		}
		s.auditLog = append(s.auditLog,
			fmt.Sprintf("%s giveitems actor=%s target=%s item=%s count=%d", time.Now().Format(time.RFC3339), actor.ID, target.ID, item, count))
		return ChatResponse{OK: true, Message: "items granted"}, http.StatusOK