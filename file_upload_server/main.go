package main

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

var allowedExt = map[string]bool{
	".jpg": true, ".jpeg": true, ".png": true, ".gif": true, ".webp": true, ".svg": true, ".bmp": true, ".ico": true,
	".tif": true, ".tiff": true, ".heic": true, ".avif": true,
	".pdf": true, ".doc": true, ".docx": true, ".xls": true, ".xlsx": true, ".ppt": true, ".pptx": true,
	".txt": true, ".csv": true, ".rtf": true, ".odt": true, ".ods": true, ".odp": true, ".json": true, ".md": true, ".xml": true,
	".zip": true, ".rar": true, ".7z": true, ".tar": true, ".gz": true, ".tgz": true, ".bz2": true, ".xz": true,
}

func main() {
	publicDir := "public"
	if err := os.MkdirAll(publicDir, 0755); err != nil {
		panic(err)
	}
	http.HandleFunc("/upload", uploadHandler(publicDir))
	http.Handle("/public/", http.StripPrefix("/public/", http.FileServer(http.Dir(publicDir))))
	if err := http.ListenAndServe(":8080", nil); err != nil {
		panic(err)
	}
}

func uploadHandler(publicDir string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		const maxBytes = 64 << 20
		r.Body = http.MaxBytesReader(w, r.Body, maxBytes)
		if err := r.ParseMultipartForm(maxBytes); err != nil {
			http.Error(w, "invalid multipart form", http.StatusBadRequest)
			return
		}
		defer func() {
			if r.MultipartForm != nil {
				_ = r.MultipartForm.RemoveAll()
			}
		}()
		file, header, err := r.FormFile("file")
		if err != nil {
			http.Error(w, "missing file field", http.StatusBadRequest)
			return
		}
		defer file.Close()
		ext := strings.ToLower(filepath.Ext(header.Filename))
		if ext == "" || !allowedExt[ext] {
			http.Error(w, "unsupported file type", http.StatusBadRequest)
			return
		}
		base := strings.TrimSuffix(filepath.Base(header.Filename), ext)
		base = sanitizeFilename(base)
		if base == "" {
			base = "upload"
		}
		saveName := fmt.Sprintf("%s_%s%s", base, randomID(8), ext)
		savePath := filepath.Join(publicDir, saveName)
		dst, err := os.OpenFile(savePath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0644)
		if err != nil {
			http.Error(w, "failed to create file", http.StatusInternalServerError)
			return
		}
		defer dst.Close()
		if _, err := io.Copy(dst, file); err != nil {
			_ = os.Remove(savePath)
			http.Error(w, "failed to save file", http.StatusInternalServerError)
			return
		}
		rel := "/public/" + filepath.ToSlash(saveName)
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		_ = json.NewEncoder(w).Encode(map[string]string{"path": rel})
	}
}

func sanitizeFilename(s string) string {
	var b strings.Builder
	for _, r := range s {
		switch {
		case r >= 'a' && r <= 'z', r >= 'A' && r <= 'Z', r >= '0' && r <= '9', r == '-', r == '_', r == '.':
			b.WriteRune(r)
		}
	}
	out := b.String()
	if len(out) > 80 {
		out = out[:80]
	}
	return out
}

func randomID(n int) string {
	b := make([]byte, n)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	return hex.EncodeToString(b)
}
