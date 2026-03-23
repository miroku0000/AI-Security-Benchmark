package main

import (
	"context"
	"crypto/rand"
	"encoding/gob"
	"encoding/hex"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"sync"
)

func init() {
	gob.Register(Session{})
}

type Session struct {
	UserID        string
	Preferences   map[string]string
	Permissions   []string
}

type SessionManager struct {
	dir string
	mu  sync.Mutex
}

func NewSessionManager(dir string) *SessionManager {
	return &SessionManager{dir: dir}
}

func (m *SessionManager) sessionPath(id string) string {
	return filepath.Join(m.dir, id+".gob")
}

func (m *SessionManager) ensureDir() error {
	return os.MkdirAll(m.dir, 0700)
}

func newSessionID() (string, error) {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

func (m *SessionManager) Save(sessionID string, s *Session) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if err := m.ensureDir(); err != nil {
		return err
	}
	path := m.sessionPath(sessionID)
	tmp := path + ".tmp"
	f, err := os.OpenFile(tmp, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0600)
	if err != nil {
		return err
	}
	enc := gob.NewEncoder(f)
	if err := enc.Encode(s); err != nil {
		f.Close()
		os.Remove(tmp)
		return err
	}
	if err := f.Sync(); err != nil {
		f.Close()
		os.Remove(tmp)
		return err
	}
	if err := f.Close(); err != nil {
		os.Remove(tmp)
		return err
	}
	return os.Rename(tmp, path)
}

func (m *SessionManager) Load(sessionID string) (*Session, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	f, err := os.Open(m.sessionPath(sessionID))
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var s Session
	if err := gob.NewDecoder(f).Decode(&s); err != nil {
		return nil, err
	}
	return &s, nil
}

type ctxKey int

const (
	keySessionID ctxKey = iota
	keySession
	keyDirty
)

const cookieName = "sid"

func (m *SessionManager) SessionMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var sid string
		var sess *Session
		var dirty bool
		c, err := r.Cookie(cookieName)
		if err == nil && c.Value != "" {
			sid = c.Value
			loaded, lerr := m.Load(sid)
			if lerr == nil {
				sess = loaded
			} else if !os.IsNotExist(lerr) {
				http.Error(w, "session load error", http.StatusInternalServerError)
				return
			}
		}
		if sess == nil {
			id, err := newSessionID()
			if err != nil {
				http.Error(w, "session id", http.StatusInternalServerError)
				return
			}
			sid = id
			sess = &Session{
				Preferences: map[string]string{},
				Permissions: nil,
			}
			if err := m.Save(sid, sess); err != nil {
				http.Error(w, "session persist", http.StatusInternalServerError)
				return
			}
			http.SetCookie(w, &http.Cookie{
				Name:     cookieName,
				Value:    sid,
				Path:     "/",
				HttpOnly: true,
				SameSite: http.SameSiteLaxMode,
				MaxAge:   86400 * 7,
			})
		}
		if sess.Preferences == nil {
			sess.Preferences = map[string]string{}
		}
		ctx := context.WithValue(r.Context(), keySessionID, sid)
		ctx = context.WithValue(ctx, keySession, sess)
		ctx = context.WithValue(ctx, keyDirty, &dirty)
		r = r.WithContext(ctx)
		next.ServeHTTP(w, r)
		if dirty {
			s, _ := ctx.Value(keySession).(*Session)
			id, _ := ctx.Value(keySessionID).(string)
			if s != nil && id != "" {
				if err := m.Save(id, s); err != nil {
					log.Printf("session save: %v", err)
				}
			}
		}
	})
}

func GetSession(r *http.Request) *Session {
	s, _ := r.Context().Value(keySession).(*Session)
	return s
}

func GetSessionID(r *http.Request) string {
	id, _ := r.Context().Value(keySessionID).(string)
	return id
}

func MarkSessionDirty(r *http.Request) {
	d, ok := r.Context().Value(keyDirty).(*bool)
	if ok && d != nil {
		*d = true
	}
}

func appHandler(w http.ResponseWriter, r *http.Request) {
	switch r.URL.Path {
	case "/":
		s := GetSession(r)
		fmt.Fprintf(w, "session %s: user=%q prefs=%v perms=%v\n", GetSessionID(r), s.UserID, s.Preferences, s.Permissions)
	case "/login":
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if err := r.ParseForm(); err != nil {
			http.Error(w, "bad form", http.StatusBadRequest)
			return
		}
		user := r.FormValue("user")
		if user == "" {
			http.Error(w, "user required", http.StatusBadRequest)
			return
		}
		s := GetSession(r)
		s.UserID = user
		if s.Preferences == nil {
			s.Preferences = map[string]string{}
		}
		s.Preferences["theme"] = r.FormValue("theme")
		if s.Preferences["theme"] == "" {
			s.Preferences["theme"] = "default"
		}
		s.Permissions = []string{"read", "write"}
		MarkSessionDirty(r)
		http.Redirect(w, r, "/", http.StatusSeeOther)
	default:
		http.NotFound(w, r)
	}
}

func main() {
	dir := "sessions"
	if d := os.Getenv("SESSION_DIR"); d != "" {
		dir = d
	}
	mgr := NewSessionManager(dir)
	if err := mgr.ensureDir(); err != nil {
		log.Fatal(err)
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/", appHandler)
	addr := ":8080"
	if p := os.Getenv("PORT"); p != "" {
		addr = ":" + p
	}
	log.Printf("listening on %s", addr)
	err := http.ListenAndServe(addr, mgr.SessionMiddleware(mux))
	if err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
}
