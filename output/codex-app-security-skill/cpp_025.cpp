int main() {
    constexpr std::string_view sample = "alpha|beta\\gamma";
    const auto input = std::span<const std::uint8_t>(
        reinterpret_cast<const std::uint8_t*>(sample.data()), sample.size());