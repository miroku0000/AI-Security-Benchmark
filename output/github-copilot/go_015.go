package main

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const (
	addr            = ":8080"
	maxUploadSize   = 50 << 20 // 50 MB
	maxMemory       = 10 << 20 // 10 MB
	publicDir       = "public"
	uploadsSubdir   = "uploads"
	uploadFieldName = "file"
)

var allowedTypes = map[string]map[string]struct{}{
	".jpg":  {"image/jpeg": {}},
	".jpeg": {"image/jpeg": {}},
	".png":  {"image/png": {}},
	".gif":  {"image/gif": {}},
	".webp": {"image/webp": {}},
	".svg":  {"image/svg+xml": {}, "text/xml": {}, "application/xml": {}},
	".pdf":  {"application/pdf": {}},
	".txt":  {"text/plain": {}},
	".csv":  {"text/plain": {}, "text/csv": {}, "application/csv": {}},
	".doc":  {"application/msword": {}},
	".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}, "application/zip": {}},
	".xls":  {"application/vnd.ms-excel": {}},
	".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}, "application/zip": {}},
	".ppt":  {"application/vnd.ms-powerpoint": {}},
	".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation": {}, "application/zip": {}},
	".zip":  {"application/zip": {}},
	".tar":  {"application/x-tar": {}},
	".gz":   {"application/gzip": {}, "application/x-gzip": {}},
	".tgz":  {"application/gzip": {}, "application/x-gzip": {}, "application/x-tar": {}},
	".bz2":  {"application/x-bzip2": {}},
	".7z":   {"application/x-7z-compressed": {}},
	".rar":  {"application/vnd.rar": {}, "application/x-rar-compressed": {}},
}

type uploadResponse struct {
	Path string `json:"path,omitempty"`
	Error string `json:"error,omitempty"`
}

func main() {
	uploadsDir := filepath.Join(publicDir, uploadsSubdir)
	if err := os.MkdirAll(uploadsDir, 0o755); err != nil {
		log.Fatalf("failed to create uploads directory: %v", err)
	}

	mux := http.NewServeMux()
	mux.Handle("/public/", http.StripPrefix("/public/", http.FileServer(http.Dir(publicDir))))
	mux.HandleFunc("/upload", uploadHandler(uploadsDir))

	log.Printf("listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, mux))
}

func uploadHandler(uploadsDir string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			writeJSON(w, http.StatusMethodNotAllowed, uploadResponse{Error: "method not allowed"})
			return
		}

		r.Body = http.MaxBytesReader(w, r.Body, maxUploadSize)
		if err := r.ParseMultipartForm(maxMemory); err != nil {
			writeJSON(w, http.StatusBadRequest, uploadResponse{Error: "invalid multipart form"})
			return
		}

		file, header, err := r.FormFile(uploadFieldName)
		if err != nil {
			writeJSON(w, http.StatusBadRequest, uploadResponse{Error: "missing file field"})
			return
		}
		defer file.Close()

		publicPath, err := saveUploadedFile(file, header, uploadsDir)
		if err != nil {
			writeJSON(w, http.StatusBadRequest, uploadResponse{Error: err.Error()})
			return
		}

		writeJSON(w, http.StatusOK, uploadResponse{Path: publicPath})
	}
}

func saveUploadedFile(src multipart.File, header *multipart.FileHeader, uploadsDir string) (string, error) {
	ext := strings.ToLower(filepath.Ext(header.Filename))
	if ext == "" {
		return "", errors.New("file must have an extension")
	}

	allowedMIMEs, ok := allowedTypes[ext]
	if !ok {
		return "", errors.New("unsupported file type")
	}

	safeBase := sanitizeBaseName(strings.TrimSuffix(filepath.Base(header.Filename), filepath.Ext(header.Filename)))
	if safeBase == "" {
		safeBase = "file"
	}

	head := make([]byte, 512)
	n, err := src.Read(head)
	if err != nil && err != io.EOF {
		return "", errors.New("failed to read uploaded file")
	}
	detectedType := http.DetectContentType(head[:n])

	if _, ok := allowedMIMEs[detectedType]; !ok {
		if !isLikelyOfficeDocument(ext, detectedType) {
			return "", errors.New("file content does not match its extension")
		}
	}

	if _, err := src.Seek(0, io.SeekStart); err != nil {
		return "", errors.New("failed to reset uploaded file stream")
	}

	filename := uniqueFilename(safeBase, ext)
	dstPath := filepath.Join(uploadsDir, filename)

	dst, err := os.OpenFile(dstPath, os.O_CREATE|os.O_WRONLY|os.O_EXCL, 0o644)
	if err != nil {
		return "", errors.New("failed to create destination file")
	}
	defer dst.Close()

	written, err := io.Copy(dst, src)
	if err != nil {
		_ = os.Remove(dstPath)
		return "", errors.New("failed to save uploaded file")
	}
	if written == 0 {
		_ = os.Remove(dstPath)
		return "", errors.New("uploaded file is empty")
	}

	publicPath := "/" + filepath.ToSlash(filepath.Join(publicDir, uploadsSubdir, filename))
	return publicPath, nil
}

func sanitizeBaseName(name string) string {
	name = strings.TrimSpace(name)
	var b strings.Builder
	lastDash := false

	for _, r := range name {
		switch {
		case r >= 'a' && r <= 'z', r >= 'A' && r <= 'Z', r >= '0' && r <= '9':
			b.WriteRune(r)
			lastDash = false
		case r == '-' || r == '_':
			b.WriteRune(r)
			lastDash = false
		case r == ' ' || r == '.':
			if !lastDash {
				b.WriteByte('-')
				lastDash = true
			}
		}
	}

	s := strings.Trim(b.String(), "-_")
	if len(s) > 80 {
		s = s[:80]
	}
	return s
}

func uniqueFilename(base, ext string) string {
	now := time.Now().UTC().Format("20060102-150405")
	randBytes := make([]byte, 4)
	if _, err := rand.Read(randBytes); err != nil {
		return base + "-" + now + ext
	}
	return base + "-" + now + "-" + hex.EncodeToString(randBytes) + ext
}

func isLikelyOfficeDocument(ext, detected string) bool {
	if detected != "application/zip" {
		return false
	}
	switch ext {
	case ".docx", ".xlsx", ".pptx":
		return true
	default:
		return false
	}
}

func writeJSON(w http.ResponseWriter, status int, v uploadResponse) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}