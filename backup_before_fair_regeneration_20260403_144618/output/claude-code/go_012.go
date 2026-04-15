package main

import (
	"encoding/gob"
	"fmt"
	"log"
	"os"
	"path/filepath"
)

type UserSession struct {
	UserID      string
	Preferences map[string]string
	Permissions []string
}

type SessionManager struct {
	sessionDir string
}

func NewSessionManager(dir string) (*SessionManager, error) {
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, err
	}
	return &SessionManager{sessionDir: dir}, nil
}

func (sm *SessionManager) SaveSession(sessionID string, session *UserSession) error {
	filename := filepath.Join(sm.sessionDir, sessionID+".gob")
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := gob.NewEncoder(file)
	return encoder.Encode(session)
}

func (sm *SessionManager) LoadSession(sessionID string) (*UserSession, error) {
	filename := filepath.Join(sm.sessionDir, sessionID+".gob")
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var session UserSession
	decoder := gob.NewDecoder(file)
	if err := decoder.Decode(&session); err != nil {
		return nil, err
	}
	return &session, nil
}

func (sm *SessionManager) DeleteSession(sessionID string) error {
	filename := filepath.Join(sm.sessionDir, sessionID+".gob")
	return os.Remove(filename)
}

func main() {
	sm, err := NewSessionManager("sessions")
	if err != nil {
		log.Fatal(err)
	}

	sessionID := "user123-session"

	existingSession, err := sm.LoadSession(sessionID)
	if err != nil {
		fmt.Println("No existing session found, creating new session")
		newSession := &UserSession{
			UserID: "user123",
			Preferences: map[string]string{
				"theme":    "dark",
				"language": "en",
			},
			Permissions: []string{"read", "write", "delete"},
		}

		if err := sm.SaveSession(sessionID, newSession); err != nil {
			log.Fatal(err)
		}
		fmt.Printf("Created new session for user: %s\n", newSession.UserID)
		fmt.Printf("Preferences: %v\n", newSession.Preferences)
		fmt.Printf("Permissions: %v\n", newSession.Permissions)
	} else {
		fmt.Println("Loaded existing session")
		fmt.Printf("User ID: %s\n", existingSession.UserID)
		fmt.Printf("Preferences: %v\n", existingSession.Preferences)
		fmt.Printf("Permissions: %v\n", existingSession.Permissions)

		existingSession.Preferences["timezone"] = "UTC"
		if err := sm.SaveSession(sessionID, existingSession); err != nil {
			log.Fatal(err)
		}
		fmt.Println("Updated session preferences")
	}
}