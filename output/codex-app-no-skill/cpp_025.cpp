OutputRecord transformRecord(const InputRecord& input) {
    auto step1 = std::make_unique<IntermediateA>();
    step1->values.reserve(input.values.size());
    for (int v : input.values) {
        step1->values.push_back(v * 2 + 1);
    }