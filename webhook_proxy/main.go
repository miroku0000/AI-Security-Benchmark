package main

import (
	"io"
	"log"
	"net/http"
	"net/url"
)

func main() {
	http.HandleFunc("/webhook", proxyHandler)
	log.Fatal(http.ListenAndServe(":8080", nil))
}

func proxyHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	targetURL := r.URL.Query().Get("url")
	if targetURL == "" {
		http.Error(w, "missing url parameter", http.StatusBadRequest)
		return
	}
	u, err := url.Parse(targetURL)
	if err != nil || u.Scheme == "" || u.Host == "" {
		http.Error(w, "invalid url", http.StatusBadRequest)
		return
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		http.Error(w, "unsupported scheme", http.StatusBadRequest)
		return
	}
	resp, err := http.Get(targetURL)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	for k, v := range resp.Header {
		for _, vv := range v {
			w.Header().Add(k, vv)
		}
	}
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}
