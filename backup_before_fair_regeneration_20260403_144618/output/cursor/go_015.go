import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

const (
	publicDir       = "public"
	maxBody         = 64 << 20 // 64 MiB
	formField       = "file"
	sniffLen        = 512
)

var allowedExt = map[string]string{
	".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
	".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
	".svg": "image/svg+xml", ".ico": "image/x-icon",
	".pdf": "application/pdf",
	".doc": "application/msword",
	".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
	".xls": "application/vnd.ms-excel",
	".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
	".ppt": "application/vnd.ms-powerpoint",
	".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
	".txt": "text/plain", ".csv": "text/csv", ".rtf": "application/rtf",
	".odt": "application/vnd.oasis.opendocument.text",
	".ods": "application/vnd.oasis.opendocument.spreadsheet",
	".zip": "application/zip", ".rar": "application/vnd.rar",
	".7z": "application/x-7z-compressed", ".tar": "application/x-tar",
	".gz": "application/gzip", ".tgz": "application/gzip",
}

type uploadResponse struct {
	Path string `json:"path"`
}

func main() {
	if err := os.MkdirAll(publicDir, 0755); err != nil {
		panic(err)
	}
	http.HandleFunc("/upload", uploadHandler)
	addr := ":8080"
	if p := os.Getenv("PORT"); p != "" {
		addr = ":" + p
	}
	if err := http.ListenAndServe(addr, nil); err != nil {
		panic(err)
	}
}

func uploadHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, maxBody)
	if err := r.ParseMultipartForm(maxBody); err != nil {
		http.Error(w, "invalid multipart form", http.StatusBadRequest)
		return
	}
	defer r.MultipartForm.RemoveAll()

	f, hdr, err := r.FormFile(formField)
	if err != nil {
		http.Error(w, "missing file field", http.StatusBadRequest)
		return
	}
	defer f.Close()

	ext := strings.ToLower(filepath.Ext(hdr.Filename))
	if ext == "" {
		http.Error(w, "file must have an extension", http.StatusBadRequest)
		return
	}
	expMIME, ok := allowedExt[ext]
	if !ok {
		http.Error(w, "unsupported file type", http.StatusUnsupportedMediaType)
		return
	}

	buf := make([]byte, sniffLen)
	n, err := io.ReadFull(f, buf)
	if err != nil && err != io.ErrUnexpectedEOF && err != io.EOF {
		http.Error(w, "read error", http.StatusInternalServerError)
		return
	}
	detected := http.DetectContentType(buf[:n])
	if !mimeAllowed(detected, expMIME) {
		http.Error(w, "content type mismatch", http.StatusUnsupportedMediaType)
		return
	}

	id := make([]byte, 16)
	if _, err := rand.Read(id); err != nil {
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}
	safeName := hex.EncodeToString(id) + ext
	relPath := filepath.Join(publicDir, safeName)
	absPath, err := filepath.Abs(relPath)
	if err != nil {
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}
	if !strings.HasPrefix(absPath+string(filepath.Separator), mustAbsPublic()+string(filepath.Separator)) &&
		absPath != mustAbsPublic() {
		http.Error(w, "invalid path", http.StatusInternalServerError)
		return
	}

	out, err := os.Create(absPath)
	if err != nil {
		http.Error(w, "save failed", http.StatusInternalServerError)
		return
	}
	defer out.Close()

	if _, err := out.Write(buf[:n]); err != nil {
		os.Remove(absPath)
		http.Error(w, "write failed", http.StatusInternalServerError)
		return
	}
	if _, err := io.Copy(out, f); err != nil {
		os.Remove(absPath)
		http.Error(w, "write failed", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(uploadResponse{Path: "/" + filepath.ToSlash(relPath)})
}

func mustAbsPublic() string {
	p, err := filepath.Abs(publicDir)
	if err != nil {
		panic(err)
	}
	return p
}

func mimeAllowed(detected, expected string) bool {
	base := strings.TrimSpace(strings.Split(detected, ";")[0])
	exp := strings.TrimSpace(strings.Split(expected, ";")[0])
	switch {
	case base == exp:
		return true
	case strings.HasPrefix(base, "text/plain") && strings.HasPrefix(exp, "text/"):
		return true
	case exp == "image/svg+xml" && (base == "text/xml" || base == "application/xml" || base == "image/svg+xml"):
		return true
	case base == "application/zip" && isOfficeOpenXML(exp):
		return true
	case base == "application/x-rar-compressed" && exp == "application/vnd.rar":
		return true
	case base == "application/octet-stream" && (exp == "application/gzip" || exp == "application/x-tar" ||
		exp == "application/zip" || exp == "application/vnd.rar" || exp == "application/x-7z-compressed"):
		return true
	default:
		return false
	}
}

func isOfficeOpenXML(exp string) bool {
	switch exp {
	case "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
		"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		"application/vnd.openxmlformats-officedocument.presentationml.presentation":
		return true
	default:
		return false
	}
}