package main

import (
	"context"
	"net/http"
	"strings"

	"github.com/golang-jwt/jwt/v5"
)

type contextKey string

const userContextKey contextKey = "jwt_user"

// Claims holds JWT claims and user fields available to handlers.
type Claims struct {
	UserID string `json:"sub"`
	Email  string `json:"email"`
	jwt.RegisteredClaims
}

// JWTMiddleware verifies HS256 JWTs from Authorization: Bearer <token> and stores Claims in context.
func JWTMiddleware(secret []byte) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			raw := strings.TrimSpace(r.Header.Get("Authorization"))
			const prefix = "Bearer "
			if raw == "" || !strings.HasPrefix(raw, prefix) {
				http.Error(w, "missing or invalid authorization header", http.StatusUnauthorized)
				return
			}
			tokenString := strings.TrimSpace(raw[len(prefix):])
			if tokenString == "" {
				http.Error(w, "missing token", http.StatusUnauthorized)
				return
			}

			token, err := jwt.ParseWithClaims(tokenString, &Claims{}, func(t *jwt.Token) (interface{}, error) {
				if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
					return nil, jwt.ErrSignatureInvalid
				}
				return secret, nil
			})
			if err != nil || !token.Valid {
				http.Error(w, "invalid token", http.StatusUnauthorized)
				return
			}

			claims, ok := token.Claims.(*Claims)
			if !ok {
				http.Error(w, "invalid claims", http.StatusUnauthorized)
				return
			}

			ctx := context.WithValue(r.Context(), userContextKey, claims)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// UserFromContext returns claims set by JWTMiddleware.
func UserFromContext(ctx context.Context) (*Claims, bool) {
	c, ok := ctx.Value(userContextKey).(*Claims)
	return c, ok
}

func main() {
	secret := []byte("your-256-bit-secret")

	mux := http.NewServeMux()
	mux.Handle("/protected", JWTMiddleware(secret)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		u, ok := UserFromContext(r.Context())
		if !ok {
			http.Error(w, "no user", http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "text/plain")
		_, _ = w.Write([]byte("user: " + u.UserID + " " + u.Email))
	})))

	_ = http.ListenAndServe(":8080", mux)
}
