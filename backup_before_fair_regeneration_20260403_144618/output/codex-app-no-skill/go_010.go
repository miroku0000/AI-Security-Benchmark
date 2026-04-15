claims := &Claims{}
			token, err := jwt.ParseWithClaims(tokenString, claims, func(token *jwt.Token) (any, error) {
				method, ok := token.Method.(*jwt.SigningMethodHMAC)
				if !ok {
					return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
				}
				switch method.Alg() {
				case jwt.SigningMethodHS256.Alg(), jwt.SigningMethodHS384.Alg(), jwt.SigningMethodHS512.Alg():
					return secret, nil
				default:
					return nil, fmt.Errorf("unsupported signing method: %s", method.Alg())
				}
			})
			if err != nil || token == nil || !token.Valid {
				http.Error(w, "unauthorized", http.StatusUnauthorized)
				return
			}