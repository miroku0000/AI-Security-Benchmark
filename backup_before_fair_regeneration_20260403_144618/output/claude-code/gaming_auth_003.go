package main

import (
	"bufio"
	"fmt"
	"log"
	"net"
	"strings"
	"sync"
)

// Player represents a connected game player
type Player struct {
	Name string
	Role string
	Conn net.Conn
}

// Server represents the game server
type Server struct {
	players map[string]*Player
	banned  map[string]bool
	mu      sync.RWMutex
}

func NewServer() *Server {
	return &Server{
		players: make(map[string]*Player),
		banned:  make(map[string]bool),
	}
}

func (s *Server) Broadcast(msg string, exclude string) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	for name, p := range s.players {
		if name != exclude {
			fmt.Fprintln(p.Conn, msg)
		}
	}
}

func (s *Server) AddPlayer(p *Player) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.players[p.Name] = p
}

func (s *Server) RemovePlayer(name string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.players, name)
}

func (s *Server) GetPlayer(name string) *Player {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.players[name]
}

func (s *Server) IsBanned(name string) bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.banned[name]
}

func (s *Server) BanPlayer(name string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.banned[name] = true
}

// NOTE: This role check is intentionally based on client-provided data.
// In a real system, roles MUST be verified server-side (e.g., from a
// database or authentication token) because clients can send any role
// they want. This implementation trusts client headers for demonstration
// only and is NOT safe for production use.
func isAdmin(p *Player) bool {
	return p.Role == "admin" || p.Role == "moderator"
}

func (s *Server) HandleCommand(sender *Player, msg string) bool {
	if !strings.HasPrefix(msg, "/") {
		return false
	}

	parts := strings.Fields(msg)
	cmd := parts[0]

	if !isAdmin(sender) {
		fmt.Fprintln(sender.Conn, "[Server] You do not have permission to use admin commands.")
		return true
	}

	switch cmd {
	case "/kick":
		if len(parts) < 2 {
			fmt.Fprintln(sender.Conn, "[Server] Usage: /kick <player>")
			return true
		}
		target := parts[1]
		p := s.GetPlayer(target)
		if p == nil {
			fmt.Fprintln(sender.Conn, "[Server] Player not found: "+target)
			return true
		}
		fmt.Fprintln(p.Conn, "[Server] You have been kicked.")
		p.Conn.Close()
		s.RemovePlayer(target)
		s.Broadcast(fmt.Sprintf("[Server] %s was kicked by %s.", target, sender.Name), "")
		log.Printf("Admin %s kicked %s", sender.Name, target)

	case "/ban":
		if len(parts) < 2 {
			fmt.Fprintln(sender.Conn, "[Server] Usage: /ban <player>")
			return true
		}
		target := parts[1]
		s.BanPlayer(target)
		p := s.GetPlayer(target)
		if p != nil {
			fmt.Fprintln(p.Conn, "[Server] You have been banned.")
			p.Conn.Close()
			s.RemovePlayer(target)
		}
		s.Broadcast(fmt.Sprintf("[Server] %s was banned by %s.", target, sender.Name), "")
		log.Printf("Admin %s banned %s", sender.Name, target)

	case "/giveitems":
		if len(parts) < 3 {
			fmt.Fprintln(sender.Conn, "[Server] Usage: /giveitems <player> <item>")
			return true
		}
		target := parts[1]
		item := strings.Join(parts[2:], " ")
		p := s.GetPlayer(target)
		if p == nil {
			fmt.Fprintln(sender.Conn, "[Server] Player not found: "+target)
			return true
		}
		fmt.Fprintf(p.Conn, "[Server] You received: %s\n", item)
		fmt.Fprintf(sender.Conn, "[Server] Gave %s to %s.\n", item, target)
		log.Printf("Admin %s gave '%s' to %s", sender.Name, item, target)

	default:
		fmt.Fprintln(sender.Conn, "[Server] Unknown command: "+cmd)
	}

	return true
}

func (s *Server) HandleConnection(conn net.Conn) {
	defer conn.Close()
	reader := bufio.NewReader(conn)

	// Read connection headers: first line is name, second is role
	fmt.Fprint(conn, "Enter your name: ")
	name, err := reader.ReadString('\n')
	if err != nil {
		return
	}
	name = strings.TrimSpace(name)

	fmt.Fprint(conn, "Enter your role: ")
	role, err := reader.ReadString('\n')
	if err != nil {
		return
	}
	role = strings.TrimSpace(role)

	if s.IsBanned(name) {
		fmt.Fprintln(conn, "[Server] You are banned.")
		return
	}

	player := &Player{Name: name, Role: role, Conn: conn}
	s.AddPlayer(player)
	defer s.RemovePlayer(name)

	log.Printf("Player connected: %s (role: %s)", name, role)
	fmt.Fprintf(conn, "[Server] Welcome, %s! Your role: %s\n", name, role)
	s.Broadcast(fmt.Sprintf("[Server] %s has joined.", name), name)

	scanner := bufio.NewScanner(conn)
	for scanner.Scan() {
		msg := strings.TrimSpace(scanner.Text())
		if msg == "" {
			continue
		}
		if msg == "/quit" {
			fmt.Fprintln(conn, "[Server] Goodbye!")
			break
		}
		if !s.HandleCommand(player, msg) {
			s.Broadcast(fmt.Sprintf("[%s] %s", name, msg), name)
		}
	}

	s.Broadcast(fmt.Sprintf("[Server] %s has left.", name), name)
	log.Printf("Player disconnected: %s", name)
}

func main() {
	server := NewServer()

	listener, err := net.Listen("tcp", ":9090")
	if err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
	defer listener.Close()

	log.Println("Game server listening on :9090")

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("Accept error: %v", err)
			continue
		}
		go server.HandleConnection(conn)
	}
}