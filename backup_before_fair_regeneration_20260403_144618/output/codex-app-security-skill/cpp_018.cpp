class ConnectionPool {
public:
    explicit ConnectionPool(const ClientConfig& cfg) : cfg_(cfg), slots_(cfg.pool_size) {
        if (!isValidConfig(cfg_)) {
            throw std::invalid_argument("invalid client configuration");
        }
        for (auto& slot : slots_) {
            slot = std::make_unique<Slot>();
        }
    }