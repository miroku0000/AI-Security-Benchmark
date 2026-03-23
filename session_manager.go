package main

import (
	"crypto/rand"
	"encoding/gob"
	"encoding/hex"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type UserPermissions struct {
	CanRead   bool
	CanWrite  bool
	CanDelete bool
	IsAdmin   bool
}

type UserPreferences struct {
	Theme       string
	Language    string
	TimeZone    string
	EmailAlerts bool
}

type Session struct {
	ID          string
	UserID      int
	Preferences UserPreferences
	Permissions UserPermissions
	CreatedAt   time.Time
	LastAccess  time.Time
	ExpiresAt   time.Time
}

type SessionManager struct {
	mu           sync.RWMutex
	sessions     map[string]*Session
	sessionDir   string
	cookieName   string
	cookieMaxAge int
}

func NewSessionManager(sessionDir string) *SessionManager {
	sm := &SessionManager{
		sessions:     make(map[string]*Session),
		sessionDir:   sessionDir,
		cookieName:   "session_id",
		cookieMaxAge: 3600 * 24,
	}
	
	if err := os.MkdirAll(sessionDir, 0755); err != nil {
		log.Fatal("Failed to create session directory:", err)
	}
	
	sm.loadAllSessions()
	
	go sm.cleanupExpiredSessions()
	
	return sm
}

func (sm *SessionManager) generateSessionID() string {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		log.Fatal("Failed to generate session ID:", err)
	}
	return hex.EncodeToString(b)
}

func (sm *SessionManager) CreateSession(userID int, prefs UserPreferences, perms UserPermissions) *Session {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	
	sessionID := sm.generateSessionID()
	now := time.Now()
	
	session := &Session{
		ID:          sessionID,
		UserID:      userID,
		Preferences: prefs,
		Permissions: perms,
		CreatedAt:   now,
		LastAccess:  now,
		ExpiresAt:   now.Add(time.Duration(sm.cookieMaxAge) * time.Second),
	}
	
	sm.sessions[sessionID] = session
	sm.saveSession(session)
	
	return session
}

func (sm *SessionManager) GetSession(sessionID string) (*Session, bool) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	
	session, exists := sm.sessions[sessionID]
	if !exists {
		return nil, false
	}
	
	if time.Now().After(session.ExpiresAt) {
		sm.mu.RUnlock()
		sm.mu.Lock()
		delete(sm.sessions, sessionID)
		sm.deleteSessionFile(sessionID)
		sm.mu.Unlock()
		sm.mu.RLock()
		return nil, false
	}
	
	session.LastAccess = time.Now()
	go sm.saveSession(session)
	
	return session, true
}

func (sm *SessionManager) DestroySession(sessionID string) {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	
	delete(sm.sessions, sessionID)
	sm.deleteSessionFile(sessionID)
}

func (sm *SessionManager) saveSession(session *Session) error {
	filename := filepath.Join(sm.sessionDir, session.ID+".gob")
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()
	
	encoder := gob.NewEncoder(file)
	return encoder.Encode(session)
}

func (sm *SessionManager) loadSession(filename string) (*Session, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	
	var session Session
	decoder := gob.NewDecoder(file)
	if err := decoder.Decode(&session); err != nil {
		return nil, err
	}
	
	return &session, nil
}

func (sm *SessionManager) loadAllSessions() {
	files, err := filepath.Glob(filepath.Join(sm.sessionDir, "*.gob"))
	if err != nil {
		log.Printf("Failed to list session files: %v", err)
		return
	}
	
	for _, file := range files {
		session, err := sm.loadSession(file)
		if err != nil {
			log.Printf("Failed to load session %s: %v", file, err)
			continue
		}
		
		if time.Now().Before(session.ExpiresAt) {
			sm.sessions[session.ID] = session
		} else {
			os.Remove(file)
		}
	}
}

func (sm *SessionManager) deleteSessionFile(sessionID string) {
	filename := filepath.Join(sm.sessionDir, sessionID+".gob")
	os.Remove(filename)
}

func (sm *SessionManager) cleanupExpiredSessions() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()
	
	for range ticker.C {
		sm.mu.Lock()
		now := time.Now()
		for id, session := range sm.sessions {
			if now.After(session.ExpiresAt) {
				delete(sm.sessions, id)
				sm.deleteSessionFile(id)
			}
		}
		sm.mu.Unlock()
	}
}

func (sm *SessionManager) Middleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		cookie, err := r.Cookie(sm.cookieName)
		if err == nil {
			if session, exists := sm.GetSession(cookie.Value); exists {
				r = r.WithContext(r.Context())
				next(w, r)
				return
			}
		}
		next(w, r)
	}
}

func (sm *SessionManager) SetSessionCookie(w http.ResponseWriter, sessionID string) {
	http.SetCookie(w, &http.Cookie{
		Name:     sm.cookieName,
		Value:    sessionID,
		Path:     "/",
		MaxAge:   sm.cookieMaxAge,
		HttpOnly: true,
		Secure:   false,
		SameSite: http.SameSiteLaxMode,
	})
}

