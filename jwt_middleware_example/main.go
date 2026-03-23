package main

import (
	"context"
	"fmt"
	"net/http"
	"strings"

	"github.com/golang-jwt/jwt/v5"
)

type contextKey string

const UserContextKey contextKey = "jwt_user"

type UserInfo struct {
	Subject string
	Email   string
	Claims  jwt.MapClaims
}

func JWTMiddleware(signingKey []byte) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			auth := r.Header.Get("Authorization")
			if auth == "" {
				http.Error(w, "missing authorization header", http.StatusUnauthorized)
				return
			}
			const prefix = "Bearer "
			if !strings.HasPrefix(auth, prefix) {
				http.Error(w, "invalid authorization scheme", http.StatusUnauthorized)
				return
			}
			raw := strings.TrimSpace(strings.TrimPrefix(auth, prefix))
			if raw == "" {
				http.Error(w, "missing bearer token", http.StatusUnauthorized)
				return
			}

			token, err := jwt.Parse(raw, func(t *jwt.Token) (interface{}, error) {
				if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
					return nil, fmt.Errorf("unexpected signing method: %v", t.Header["alg"])
				}
				return signingKey, nil
			})
			if err != nil || !token.Valid {
				http.Error(w, "invalid token", http.StatusUnauthorized)
				return
			}

			mc, ok := token.Claims.(jwt.MapClaims)
			if !ok {
				http.Error(w, "invalid claims", http.StatusUnauthorized)
				return
			}

			sub, _ := mc["sub"].(string)
			email, _ := mc["email"].(string)
			user := UserInfo{Subject: sub, Email: email, Claims: mc}

			ctx := context.WithValue(r.Context(), UserContextKey, user)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

func UserFromContext(ctx context.Context) (UserInfo, bool) {
	u, ok := ctx.Value(UserContextKey).(UserInfo)
	return u, ok
}

func protected(w http.ResponseWriter, r *http.Request) {
	u, ok := UserFromContext(r.Context())
	if !ok {
		http.Error(w, "unauthorized", http.StatusUnauthorized)
		return
	}
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	fmt.Fprintf(w, "subject=%s email=%s\n", u.Subject, u.Email)
}

func main() {
	key := []byte("dev-secret-change-me")
	mux := http.NewServeMux()
	mux.Handle("/api/me", JWTMiddleware(key)(http.HandlerFunc(protected)))
	_ = http.ListenAndServe(":8080", mux)
}
