package main

import (
	"io"
	"log"
	"mime"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const uploadsDir = "uploads"

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/download", serveUpload)
	log.Fatal(http.ListenAndServe(":8080", mux))
}

func serveUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	name := r.URL.Query().Get("file")
	if name == "" {
		http.Error(w, "missing file parameter", http.StatusBadRequest)
		return
	}
	name = filepath.ToSlash(name)
	if name == "" || name == "." || strings.Contains(name, "..") || strings.HasPrefix(name, "/") {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	absUploads, err := filepath.Abs(uploadsDir)
	if err != nil {
		http.Error(w, "internal server error", http.StatusInternalServerError)
		return
	}
	full := filepath.Join(absUploads, filepath.FromSlash(name))
	absFile, err := filepath.Abs(full)
	if err != nil {
		http.Error(w, "internal server error", http.StatusInternalServerError)
		return
	}
	if absFile != absUploads && !strings.HasPrefix(absFile, absUploads+string(os.PathSeparator)) {
		http.Error(w, "forbidden", http.StatusForbidden)
		return
	}

	fi, err := os.Stat(absFile)
	if err != nil {
		if os.IsNotExist(err) {
			http.NotFound(w, r)
			return
		}
		http.Error(w, "internal server error", http.StatusInternalServerError)
		return
	}
	if fi.IsDir() {
		http.Error(w, "forbidden", http.StatusForbidden)
		return
	}

	ct := mime.TypeByExtension(filepath.Ext(absFile))
	if ct == "" {
		f, err := os.Open(absFile)
		if err != nil {
			http.Error(w, "internal server error", http.StatusInternalServerError)
			return
		}
		buf := make([]byte, 512)
		n, err := f.Read(buf)
		f.Close()
		if err != nil && err != io.EOF {
			http.Error(w, "internal server error", http.StatusInternalServerError)
			return
		}
		ct = http.DetectContentType(buf[:n])
	}

	w.Header().Set("Content-Type", ct)
	w.Header().Set("Content-Length", strconv.FormatInt(fi.Size(), 10))
	w.Header().Set("Content-Disposition", `inline; filename="`+filepath.Base(absFile)+`"`)

	if r.Method == http.MethodHead {
		w.WriteHeader(http.StatusOK)
		return
	}

	f, err := os.Open(absFile)
	if err != nil {
		http.Error(w, "internal server error", http.StatusInternalServerError)
		return
	}
	defer f.Close()

	w.WriteHeader(http.StatusOK)
	_, _ = io.Copy(w, f)
}
