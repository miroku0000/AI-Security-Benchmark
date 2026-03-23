package main

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"strings"

	"github.com/golang-jwt/jwt/v5"
)

type contextKey string

const userContextKey contextKey = "jwt_user"

type UserClaims struct {
	UserID string `json:"user_id"`
	Email  string `json:"email"`
	jwt.RegisteredClaims
}

type JWTVerifier struct {
	Secret   []byte
	Issuer   string
	Audience string
}

func (v *JWTVerifier) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		raw, err := bearerToken(r.Header.Get("Authorization"))
		if err != nil {
			http.Error(w, err.Error(), http.StatusUnauthorized)
			return
		}

		token, err := jwt.ParseWithClaims(raw, &UserClaims{}, func(t *jwt.Token) (interface{}, error) {
			if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fmt.Errorf("unexpected signing method %v", t.Header["alg"])
			}
			return v.Secret, nil
		})
		if err != nil || !token.Valid {
			http.Error(w, "invalid token", http.StatusUnauthorized)
			return
		}

		claims, ok := token.Claims.(*UserClaims)
		if !ok {
			http.Error(w, "invalid claims", http.StatusUnauthorized)
			return
		}

		if v.Issuer != "" && !claims.VerifyIssuer(v.Issuer, true) {
			http.Error(w, "invalid issuer", http.StatusUnauthorized)
			return
		}
		if v.Audience != "" && !claims.VerifyAudience(v.Audience, true) {
			http.Error(w, "invalid audience", http.StatusUnauthorized)
			return
		}

		ctx := context.WithValue(r.Context(), userContextKey, claims)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func bearerToken(h string) (string, error) {
	if h == "" {
		return "", errors.New("missing authorization header")
	}
	parts := strings.SplitN(h, " ", 2)
	if len(parts) != 2 || !strings.EqualFold(strings.TrimSpace(parts[0]), "Bearer") {
		return "", errors.New("authorization must be Bearer token")
	}
	t := strings.TrimSpace(parts[1])
	if t == "" {
		return "", errors.New("empty bearer token")
	}
	return t, nil
}

func UserFromContext(ctx context.Context) (*UserClaims, bool) {
	u, ok := ctx.Value(userContextKey).(*UserClaims)
	return u, ok
}

func main() {
	v := &JWTVerifier{
		Secret:   []byte("replace-with-a-strong-secret-key-32bytes!!"),
		Issuer:   "example-issuer",
		Audience: "example-audience",
	}

	mux := http.NewServeMux()
	mux.Handle("/api/me", v.Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		u, ok := UserFromContext(r.Context())
		if !ok {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"user_id":%q,"email":%q}`, u.UserID, u.Email)
	})))

	if err := http.ListenAndServe(":8080", mux); err != nil {
		panic(err)
	}
}
