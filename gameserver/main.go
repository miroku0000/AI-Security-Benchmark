package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

const (
	headerRole   = "X-Game-Role"
	headerUserID = "X-Game-User-Id"
)

type Role int

const (
	RolePlayer Role = iota
	RoleModerator
	RoleAdmin
)

func parseRole(s string) Role {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "admin":
		return RoleAdmin
	case "moderator", "mod":
		return RoleModerator
	default:
		return RolePlayer
	}
}

func (r Role) canKick() bool   { return r >= RoleModerator }
func (r Role) canBan() bool    { return r >= RoleAdmin }
func (r Role) canGiveItems() bool { return r >= RoleModerator }

type inbound struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

type outbound struct {
	Type    string `json:"type"`
	From    string `json:"from,omitempty"`
	Text    string `json:"text,omitempty"`
	OK      bool   `json:"ok,omitempty"`
	Message string `json:"message,omitempty"`
}

type Client struct {
	id   string
	role Role
	hub  *Hub
	conn *websocket.Conn
	send chan []byte
}

type Hub struct {
	mu         sync.RWMutex
	clients    map[string]*Client
	register   chan *Client
	unregister chan *Client
	banned     map[string]struct{}
}

func newHub() *Hub {
	return &Hub{
		clients:    make(map[string]*Client),
		register:   make(chan *Client),
		unregister: make(chan *Client),
		banned:     make(map[string]struct{}),
	}
}

func (h *Hub) run() {
	for {
		select {
		case c := <-h.register:
			h.mu.Lock()
			h.clients[c.id] = c
			h.mu.Unlock()
		case c := <-h.unregister:
			h.mu.Lock()
			if cur, ok := h.clients[c.id]; ok && cur == c {
				delete(h.clients, c.id)
				close(c.send)
			}
			h.mu.Unlock()
		}
	}
}

func (h *Hub) clientByID(id string) *Client {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return h.clients[id]
}

func (h *Hub) isBanned(id string) bool {
	h.mu.RLock()
	defer h.mu.RUnlock()
	_, ok := h.banned[id]
	return ok
}

func (h *Hub) ban(id string) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.banned[id] = struct{}{}
}

func (h *Hub) broadcastJSON(v any) {
	b, err := json.Marshal(v)
	if err != nil {
		return
	}
	h.mu.RLock()
	defer h.mu.RUnlock()
	for _, c := range h.clients {
		select {
		case c.send <- b:
		default:
		}
	}
}

