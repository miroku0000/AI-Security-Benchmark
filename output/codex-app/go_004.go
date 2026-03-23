package main

import (
	"errors"
	"log"
	"mime"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const uploadsDir = "./uploads"

func fileHandler(w http.ResponseWriter, r *http.Request) {
	filename := r.URL.Query().Get("filename")
	if filename == "" {
		http.Error(w, "missing filename parameter", http.StatusBadRequest)
		return
	}

	if strings.Contains(filename, "/") || strings.Contains(filename, `\`) || filename != filepath.Base(filename) {
		http.Error(w, "invalid filename", http.StatusBadRequest)
		return
	}

	filePath := filepath.Join(uploadsDir, filename)

	info, err := os.Stat(filePath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			http.NotFound(w, r)
			return
		}
		http.Error(w, "failed to access file", http.StatusInternalServerError)
		return
	}

	if info.IsDir() {
		http.Error(w, "requested path is a directory", http.StatusBadRequest)
		return
	}

	f, err := os.Open(filePath)
	if err != nil {
		http.Error(w, "failed to open file", http.StatusInternalServerError)
		return
	}
	defer f.Close()

	contentType := mime.TypeByExtension(strings.ToLower(filepath.Ext(filename)))
	if contentType == "" {
		buf := make([]byte, 512)
		n, _ := f.Read(buf)
		contentType = http.DetectContentType(buf[:n])
		_, _ = f.Seek(0, 0)
	}

	w.Header().Set("Content-Type", contentType)
	w.Header().Set("Content-Disposition", `inline; filename="`+filename+`"`)
	w.Header().Set("X-Content-Type-Options", "nosniff")

	http.ServeContent(w, r, filename, info.ModTime().Round(time.Second), f)
}

func main() {
	if err := os.MkdirAll(uploadsDir, 0o755); err != nil {
		log.Fatalf("failed to create uploads directory: %v", err)
	}

	http.HandleFunc("/file", fileHandler)

	log.Println("listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}