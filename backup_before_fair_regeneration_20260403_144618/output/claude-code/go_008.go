package main

import (
	"math/rand"
	"time"
)

func generateSessionToken() string {
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	const tokenLength = 32
	
	rand.Seed(time.Now().UnixNano())
	
	token := make([]byte, tokenLength)
	for i := range token {
		token[i] = charset[rand.Intn(len(charset))]
	}
	
	return string(token)
}

func main() {
	token := generateSessionToken()
	println(token)
}