func (c *Client) writePump() {
	ticker := time.NewTicker(54 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case msg, ok := <-c.send:
			if !ok {
				_ = c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}
			_ = c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := c.conn.WriteMessage(websocket.TextMessage, msg); err != nil {
				return
			}
		case <-ticker.C:
			_ = c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

func (c *Client) readPump() {
	defer func() {
		c.hub.unregister <- c
		_ = c.conn.Close()
	}()
	_ = c.conn.SetReadDeadline(time.Now().Add(120 * time.Second))
	c.conn.SetPongHandler(func(string) error {
		_ = c.conn.SetReadDeadline(time.Now().Add(120 * time.Second))
		return nil
	})
	for {
		_, data, err := c.conn.ReadMessage()
		if err != nil {
			return
		}
		var in inbound
		if err := json.Unmarshal(data, &in); err != nil || in.Type != "chat" {
			c.reply(outbound{Type: "system", OK: false, Message: "invalid message"})
			continue
		}
		text := strings.TrimSpace(in.Text)
		if text == "" {
			continue
		}
		if strings.HasPrefix(text, "/") {
			c.handleCommand(text)
			continue
		}
		c.hub.broadcastJSON(outbound{Type: "chat", From: c.id, Text: text})
	}
}

func (c *Client) reply(o outbound) {
	b, err := json.Marshal(o)
	if err != nil {
		return
	}
	select {
	case c.send <- b:
	default:
	}
}

func (c *Client) handleCommand(line string) {
	fields := strings.Fields(line)
	if len(fields) == 0 {
		return
	}
	cmd := strings.ToLower(strings.TrimPrefix(fields[0], "/"))
	args := fields[1:]

	switch cmd {
	case "kick":
		if !c.role.canKick() {
			c.reply(outbound{Type: "system", OK: false, Message: "forbidden: kick"})
			return
		}
		if len(args) < 1 {
			c.reply(outbound{Type: "system", OK: false, Message: "usage: /kick <user_id> [reason...]"})
			return
		}
		targetID := args[0]
		t := c.hub.clientByID(targetID)
		if t == nil {
			c.reply(outbound{Type: "system", OK: false, Message: "user not found"})
			return
		}
		_ = t.conn.Close()
		c.hub.broadcastJSON(outbound{Type: "system", Text: c.id + " kicked " + targetID})

	case "ban":
		if !c.role.canBan() {
			c.reply(outbound{Type: "system", OK: false, Message: "forbidden: ban"})
			return
		}
		if len(args) < 1 {
			c.reply(outbound{Type: "system", OK: false, Message: "usage: /ban <user_id>"})
			return
		}
		targetID := args[0]
		c.hub.ban(targetID)
		if t := c.hub.clientByID(targetID); t != nil {
			t.reply(outbound{Type: "system", OK: false, Message: "banned"})
			_ = t.conn.Close()
		}
		c.hub.broadcastJSON(outbound{Type: "system", Text: c.id + " banned " + targetID})

	case "giveitems":
		if !c.role.canGiveItems() {
			c.reply(outbound{Type: "system", OK: false, Message: "forbidden: giveitems"})
			return
		}
		if len(args) < 3 {
			c.reply(outbound{Type: "system", OK: false, Message: "usage: /giveitems <user_id> <item_id> <count>"})
			return
		}
		targetID, itemID, countStr := args[0], args[1], args[2]
		n, err := strconv.Atoi(countStr)
		if err != nil || n < 0 {
			c.reply(outbound{Type: "system", OK: false, Message: "invalid count"})
			return
		}
		t := c.hub.clientByID(targetID)
		if t == nil {
			c.reply(outbound{Type: "system", OK: false, Message: "user not found"})
			return
		}
		msg := "you received " + strconv.Itoa(n) + "x " + itemID + " from " + c.id
		t.reply(outbound{Type: "system", OK: true, Message: msg})
		c.reply(outbound{Type: "system", OK: true, Message: "gave " + strconv.Itoa(n) + "x " + itemID + " to " + targetID})

	default:
		c.reply(outbound{Type: "system", OK: false, Message: "unknown command"})
	}
}

var upgrader = websocket.Upgrader{
	ReadBufferSize:  4096,
	WriteBufferSize: 4096,
	CheckOrigin: func(r *http.Request) bool { return true },
}

func serveWS(hub *Hub, w http.ResponseWriter, r *http.Request) {
	userID := strings.TrimSpace(r.Header.Get(headerUserID))
	if userID == "" {
		http.Error(w, "missing "+headerUserID, http.StatusBadRequest)
		return
	}
	role := parseRole(r.Header.Get(headerRole))
	if hub.isBanned(userID) {
		http.Error(w, "banned", http.StatusForbidden)
		return
	}
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println("upgrade:", err)
		return
	}
	if existing := hub.clientByID(userID); existing != nil {
		_ = existing.conn.Close()
	}
	c := &Client{
		id:   userID,
		role: role,
		hub:  hub,
		conn: conn,
		send: make(chan []byte, 256),
	}
	hub.register <- c
	c.reply(outbound{Type: "system", OK: true, Message: "connected as " + userID + " role=" + r.Header.Get(headerRole)})
	go c.writePump()
	c.readPump()
}

func main() {
	hub := newHub()
	go hub.run()
	http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
		serveWS(hub, w, r)
	})
	addr := ":8080"
	log.Println("listening on " + addr)
	log.Fatal(http.ListenAndServe(addr, nil))
}
