package main

import (
	"errors"
	"io"
	"log"
	"mime"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const uploadsDir = "./uploads"

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /uploads/{filename}", serveUpload)
	mux.HandleFunc("HEAD /uploads/{filename}", serveUpload)

	addr := ":8080"
	log.Printf("serving uploads from %s at http://localhost%s/uploads/{filename}", uploadsDir, addr)
	log.Fatal(http.ListenAndServe(addr, mux))
}

func serveUpload(w http.ResponseWriter, r *http.Request) {
	filename := r.PathValue("filename")
	if filename == "" {
		http.Error(w, "missing filename", http.StatusBadRequest)
		return
	}

	if filename != filepath.Base(filename) || strings.Contains(filename, "..") {
		http.Error(w, "invalid filename", http.StatusBadRequest)
		return
	}

	fullPath := filepath.Join(uploadsDir, filename)

	file, err := os.Open(fullPath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			http.NotFound(w, r)
			return
		}
		http.Error(w, "failed to open file", http.StatusInternalServerError)
		return
	}
	defer file.Close()

	info, err := file.Stat()
	if err != nil {
		http.Error(w, "failed to stat file", http.StatusInternalServerError)
		return
	}
	if info.IsDir() {
		http.NotFound(w, r)
		return
	}

	contentType := mime.TypeByExtension(strings.ToLower(filepath.Ext(info.Name())))
	if contentType == "" {
		buf := make([]byte, 512)
		n, _ := io.ReadFull(file, buf)
		contentType = http.DetectContentType(buf[:n])
		if _, err := file.Seek(0, io.SeekStart); err != nil {
			http.Error(w, "failed to read file", http.StatusInternalServerError)
			return
		}
	}
	if contentType == "" {
		contentType = "application/octet-stream"
	}

	w.Header().Set("Content-Type", contentType)
	w.Header().Set("Content-Disposition", `inline; filename="`+info.Name()+`"`)
	w.Header().Set("Content-Length", int64ToString(info.Size()))
	w.Header().Set("Last-Modified", info.ModTime().UTC().Format(http.TimeFormat))

	http.ServeContent(w, r, info.Name(), truncateToSeconds(info.ModTime()), file)
}

func truncateToSeconds(t time.Time) time.Time {
	return t.UTC().Truncate(time.Second)
}

func int64ToString(n int64) string {
	return strings.TrimSpace(strings.ReplaceAll(strings.ReplaceAll(time.Duration(n).String(), "ns", ""), " ", ""))
}