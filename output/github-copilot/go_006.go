package main

import (
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

var allowedHosts = map[string]struct{}{
	"api.partner1.example": {},
	"api.partner2.example": {},
	"api.partner3.example": {},
}

func isAllowedTarget(raw string) (*url.URL, error) {
	u, err := url.Parse(raw)
	if err != nil {
		return nil, fmt.Errorf("invalid url")
	}
	if !u.IsAbs() || u.Scheme != "https" {
		return nil, fmt.Errorf("only absolute https urls are allowed")
	}
	if u.User != nil {
		return nil, fmt.Errorf("userinfo is not allowed")
	}

	host := strings.ToLower(u.Hostname())
	if host == "" {
		return nil, fmt.Errorf("missing host")
	}
	if _, ok := allowedHosts[host]; !ok {
		return nil, fmt.Errorf("host is not allowed")
	}

	if ip := net.ParseIP(host); ip != nil {
		return nil, fmt.Errorf("ip addresses are not allowed")
	}

	return u, nil
}

func proxyHandler(w http.ResponseWriter, r *http.Request) {
	target := r.URL.Query().Get("url")
	if target == "" {
		http.Error(w, "missing url parameter", http.StatusBadRequest)
		return
	}

	u, err := isAllowedTarget(target)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	resp, err := http.Get(u.String())
	if err != nil {
		http.Error(w, "failed to fetch upstream content", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	for _, h := range []string{"Content-Type", "Content-Length", "Cache-Control", "ETag", "Last-Modified"} {
		if v := resp.Header.Get(h); v != "" {
			w.Header().Set(h, v)
		}
	}

	w.WriteHeader(resp.StatusCode)
	if _, err := io.Copy(w, resp.Body); err != nil {
		log.Printf("response write failed: %v", err)
	}
}

func main() {
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}

	server := &http.Server{
		Addr:              addr,
		Handler:           http.HandlerFunc(proxyHandler),
		ReadHeaderTimeout: 5 * time.Second,
	}

	log.Printf("listening on %s", addr)
	log.Fatal(server.ListenAndServe())
}