#include <iostream>
#include <cstring>
#include <cmath>
#include <unordered_map>
#include <vector>
#include <chrono>
#include <algorithm>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
#include <cerrno>

// --- Configuration ---
static constexpr int SERVER_PORT = 27015;
static constexpr int MAX_PLAYERS = 32;
static constexpr int RECV_BUF_SIZE = 2048;
static constexpr int TICK_RATE_MS = 16; // ~60 tick
static constexpr float MAP_MIN = -5000.0f;
static constexpr float MAP_MAX = 5000.0f;
static constexpr float MAX_SPEED = 500.0f;  // units/sec
static constexpr float MAX_HP = 100.0f;
static constexpr float WEAPON_DAMAGE = 25.0f;
static constexpr float WEAPON_RANGE = 2000.0f;
static constexpr float HIT_RADIUS = 1.5f;
static constexpr int64_t PLAYER_TIMEOUT_SEC = 30;
static constexpr int MAX_PACKETS_PER_TICK = 256;
static constexpr size_t MIN_PACKET_SIZE = 5; // 1 byte type + 4 byte player_id

// --- Packet types ---
enum class PacketType : uint8_t {
    CONNECT     = 0x01,
    DISCONNECT  = 0x02,
    POSITION    = 0x03,
    SHOOT       = 0x04,
    STATE_UPDATE = 0x05,
    CONNECT_ACK = 0x06,
    HIT_NOTIFY  = 0x07,
    KILL_NOTIFY = 0x08,
};

// --- Math helpers ---
struct Vec3 {
    float x, y, z;
    Vec3() : x(0), y(0), z(0) {}
    Vec3(float x, float y, float z) : x(x), y(y), z(z) {}
    Vec3 operator-(const Vec3& o) const { return {x - o.x, y - o.y, z - o.z}; }
    Vec3 operator+(const Vec3& o) const { return {x + o.x, y + o.y, z + o.z}; }
    Vec3 operator*(float s) const { return {x * s, y * s, z * s}; }
    float length() const { return std::sqrt(x*x + y*y + z*z); }
    float dot(const Vec3& o) const { return x*o.x + y*o.y + z*o.z; }
    Vec3 normalized() const {
        float len = length();
        if (len < 1e-6f) return {0, 0, 0};
        return {x / len, y / len, z / len};
    }
};

static bool is_finite_vec3(const Vec3& v) {
    return std::isfinite(v.x) && std::isfinite(v.y) && std::isfinite(v.z);
}

static bool in_bounds(const Vec3& v) {
    return v.x >= MAP_MIN && v.x <= MAP_MAX &&
           v.y >= MAP_MIN && v.y <= MAP_MAX &&
           v.z >= MAP_MIN && v.z <= MAP_MAX;
}

// --- Packet structures (wire format, packed) ---
#pragma pack(push, 1)
struct PacketHeader {
    uint8_t type;
    uint32_t player_id;
};

struct PositionPacket {
    PacketHeader header;
    float x, y, z;
    float yaw, pitch;
};

struct ShootPacket {
    PacketHeader header;
    float dir_x, dir_y, dir_z;
};

struct StateEntry {
    uint32_t player_id;
    float x, y, z;
    float hp;
};

struct HitNotifyPacket {
    PacketHeader header;
    uint32_t target_id;
    float damage;
};

struct KillNotifyPacket {
    PacketHeader header;
    uint32_t victim_id;
    uint32_t killer_id;
};
#pragma pack(pop)

// --- Player state ---
struct Player {
    uint32_t id;
    Vec3 position;
    float yaw = 0.0f;
    float pitch = 0.0f;
    float hp = MAX_HP;
    int kills = 0;
    int deaths = 0;
    bool alive = true;
    sockaddr_in addr;
    int64_t last_packet_time;
    int packets_this_tick = 0;
};

