#include <arpa/inet.h>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#pragma pack(push, 1)
struct PositionPacket {
    std::uint8_t type;
    std::uint32_t player_id;
    float x;
    float y;
    float z;
    float yaw;
    float pitch;
};

struct ActionPacket {
    std::uint8_t type;
    std::uint32_t player_id;
    float dir_x;
    float dir_y;
    float dir_z;
    std::uint32_t weapon_id;
};
#pragma pack(pop)

constexpr std::uint8_t kPacketPosition = 0;
constexpr std::uint8_t kPacketShoot = 1;
constexpr float kHitRadius = 0.6f;
constexpr std::uint16_t kDefaultPort = 7777;

struct PlayerState {
    float x = 0.f;
    float y = 0.f;
    float z = 0.f;
    float yaw = 0.f;
    float pitch = 0.f;
    bool present = false;
};

static float dot3(float ax, float ay, float az, float bx, float by, float bz) {
    return ax * bx + ay * by + az * bz;
}

static bool ray_hits_sphere(float ox, float oy, float oz, float dx, float dy, float dz, float cx,
                            float cy, float cz, float r) {
    const float lx = cx - ox;
    const float ly = cy - oy;
    const float lz = cz - oz;
    const float tca = dot3(lx, ly, lz, dx, dy, dz);
    if (tca < 0.f) {
        return false;
    }
    const float d2 = dot3(lx, ly, lz, lx, ly, lz) - tca * tca;
    return d2 <= r * r;
}

int main(int argc, char** argv) {
    std::uint16_t port = kDefaultPort;
    if (argc >= 2) {
        const long p = std::strtol(argv[1], nullptr, 10);
        if (p > 0 && p < 65536) {
            port = static_cast<std::uint16_t>(p);
        }
    }

    const int fd = ::socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        std::perror("socket");
        return 1;
    }

    int yes = 1;
    if (::setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes)) != 0) {
        std::perror("setsockopt");
        ::close(fd);
        return 1;
    }

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(port);

    if (::bind(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
        std::perror("bind");
        ::close(fd);
        return 1;
    }

    std::printf("fps udp server listening on udp/%u\n", static_cast<unsigned>(port));

    std::map<std::uint32_t, PlayerState> players;
    alignas(ActionPacket) unsigned char buf[65536];

    for (;;) {
        sockaddr_in from{};
        socklen_t from_len = sizeof(from);
        const ssize_t n =
            ::recvfrom(fd, buf, sizeof(buf), 0, reinterpret_cast<sockaddr*>(&from), &from_len);
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            std::perror("recvfrom");
            break;
        }
        if (n < 1) {
            continue;
        }

        const std::uint8_t pkt_type = buf[0];

        if (pkt_type == kPacketPosition) {
            if (static_cast<std::size_t>(n) < sizeof(PositionPacket)) {
                continue;
            }
            PositionPacket pos{};
            std::memcpy(&pos, buf, sizeof(pos));
            PlayerState& st = players[pos.player_id];
            st.x = pos.x;
            st.y = pos.y;
            st.z = pos.z;
            st.yaw = pos.yaw;
            st.pitch = pos.pitch;
            st.present = true;
            continue;
        }

        if (pkt_type == kPacketShoot) {
            if (static_cast<std::size_t>(n) < sizeof(ActionPacket)) {
                continue;
            }
            ActionPacket act{};
            std::memcpy(&act, buf, sizeof(act));
            const auto shooter_it = players.find(act.player_id);
            if (shooter_it == players.end() || !shooter_it->second.present) {
                continue;
            }
            const PlayerState& shooter = shooter_it->second;
            const float ox = shooter.x;
            const float oy = shooter.y;
            const float oz = shooter.z;
            const float dx = act.dir_x;
            const float dy = act.dir_y;
            const float dz = act.dir_z;

            for (const auto& kv : players) {
                const std::uint32_t target_id = kv.first;
                if (target_id == act.player_id) {
                    continue;
                }
                const PlayerState& tgt = kv.second;
                if (!tgt.present) {
                    continue;
                }
                if (ray_hits_sphere(ox, oy, oz, dx, dy, dz, tgt.x, tgt.y, tgt.z, kHitRadius)) {
                    char ip[INET_ADDRSTRLEN]{};
                    inet_ntop(AF_INET, &from.sin_addr, ip, sizeof(ip));
                    std::printf("hit player %u from shooter %u weapon %u (from %s:%u)\n",
                                target_id, act.player_id, act.weapon_id, ip,
                                static_cast<unsigned>(ntohs(from.sin_port)));
                }
            }
            continue;
        }
    }

    ::close(fd);
    return 0;
}
