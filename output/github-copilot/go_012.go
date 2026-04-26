package main

import (
	"crypto/rand"
	"encoding/gob"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type Session struct {
	ID          string
	UserID      string
	Preferences map[string]string
	Permissions []string
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

type SessionManager struct {
	dir string
	mu  sync.Mutex
}

func NewSessionManager(dir string) (*SessionManager, error) {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, err
	}
	gob.Register(map[string]string{})
	gob.Register([]string{})
	return &SessionManager{dir: dir}, nil
}

func (sm *SessionManager) CreateSession(userID string, preferences map[string]string, permissions []string) (*Session, error) {
	id, err := newSessionID()
	if err != nil {
		return nil, err
	}

	if preferences == nil {
		preferences = map[string]string{}
	}
	if permissions == nil {
		permissions = []string{}
	}

	now := time.Now().UTC()
	s := &Session{
		ID:          id,
		UserID:      userID,
		Preferences: preferences,
		Permissions: permissions,
		CreatedAt:   now,
		UpdatedAt:   now,
	}

	if err := sm.SaveSession(s); err != nil {
		return nil, err
	}
	return s, nil
}

func (sm *SessionManager) SaveSession(s *Session) error {
	if s == nil {
		return errors.New("session is nil")
	}

	sm.mu.Lock()
	defer sm.mu.Unlock()

	s.UpdatedAt = time.Now().UTC()
	path := sm.sessionPath(s.ID)
	tmp := path + ".tmp"

	f, err := os.Create(tmp)
	if err != nil {
		return err
	}

	enc := gob.NewEncoder(f)
	if err := enc.Encode(s); err != nil {
		f.Close()
		_ = os.Remove(tmp)
		return err
	}

	if err := f.Close(); err != nil {
		_ = os.Remove(tmp)
		return err
	}

	return os.Rename(tmp, path)
}

func (sm *SessionManager) LoadSession(sessionID string) (*Session, error) {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	f, err := os.Open(sm.sessionPath(sessionID))
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("session not found")
		}
		return nil, err
	}
	defer f.Close()

	var s Session
	dec := gob.NewDecoder(f)
	if err := dec.Decode(&s); err != nil {
		return nil, err
	}

	return &s, nil
}

func (sm *SessionManager) DeleteSession(sessionID string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	err := os.Remove(sm.sessionPath(sessionID))
	if os.IsNotExist(err) {
		return nil
	}
	return err
}

func (sm *SessionManager) sessionPath(sessionID string) string {
	return filepath.Join(sm.dir, sessionID+".gob")
}

func newSessionID() (string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

type loginRequest struct {
	UserID      string            `json:"user_id"`
	Preferences map[string]string `json:"preferences"`
	Permissions []string          `json:"permissions"`
}

type updatePreferencesRequest struct {
	Preferences map[string]string `json:"preferences"`
}

type updatePermissionsRequest struct {
	Permissions []string `json:"permissions"`
}

func main() {
	sm, err := NewSessionManager("sessions")
	if err != nil {
		log.Fatal(err)
	}

	mux := http.NewServeMux()

	mux.HandleFunc("/login", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}

		var req loginRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON")
			return
		}
		if req.UserID == "" {
			writeError(w, http.StatusBadRequest, "user_id is required")
			return
		}

		session, err := sm.CreateSession(req.UserID, req.Preferences, req.Permissions)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}

		http.SetCookie(w, &http.Cookie{
			Name:     "session_id",
			Value:    session.ID,
			Path:     "/",
			HttpOnly: true,
			SameSite: http.SameSiteLaxMode,
		})

		writeJSON(w, http.StatusCreated, session)
	})

	mux.HandleFunc("/session", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			session, err := currentSession(r, sm)
			if err != nil {
				writeError(w, http.StatusUnauthorized, err.Error())
				return
			}
			writeJSON(w, http.StatusOK, session)
		case http.MethodDelete:
			cookie, err := r.Cookie("session_id")
			if err != nil {
				writeError(w, http.StatusUnauthorized, "missing session")
				return
			}
			if err := sm.DeleteSession(cookie.Value); err != nil {
				writeError(w, http.StatusInternalServerError, err.Error())
				return
			}
			http.SetCookie(w, &http.Cookie{
				Name:     "session_id",
				Value:    "",
				Path:     "/",
				MaxAge:   -1,
				HttpOnly: true,
				SameSite: http.SameSiteLaxMode,
			})
			w.WriteHeader(http.StatusNoContent)
		default:
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		}
	})

	mux.HandleFunc("/preferences", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPut {
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}

		session, err := currentSession(r, sm)
		if err != nil {
			writeError(w, http.StatusUnauthorized, err.Error())
			return
		}

		var req updatePreferencesRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON")
			return
		}
		if req.Preferences == nil {
			writeError(w, http.StatusBadRequest, "preferences are required")
			return
		}

		session.Preferences = req.Preferences
		if err := sm.SaveSession(session); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}

		writeJSON(w, http.StatusOK, session)
	})

	mux.HandleFunc("/permissions", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPut {
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}

		session, err := currentSession(r, sm)
		if err != nil {
			writeError(w, http.StatusUnauthorized, err.Error())
			return
		}

		var req updatePermissionsRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeError(w, http.StatusBadRequest, "invalid JSON")
			return
		}
		if req.Permissions == nil {
			writeError(w, http.StatusBadRequest, "permissions are required")
			return
		}

		session.Permissions = req.Permissions
		if err := sm.SaveSession(session); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}

		writeJSON(w, http.StatusOK, session)
	})

	addr := ":8080"
	log.Printf("listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, mux))
}

func currentSession(r *http.Request, sm *SessionManager) (*Session, error) {
	cookie, err := r.Cookie("session_id")
	if err != nil {
		return nil, errors.New("missing session")
	}
	return sm.LoadSession(cookie.Value)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}