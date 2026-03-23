#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <cstring>
#include <stdexcept>
#include <string>

class NetworkConnection {
 public:
  explicit NetworkConnection(const std::string& host, std::uint16_t port)
      : fd_(-1), host_(host), port_(port) {
    if (!EstablishConnection()) {
      cleanup();
      throw std::runtime_error(std::string("connection failed: ") +
                               std::strerror(errno));
    }
  }

  ~NetworkConnection() { cleanup(); }

  NetworkConnection(const NetworkConnection&) = delete;
  NetworkConnection& operator=(const NetworkConnection&) = delete;

  NetworkConnection(NetworkConnection&& other) noexcept
      : fd_(other.fd_), host_(std::move(other.host_)), port_(other.port_) {
    other.fd_ = -1;
  }

  NetworkConnection& operator=(NetworkConnection&& other) noexcept {
    if (this != &other) {
      cleanup();
      fd_ = other.fd_;
      host_ = std::move(other.host_);
      port_ = other.port_;
      other.fd_ = -1;
    }
    return *this;
  }

  void reset() {
    cleanup();
    if (!EstablishConnection()) {
      cleanup();
      throw std::runtime_error(std::string("reset failed: ") +
                               std::strerror(errno));
    }
  }

  void reinitialize() {
    cleanup();
    if (!EstablishConnection()) {
      cleanup();
      throw std::runtime_error(std::string("reinitialize failed: ") +
                               std::strerror(errno));
    }
  }

  int fd() const noexcept { return fd_; }

 private:
  void cleanup() noexcept {
    if (fd_ >= 0) {
      ::close(fd_);
      fd_ = -1;
    }
  }

  bool EstablishConnection() {
    int s = ::socket(AF_INET, SOCK_STREAM, 0);
    if (s < 0) {
      return false;
    }

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port_);
    if (inet_pton(AF_INET, host_.c_str(), &addr.sin_addr) != 1) {
      ::close(s);
      errno = EINVAL;
      return false;
    }

    if (::connect(s, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
      ::close(s);
      return false;
    }

    fd_ = s;
    return true;
  }

  int fd_;
  std::string host_;
  std::uint16_t port_;
};

int main() {
  return 0;
}
