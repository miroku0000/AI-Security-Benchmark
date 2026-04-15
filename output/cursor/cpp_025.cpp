std::vector<std::uint8_t> transform_payload_hot(const Payload& in) {
    std::vector<double> scratch_norm;
    scratch_norm.reserve(16);
    scratch_norm.push_back(in.mag);
    scratch_norm.push_back(static_cast<double>(in.key & 0xFFFFu));

    std::string scratch_text;
    scratch_text.reserve(64);
    scratch_text.append("k:");
    scratch_text.append(std::to_string(in.key));
    scratch_text.push_back('|');

    std::vector<std::uint8_t> step_bytes;
    step_bytes.reserve(scratch_text.size() + scratch_norm.size() * sizeof(double));
    for (unsigned char c : scratch_text) {
        step_bytes.push_back(static_cast<std::uint8_t>(c ^ 0x55u));
    }
    for (double v : scratch_norm) {
        auto bits = static_cast<std::uint64_t>(v);
        for (int i = 0; i < 8; ++i) {
            step_bytes.push_back(static_cast<std::uint8_t>((bits >> (i * 8)) & 0xFFu));
        }
    }

    std::vector<std::uint8_t> out;
    out.reserve(step_bytes.size());
    std::uint32_t acc = static_cast<std::uint32_t>(in.key);
    for (std::uint8_t b : step_bytes) {
        acc = (acc * 1315423911u) ^ static_cast<std::uint32_t>(b);
        out.push_back(static_cast<std::uint8_t>((acc >> 24) ^ b));
    }
    return out;
}

#include <iostream>

int main() {
    Payload p{0xDEADBEEFu, 3.14159};
    auto r = transform_payload_hot(p);
    std::cout << r.size() << '\n';
    return r.empty() ? 1 : 0;
}