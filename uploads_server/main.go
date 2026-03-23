package main

import (
	"io"
	"log"
	"mime"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

const uploadsDir = "uploads"

func main() {
	http.HandleFunc("/uploads/", serveUpload)

	addr := ":8080"
	log.Printf("listening on %s", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatal(err)
	}
}

func serveUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	rel := strings.TrimPrefix(r.URL.Path, "/uploads/")
	rel = strings.Trim(rel, "/")
	if rel == "" || strings.Contains(rel, "..") || strings.ContainsAny(rel, `/\`) {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	full := filepath.Join(uploadsDir, filepath.Clean(rel))
	absUploads, err := filepath.Abs(uploadsDir)
	if err != nil {
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}
	absFull, err := filepath.Abs(full)
	if err != nil {
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}
	if !strings.HasPrefix(absFull, absUploads+string(os.PathSeparator)) && absFull != absUploads {
		http.Error(w, "forbidden", http.StatusForbidden)
		return
	}

	f, err := os.Open(absFull)
	if err != nil {
		if os.IsNotExist(err) {
			http.NotFound(w, r)
			return
		}
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}
	defer f.Close()

	st, err := f.Stat()
	if err != nil {
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}
	if st.IsDir() {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}

	ctype := mime.TypeByExtension(filepath.Ext(absFull))
	if ctype == "" {
		buf := make([]byte, 512)
		n, _ := io.ReadFull(f, buf)
		ctype = http.DetectContentType(buf[:n])
		if _, err := f.Seek(0, io.SeekStart); err != nil {
			http.Error(w, "internal error", http.StatusInternalServerError)
			return
		}
	} else {
		if _, err := f.Seek(0, io.SeekStart); err != nil {
			http.Error(w, "internal error", http.StatusInternalServerError)
			return
		}
	}

	w.Header().Set("Content-Type", ctype)
	w.Header().Set("Content-Disposition", "inline; filename=\""+filepath.Base(absFull)+"\"")
	http.ServeContent(w, r, filepath.Base(absFull), st.ModTime(), f)
}