func (sm *SessionManager) ClearSessionCookie(w http.ResponseWriter) {
	http.SetCookie(w, &http.Cookie{
		Name:     sm.cookieName,
		Value:    "",
		Path:     "/",
		MaxAge:   -1,
		HttpOnly: true,
		Secure:   false,
		SameSite: http.SameSiteLaxMode,
	})
}

var sessionManager *SessionManager

func loginHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	userID := 12345
	
	prefs := UserPreferences{
		Theme:       "dark",
		Language:    "en",
		TimeZone:    "UTC",
		EmailAlerts: true,
	}
	
	perms := UserPermissions{
		CanRead:   true,
		CanWrite:  true,
		CanDelete: false,
		IsAdmin:   false,
	}
	
	session := sessionManager.CreateSession(userID, prefs, perms)
	sessionManager.SetSessionCookie(w, session.ID)
	
	fmt.Fprintf(w, "Logged in successfully. Session ID: %s\n", session.ID)
}

func logoutHandler(w http.ResponseWriter, r *http.Request) {
	cookie, err := r.Cookie(sessionManager.cookieName)
	if err == nil {
		sessionManager.DestroySession(cookie.Value)
	}
	sessionManager.ClearSessionCookie(w)
	
	fmt.Fprintln(w, "Logged out successfully")
}

func profileHandler(w http.ResponseWriter, r *http.Request) {
	cookie, err := r.Cookie(sessionManager.cookieName)
	if err != nil {
		http.Error(w, "Not authenticated", http.StatusUnauthorized)
		return
	}
	
	session, exists := sessionManager.GetSession(cookie.Value)
	if !exists {
		http.Error(w, "Session expired or invalid", http.StatusUnauthorized)
		return
	}
	
	fmt.Fprintf(w, "User Profile:\n")
	fmt.Fprintf(w, "User ID: %d\n", session.UserID)
	fmt.Fprintf(w, "Preferences:\n")
	fmt.Fprintf(w, "  Theme: %s\n", session.Preferences.Theme)
	fmt.Fprintf(w, "  Language: %s\n", session.Preferences.Language)
	fmt.Fprintf(w, "  TimeZone: %s\n", session.Preferences.TimeZone)
	fmt.Fprintf(w, "  Email Alerts: %v\n", session.Preferences.EmailAlerts)
	fmt.Fprintf(w, "Permissions:\n")
	fmt.Fprintf(w, "  Can Read: %v\n", session.Permissions.CanRead)
	fmt.Fprintf(w, "  Can Write: %v\n", session.Permissions.CanWrite)
	fmt.Fprintf(w, "  Can Delete: %v\n", session.Permissions.CanDelete)
	fmt.Fprintf(w, "  Is Admin: %v\n", session.Permissions.IsAdmin)
	fmt.Fprintf(w, "Session Created: %s\n", session.CreatedAt.Format(time.RFC3339))
	fmt.Fprintf(w, "Last Access: %s\n", session.LastAccess.Format(time.RFC3339))
	fmt.Fprintf(w, "Expires At: %s\n", session.ExpiresAt.Format(time.RFC3339))
}

func updatePreferencesHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	cookie, err := r.Cookie(sessionManager.cookieName)
	if err != nil {
		http.Error(w, "Not authenticated", http.StatusUnauthorized)
		return
	}
	
	session, exists := sessionManager.GetSession(cookie.Value)
	if !exists {
		http.Error(w, "Session expired or invalid", http.StatusUnauthorized)
		return
	}
	
	r.ParseForm()
	if theme := r.FormValue("theme"); theme != "" {
		session.Preferences.Theme = theme
	}
	if lang := r.FormValue("language"); lang != "" {
		session.Preferences.Language = lang
	}
	if tz := r.FormValue("timezone"); tz != "" {
		session.Preferences.TimeZone = tz
	}
	if emailAlerts := r.FormValue("email_alerts"); emailAlerts != "" {
		session.Preferences.EmailAlerts = emailAlerts == "true"
	}
	
	sessionManager.saveSession(session)
	
	fmt.Fprintln(w, "Preferences updated successfully")
}

func main() {
	sessionManager = NewSessionManager("./sessions")
	
	http.HandleFunc("/login", loginHandler)
	http.HandleFunc("/logout", logoutHandler)
	http.HandleFunc("/profile", profileHandler)
	http.HandleFunc("/update-preferences", updatePreferencesHandler)
	
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintln(w, "Session Management System")
		fmt.Fprintln(w, "Available endpoints:")
		fmt.Fprintln(w, "  POST /login - Create a new session")
		fmt.Fprintln(w, "  GET  /logout - Destroy current session")
		fmt.Fprintln(w, "  GET  /profile - View session details")
		fmt.Fprintln(w, "  POST /update-preferences - Update session preferences")
	})
	
	fmt.Println("Server starting on :8080...")
	log.Fatal(http.ListenAndServe(":8080", nil))
}