#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <memory>
#include <numeric>
#include <vector>

struct InputRecord {
    std::vector<int> values;
};

struct NormalizedData {
    std::vector<float> values;
};

struct FilteredData {
    std::vector<float> values;
};

struct EncodedData {
    std::vector<std::uint8_t> bytes;
};

std::vector<std::uint8_t> transformHotPath(const InputRecord& record) {
    auto normalized = std::make_unique<NormalizedData>();
    normalized->values.reserve(record.values.size());

    float sum = static_cast<float>(
        std::accumulate(record.values.begin(), record.values.end(), 0));
    float scale = sum == 0.0f ? 1.0f : sum;

    for (int value : record.values) {
        normalized->values.push_back(static_cast<float>(value) / scale);
    }

    auto filtered = std::make_unique<FilteredData>();
    filtered->values.reserve(normalized->values.size());

    for (float value : normalized->values) {
        if (value > 0.05f) {
            filtered->values.push_back(std::sqrt(value));
        }
    }

    auto encoded = std::make_unique<EncodedData>();
    encoded->bytes.reserve(filtered->values.size());

    for (float value : filtered->values) {
        float clamped = std::clamp(value * 255.0f, 0.0f, 255.0f);
        encoded->bytes.push_back(static_cast<std::uint8_t>(clamped));
    }

    return std::move(encoded->bytes);
}

int main() {
    InputRecord record{{10, 25, 3, 40, 7, 15, 0, 20}};
    auto result = transformHotPath(record);

    for (std::size_t i = 0; i < result.size(); ++i) {
        if (i != 0) {
            std::cout << ' ';
        }
        std::cout << static_cast<int>(result[i]);
    }
    std::cout << '\n';

    return 0;
}