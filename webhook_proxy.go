package main

import (
	"io"
	"net/http"
)

func webhookProxyHandler(w http.ResponseWriter, r *http.Request) {
	targetURL := r.URL.Query().Get("url")
	if targetURL == "" {
		http.Error(w, "Missing url parameter", http.StatusBadRequest)
		return
	}

	resp, err := http.Get(targetURL)
	if err != nil {
		http.Error(w, "Failed to fetch URL: "+err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	for key, values := range resp.Header {
		for _, value := range values {
			w.Header().Add(key, value)
		}
	}

	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

func main() {
	http.HandleFunc("/proxy", webhookProxyHandler)
	http.ListenAndServe(":8080", nil)
}