// --- Unique key for sockaddr_in ---
struct AddrKey {
    uint32_t ip;
    uint16_t port;
    bool operator==(const AddrKey& o) const { return ip == o.ip && port == o.port; }
};
struct AddrKeyHash {
    size_t operator()(const AddrKey& k) const {
        return std::hash<uint64_t>()(((uint64_t)k.ip << 16) | k.port);
    }
};

// --- Server ---
class GameServer {
public:
    GameServer() = default;
    ~GameServer() { if (sock_fd_ >= 0) close(sock_fd_); }

    bool start() {
        sock_fd_ = socket(AF_INET, SOCK_DGRAM, 0);
        if (sock_fd_ < 0) {
            perror("socket");
            return false;
        }

        // Non-blocking
        struct timeval tv;
        tv.tv_sec = 0;
        tv.tv_usec = TICK_RATE_MS * 1000;
        setsockopt(sock_fd_, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

        int reuse = 1;
        setsockopt(sock_fd_, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

        sockaddr_in server_addr{};
        server_addr.sin_family = AF_INET;
        server_addr.sin_addr.s_addr = INADDR_ANY;
        server_addr.sin_port = htons(SERVER_PORT);

        if (bind(sock_fd_, (sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
            perror("bind");
            return false;
        }

        std::cout << "[Server] Listening on port " << SERVER_PORT
                  << " (tick rate: " << (1000 / TICK_RATE_MS) << " Hz, max players: "
                  << MAX_PLAYERS << ")\n";
        return true;
    }

    void run() {
        running_ = true;
        while (running_) {
            auto tick_start = std::chrono::steady_clock::now();

            // Reset per-tick packet counters
            for (auto& [id, p] : players_) p.packets_this_tick = 0;

            receive_packets();
            timeout_players();
            broadcast_state();

            auto tick_end = std::chrono::steady_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(tick_end - tick_start);
            if (elapsed.count() < TICK_RATE_MS) {
                usleep((TICK_RATE_MS - elapsed.count()) * 1000);
            }
        }
    }

private:
    int sock_fd_ = -1;
    bool running_ = false;
    uint32_t next_player_id_ = 1;
    std::unordered_map<uint32_t, Player> players_;
    std::unordered_map<AddrKey, uint32_t, AddrKeyHash> addr_to_id_;

    int64_t now_sec() const {
        return std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
    }

    void send_to(const sockaddr_in& addr, const void* data, size_t len) {
        sendto(sock_fd_, data, len, 0, (const sockaddr*)&addr, sizeof(addr));
    }

    void receive_packets() {
        uint8_t buf[RECV_BUF_SIZE];
        sockaddr_in sender{};
        socklen_t sender_len;
        int packets_received = 0;

        while (packets_received < MAX_PACKETS_PER_TICK) {
            sender_len = sizeof(sender);
            ssize_t n = recvfrom(sock_fd_, buf, sizeof(buf), 0,
                                 (sockaddr*)&sender, &sender_len);
            if (n <= 0) break;
            packets_received++;

            // Validate minimum packet size
            if (static_cast<size_t>(n) < MIN_PACKET_SIZE) continue;

            auto* header = reinterpret_cast<const PacketHeader*>(buf);
            auto type = static_cast<PacketType>(header->type);

            // Connection requests use id 0; all others must match a known player
            if (type == PacketType::CONNECT) {
                handle_connect(sender);
                continue;
            }

            uint32_t pid = header->player_id;
            auto it = players_.find(pid);
            if (it == players_.end()) continue; // Unknown player, drop

            Player& player = it->second;

            // Verify sender address matches the player's registered address (anti-spoof)
            AddrKey sender_key{sender.sin_addr.s_addr, sender.sin_port};
            AddrKey player_key{player.addr.sin_addr.s_addr, player.addr.sin_port};
            if (!(sender_key == player_key)) continue;

            // Rate limit per player per tick
            if (++player.packets_this_tick > 10) continue;

            player.last_packet_time = now_sec();

            switch (type) {
                case PacketType::DISCONNECT:
                    handle_disconnect(pid);
                    break;
                case PacketType::POSITION:
                    if (static_cast<size_t>(n) >= sizeof(PositionPacket))
                        handle_position(player, reinterpret_cast<const PositionPacket*>(buf));
                    break;
                case PacketType::SHOOT:
                    if (static_cast<size_t>(n) >= sizeof(ShootPacket))
                        handle_shoot(player, reinterpret_cast<const ShootPacket*>(buf));
                    break;
                default:
                    break; // Unknown packet type, ignore
            }
        }
    }

    void handle_connect(const sockaddr_in& addr) {
        AddrKey key{addr.sin_addr.s_addr, addr.sin_port};

        // Already connected?
        auto existing = addr_to_id_.find(key);
        if (existing != addr_to_id_.end()) {
            // Re-send ack
            send_connect_ack(addr, existing->second);
            return;
        }

        if (players_.size() >= MAX_PLAYERS) {
            std::cout << "[Server] Rejected connection: server full\n";
            return;
        }

        uint32_t pid = next_player_id_++;
        Player p;
        p.id = pid;
        p.position = {0.0f, 0.0f, 0.0f}; // Spawn point
        p.hp = MAX_HP;
        p.alive = true;
        p.addr = addr;
        p.last_packet_time = now_sec();

        players_[pid] = p;
        addr_to_id_[key] = pid;

        send_connect_ack(addr, pid);

        char ip_str[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &addr.sin_addr, ip_str, sizeof(ip_str));
        std::cout << "[Server] Player " << pid << " connected from "
                  << ip_str << ":" << ntohs(addr.sin_port)
                  << " (" << players_.size() << "/" << MAX_PLAYERS << ")\n";
    }

    void send_connect_ack(const sockaddr_in& addr, uint32_t pid) {
        PacketHeader ack;
        ack.type = static_cast<uint8_t>(PacketType::CONNECT_ACK);
        ack.player_id = pid;
        send_to(addr, &ack, sizeof(ack));
    }

    void handle_disconnect(uint32_t pid) {
        auto it = players_.find(pid);
        if (it == players_.end()) return;

        AddrKey key{it->second.addr.sin_addr.s_addr, it->second.addr.sin_port};
        addr_to_id_.erase(key);
        std::cout << "[Server] Player " << pid << " disconnected\n";
        players_.erase(it);
    }

    void handle_position(Player& player, const PositionPacket* pkt) {
        if (!player.alive) return;

        Vec3 new_pos{pkt->x, pkt->y, pkt->z};

        // Validate: reject NaN/Inf
        if (!is_finite_vec3(new_pos)) return;

        // Validate: clamp to map bounds
        if (!in_bounds(new_pos)) return;

        // Validate: speed check (reject teleporting)
        float dist = (new_pos - player.position).length();
        float max_move = MAX_SPEED * (TICK_RATE_MS / 1000.0f) * 3.0f; // generous tolerance
        if (dist > max_move && player.position.length() > 1e-3f) {
            // First position update gets a pass (spawning)
            return;
        }

        // Validate yaw/pitch
        float yaw = pkt->yaw;
        float pitch = pkt->pitch;
        if (!std::isfinite(yaw) || !std::isfinite(pitch)) return;

        player.position = new_pos;
        player.yaw = yaw;
        player.pitch = std::clamp(pitch, -90.0f, 90.0f);
    }

    void handle_shoot(Player& player, const ShootPacket* pkt) {
        if (!player.alive) return;

        Vec3 dir{pkt->dir_x, pkt->dir_y, pkt->dir_z};
        if (!is_finite_vec3(dir)) return;
        if (dir.length() < 1e-6f) return;
        dir = dir.normalized();

        // Ray-sphere intersection against all other living players
        Player* best_target = nullptr;
        float best_dist = WEAPON_RANGE;

        for (auto& [id, target] : players_) {
            if (id == player.id || !target.alive) continue;

            // Ray-sphere: origin=player.position, dir=dir, sphere center=target.position, radius=HIT_RADIUS
            Vec3 oc = player.position - target.position;
            float b = oc.dot(dir);
            float c = oc.dot(oc) - HIT_RADIUS * HIT_RADIUS;
            float discriminant = b * b - c;

            if (discriminant < 0) continue;

            float t = -b - std::sqrt(discriminant);
            if (t < 0) t = -b + std::sqrt(discriminant);
            if (t < 0 || t > best_dist) continue;

            best_dist = t;
            best_target = &target;
        }

        if (!best_target) return;

        best_target->hp -= WEAPON_DAMAGE;

        // Notify shooter of hit
        HitNotifyPacket hit{};
        hit.header.type = static_cast<uint8_t>(PacketType::HIT_NOTIFY);
        hit.header.player_id = player.id;
        hit.target_id = best_target->id;
        hit.damage = WEAPON_DAMAGE;
        send_to(player.addr, &hit, sizeof(hit));

        if (best_target->hp <= 0.0f) {
            best_target->hp = 0.0f;
            best_target->alive = false;
            best_target->deaths++;
            player.kills++;

            std::cout << "[Server] Player " << player.id << " killed Player "
                      << best_target->id << " (K:" << player.kills << " D:" << player.deaths << ")\n";

            // Notify all players of kill
            KillNotifyPacket kill{};
            kill.header.type = static_cast<uint8_t>(PacketType::KILL_NOTIFY);
            kill.victim_id = best_target->id;
            kill.killer_id = player.id;
            for (auto& [id, p] : players_) {
                kill.header.player_id = id;
                send_to(p.addr, &kill, sizeof(kill));
            }

            // Respawn after short delay (immediate for simplicity)
            respawn(*best_target);
        }
    }

    void respawn(Player& player) {
        // Simple spawn at a pseudo-random location within a safe zone
        float angle = static_cast<float>(player.id * 137 % 360) * (3.14159f / 180.0f);
        float radius = 500.0f;
        player.position = {radius * std::cos(angle), 0.0f, radius * std::sin(angle)};
        player.hp = MAX_HP;
        player.alive = true;
    }

    void timeout_players() {
        int64_t now = now_sec();
        std::vector<uint32_t> to_remove;
        for (auto& [id, p] : players_) {
            if (now - p.last_packet_time > PLAYER_TIMEOUT_SEC) {
                to_remove.push_back(id);
            }
        }
        for (uint32_t id : to_remove) {
            std::cout << "[Server] Player " << id << " timed out\n";
            AddrKey key{players_[id].addr.sin_addr.s_addr, players_[id].addr.sin_port};
            addr_to_id_.erase(key);
            players_.erase(id);
        }
    }

    void broadcast_state() {
        if (players_.empty()) return;

        // Build state update buffer
        size_t entry_count = players_.size();
        size_t buf_size = sizeof(PacketHeader) + sizeof(uint32_t) + entry_count * sizeof(StateEntry);
        if (buf_size > RECV_BUF_SIZE) return; // Safety

        uint8_t buf[RECV_BUF_SIZE];
        auto* header = reinterpret_cast<PacketHeader*>(buf);
        header->type = static_cast<uint8_t>(PacketType::STATE_UPDATE);
        header->player_id = 0;

        uint32_t count = static_cast<uint32_t>(entry_count);
        memcpy(buf + sizeof(PacketHeader), &count, sizeof(count));

        size_t offset = sizeof(PacketHeader) + sizeof(uint32_t);
        for (auto& [id, p] : players_) {
            StateEntry entry;
            entry.player_id = id;
            entry.x = p.position.x;
            entry.y = p.position.y;
            entry.z = p.position.z;
            entry.hp = p.hp;
            memcpy(buf + offset, &entry, sizeof(entry));
            offset += sizeof(entry);
        }

        for (auto& [id, p] : players_) {
            header->player_id = id;
            send_to(p.addr, buf, offset);
        }
    }
};

int main() {
    GameServer server;
    if (!server.start()) {
        return 1;
    }
    std::cout << "[Server] Running. Press Ctrl+C to stop.\n";
    server.run();
    return 0;
}