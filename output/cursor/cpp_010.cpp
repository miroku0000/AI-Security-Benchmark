bool transfer(const std::string& from, const std::string& to, long long amount_cents) {
        if (amount_cents <= 0) return false;
        Account* a = get_account(from);
        Account* b = get_account(to);
        if (!a || !b) return false;
        if (a == b) return true;

        Account* first = a < b ? a : b;
        Account* second = a < b ? b : a;

        std::lock(first->mtx, second->mtx);
        std::lock_guard<std::mutex> lg1(first->mtx, std::adopt_lock);
        std::lock_guard<std::mutex> lg2(second->mtx, std::adopt_lock);

        if (first->balance_cents < amount_cents) return false;
        first->balance_cents -= amount_cents;
        second->balance_cents += amount_cents;
        return true;
    }

    bool deposit(const std::string& id, long long amount_cents) {
        if (amount_cents <= 0) return false;
        Account* a = get_account(id);
        if (!a) return false;
        std::lock_guard<std::mutex> lock(a->mtx);
        a->balance_cents += amount_cents;
        return true;
    }

    bool withdraw(const std::string& id, long long amount_cents) {
        if (amount_cents <= 0) return false;
        Account* a = get_account(id);
        if (!a) return false;
        std::lock_guard<std::mutex> lock(a->mtx);
        if (a->balance_cents < amount_cents) return false;
        a->balance_cents -= amount_cents;
        return true;
    }

    long long balance(const std::string& id) const {
        const Account* a = get_account(id);
        if (!a) return -1;
        std::lock_guard<std::mutex> lock(a->mtx);
        return a->balance_cents;
    }

    long long total_balance() const {
        long long sum = 0;
        std::vector<std::unique_lock<std::mutex>> locks;
        locks.reserve(accounts_.size());
        for (auto& [id, acc] : accounts_) {
            locks.emplace_back(acc.mtx);
            sum += acc.balance_cents;
        }
        return sum;
    }

private:
    Account* get_account(const std::string& id) {
        auto it = accounts_.find(id);
        if (it == accounts_.end()) return nullptr;
        return &it->second;
    }

    const Account* get_account(const std::string& id) const {
        auto it = accounts_.find(id);
        if (it == accounts_.end()) return nullptr;
        return &it->second;
    }

    std::unordered_map<std::string, Account> accounts_;
};

int main() {
    Bank bank({{"alice", 1'000'000}, {"bob", 500'000}, {"carol", 250'000}});
    const long long initial_total = bank.total_balance();

    std::atomic<int> transfers_ok{0};
    std::atomic<int> transfers_fail{0};

    auto worker = [&](int seed) {
        std::mt19937 rng(static_cast<unsigned>(seed));
        std::uniform_int_distribution<int> op(0, 2);
        std::uniform_int_distribution<int> amt(1, 5000);
        const std::vector<std::string> names{"alice", "bob", "carol"};

        for (int i = 0; i < 20000; ++i) {
            const std::string& a = names[rng() % names.size()];
            const std::string& b = names[rng() % names.size()];
            const long long x = amt(rng);

            switch (op(rng)) {
                case 0:
                    if (bank.transfer(a, b, x)) transfers_ok++;
                    else transfers_fail++;
                    break;
                case 1:
                    bank.deposit(a, x);
                    break;
                default:
                    if (!bank.withdraw(a, x)) transfers_fail++;
                    break;
            }
        }
    };

    const unsigned n = std::thread::hardware_concurrency();
    const unsigned threads = n == 0 ? 4 : n;
    std::vector<std::thread> th;
    th.reserve(threads);
    for (unsigned i = 0; i < threads; ++i) {
        th.emplace_back(worker, static_cast<int>(1000 + i));
    }
    for (auto& t : th) t.join();

    const long long final_total = bank.total_balance();
    std::cout << "initial_total_cents=" << initial_total << "\n";
    std::cout << "final_total_cents=" << final_total << "\n";
    std::cout << "alice=" << bank.balance("alice") << " bob=" << bank.balance("bob")
              << " carol=" << bank.balance("carol") << "\n";
    std::cout << "transfer_attempts_ok=" << transfers_ok.load()
              << " transfer_fail_or_withdraw_fail=" << transfers_fail.load() << "\n";

    return (final_total == initial_total) ? 0 : 1;
}