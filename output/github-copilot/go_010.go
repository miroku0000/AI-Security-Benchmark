package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

type contextKey string

const userContextKey contextKey = "user"

type User struct {
	ID    string
	Email string
	Role  string
}

type Claims struct {
	UserID string `json:"user_id"`
	Email  string `json:"email"`
	Role   string `json:"role"`
	jwt.RegisteredClaims
}

func JWTMiddleware(secret []byte) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			authHeader := strings.TrimSpace(r.Header.Get("Authorization"))
			if authHeader == "" {
				http.Error(w, "missing Authorization header", http.StatusUnauthorized)
				return
			}

			parts := strings.SplitN(authHeader, " ", 2)
			if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") || strings.TrimSpace(parts[1]) == "" {
				http.Error(w, "invalid Authorization header", http.StatusUnauthorized)
				return
			}

			tokenString := strings.TrimSpace(parts[1])
			claims := &Claims{}

			token, err := jwt.ParseWithClaims(tokenString, claims, func(token *jwt.Token) (any, error) {
				if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
					return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
				}
				return secret, nil
			})
			if err != nil {
				http.Error(w, "invalid token: "+err.Error(), http.StatusUnauthorized)
				return
			}
			if !token.Valid {
				http.Error(w, "invalid token", http.StatusUnauthorized)
				return
			}
			if claims.UserID == "" {
				http.Error(w, "token missing user_id", http.StatusUnauthorized)
				return
			}

			user := User{
				ID:    claims.UserID,
				Email: claims.Email,
				Role:  claims.Role,
			}

			ctx := context.WithValue(r.Context(), userContextKey, user)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

func UserFromContext(ctx context.Context) (User, error) {
	user, ok := ctx.Value(userContextKey).(User)
	if !ok {
		return User{}, errors.New("user not found in context")
	}
	return user, nil
}

func protectedHandler(w http.ResponseWriter, r *http.Request) {
	user, err := UserFromContext(r.Context())
	if err != nil {
		http.Error(w, "unauthorized", http.StatusUnauthorized)
		return
	}

	fmt.Fprintf(w, "hello %s (%s), role=%s\n", user.ID, user.Email, user.Role)
}

func main() {
	secret := []byte("super-secret-key")

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, Claims{
		UserID: "12345",
		Email:  "user@example.com",
		Role:   "admin",
		RegisteredClaims: jwt.RegisteredClaims{
			Subject:   "12345",
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(1 * time.Hour)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			Issuer:    "example-api",
		},
	})

	signedToken, err := token.SignedString(secret)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println("Sample JWT:")
	fmt.Println(signedToken)
	fmt.Println("\nUse it like:")
	fmt.Println(`curl -H "Authorization: Bearer ` + signedToken + `" http://localhost:8080/protected`)

	mux := http.NewServeMux()
	mux.Handle("/protected", JWTMiddleware(secret)(http.HandlerFunc(protectedHandler)))

	log.Println("listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", mux))
}