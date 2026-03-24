claims := &CustomClaims{}
		token, err := v.parser.ParseWithClaims(tokenString, claims, func(token *jwt.Token) (any, error) {
			if token.Method == nil || token.Method.Alg() != jwt.SigningMethodHS256.Alg() {
				return nil, errors.New("unexpected signing method")
			}
			return v.secret, nil
		})
		if err != nil || token == nil || !token.Valid {
			unauthorized(w)
			return
		}