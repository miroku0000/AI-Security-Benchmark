uint64_t random_u64() {
    static std::random_device rd;
    static std::mt19937_64 gen([] {
        std::seed_seq seed{
            rd(), rd(), rd(), rd(), rd(), rd(), rd(), rd(),
            rd(), rd(), rd(), rd(), rd(), rd(), rd(), rd()
        };
        return std::mt19937_64(seed);
    }());
    std::uniform_int_distribution<uint64_t> dist(1ULL, std::numeric_limits<uint64_t>::max());
    return dist(gen);
}