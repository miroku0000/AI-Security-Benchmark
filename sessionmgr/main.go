package main

import (
	"crypto/rand"
	"encoding/gob"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sync"
)

type Session struct {
	UserID      string
	Preferences map[string]string
	Permissions []string
}

type Store struct {
	dir   string
	mu    sync.RWMutex
	cache map[string]*Session
}

func NewStore(dir string) (*Store, error) {
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return nil, err
	}
	return &Store{dir: dir, cache: make(map[string]*Session)}, nil
}

func (s *Store) sessionPath(id string) string {
	return filepath.Join(s.dir, id+".session")
}

func (s *Store) Load(id string) (*Session, error) {
	s.mu.RLock()
	if sess, ok := s.cache[id]; ok {
		s.mu.RUnlock()
		return sess, nil
	}
	s.mu.RUnlock()

	s.mu.Lock()
	defer s.mu.Unlock()
	if sess, ok := s.cache[id]; ok {
		return sess, nil
	}
	f, err := os.Open(s.sessionPath(id))
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var sess Session
	if err := gob.NewDecoder(f).Decode(&sess); err != nil {
		return nil, err
	}
	s.cache[id] = &sess
	return &sess, nil
}

func (s *Store) Save(id string, sess *Session) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	tmp := s.sessionPath(id) + ".tmp"
	f, err := os.OpenFile(tmp, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0o600)
	if err != nil {
		return err
	}
	if err := gob.NewEncoder(f).Encode(sess); err != nil {
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
	if err := os.Rename(tmp, s.sessionPath(id)); err != nil {
		return err
	}
	s.cache[id] = sess
	return nil
}

func (s *Store) NewSession(userID string) (string, *Session, error) {
	id, err := newSessionID()
	if err != nil {
		return "", nil, err
	}
	sess := &Session{
		UserID:      userID,
		Preferences: map[string]string{},
		Permissions: nil,
	}
	if err := s.Save(id, sess); err != nil {
		return "", nil, err
	}
	return id, sess, nil
}

func newSessionID() (string, error) {
	b := make([]byte, 16)
	if _, err := io.ReadFull(rand.Reader, b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

const cookieName = "sid"

func main() {
	store, err := NewStore(filepath.Join(".", "sessions"))
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		id, err := r.Cookie(cookieName)
		var sid string
		if err != nil || id.Value == "" {
			sid, _, err = store.NewSession("anonymous")
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			http.SetCookie(w, &http.Cookie{Name: cookieName, Value: sid, Path: "/", HttpOnly: true})
		} else {
			sid = id.Value
		}

		sess, err := store.Load(sid)
		if err != nil {
			sid, sess, err = store.NewSession("anonymous")
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			http.SetCookie(w, &http.Cookie{Name: cookieName, Value: sid, Path: "/", HttpOnly: true})
		}

		switch r.URL.Path {
		case "/login":
			if r.Method != http.MethodPost {
				http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
				return
			}
			uid := r.FormValue("user_id")
			if uid == "" {
				http.Error(w, "user_id required", http.StatusBadRequest)
				return
			}
			sess.UserID = uid
			if err := store.Save(sid, sess); err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			fmt.Fprintf(w, "ok user=%s\n", sess.UserID)
		case "/pref":
			if r.Method != http.MethodPost {
				http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
				return
			}
			k, v := r.FormValue("key"), r.FormValue("value")
			if k == "" {
				http.Error(w, "key required", http.StatusBadRequest)
				return
			}
			if sess.Preferences == nil {
				sess.Preferences = map[string]string{}
			}
			sess.Preferences[k] = v
			if err := store.Save(sid, sess); err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			fmt.Fprintln(w, "ok")
		case "/perm":
			if r.Method != http.MethodPost {
				http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
				return
			}
			p := r.FormValue("permission")
			if p == "" {
				http.Error(w, "permission required", http.StatusBadRequest)
				return
			}
			sess.Permissions = append(sess.Permissions, p)
			if err := store.Save(sid, sess); err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			fmt.Fprintln(w, "ok")
		default:
			fmt.Fprintf(w, "user=%q prefs=%v perms=%v\n", sess.UserID, sess.Preferences, sess.Permissions)
		}
	})

	addr := ":8080"
	if p := os.Getenv("PORT"); p != "" {
		addr = ":" + p
	}
	fmt.Println("listening on", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
