#include <atomic>
#include <iostream>
#include <mutex>
#include <random>
#include <shared_mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

struct Account {
    std::string id;
    double balance{0.0};
};

class BankLedger {
public:
    void open_account(const std::string& id, double initial_balance) {
        std::unique_lock<std::shared_mutex> lock(mutex_);
        accounts_[id] = Account{id, initial_balance};
    }

    bool deposit(const std::string& id, double amount) {
        if (amount <= 0.0) return false;
        std::unique_lock<std::shared_mutex> lock(mutex_);
        auto it = accounts_.find(id);
        if (it == accounts_.end()) return false;
        it->second.balance += amount;
        return true;
    }

    bool withdraw(const std::string& id, double amount) {
        if (amount <= 0.0) return false;
        std::unique_lock<std::shared_mutex> lock(mutex_);
        auto it = accounts_.find(id);
        if (it == accounts_.end()) return false;
        if (it->second.balance < amount) return false;
        it->second.balance -= amount;
        return true;
    }

    bool transfer(const std::string& from, const std::string& to, double amount) {
        if (amount <= 0.0) return false;
        std::unique_lock<std::shared_mutex> lock(mutex_);
        auto it_from = accounts_.find(from);
        auto it_to = accounts_.find(to);
        if (it_from == accounts_.end() || it_to == accounts_.end()) return false;
        if (it_from->second.balance < amount) return false;
        it_from->second.balance -= amount;
        it_to->second.balance += amount;
        return true;
    }

    double balance(const std::string& id) const {
        std::shared_lock<std::shared_mutex> lock(mutex_);
        auto it = accounts_.find(id);
        if (it == accounts_.end()) return -1.0;
        return it->second.balance;
    }

    double total_balance() const {
        std::shared_lock<std::shared_mutex> lock(mutex_);
        double sum = 0.0;
        for (const auto& [_, acc] : accounts_) sum += acc.balance;
        return sum;
    }

private:
    mutable std::shared_mutex mutex_;
    std::unordered_map<std::string, Account> accounts_;
};

int main() {
    BankLedger ledger;
    const std::vector<std::string> ids = {"A", "B", "C", "D", "E"};
    for (const auto& id : ids) ledger.open_account(id, 1000.0);

    std::atomic<std::uint64_t> successful_ops{0};

    auto worker = [&](int seed) {
        std::mt19937 rng(static_cast<std::uint32_t>(seed));
        std::uniform_int_distribution<int> pick(0, static_cast<int>(ids.size()) - 1);
        std::uniform_real_distribution<double> amount_dist(1.0, 75.0);
        std::uniform_int_distribution<int> op(0, 2);

        for (int i = 0; i < 2000; ++i) {
            int ai = pick(rng);
            int bi = pick(rng);
            while (bi == ai) bi = pick(rng);
            const std::string& a = ids[static_cast<std::size_t>(ai)];
            const std::string& b = ids[static_cast<std::size_t>(bi)];
            double x = amount_dist(rng);

            bool ok = false;
            switch (op(rng)) {
                case 0:
                    ok = ledger.transfer(a, b, x);
                    break;
                case 1:
                    ok = ledger.deposit(a, x);
                    break;
                case 2:
                    ok = ledger.withdraw(a, x);
                    break;
            }
            if (ok) successful_ops.fetch_add(1, std::memory_order_relaxed);

            (void)ledger.balance(ids[static_cast<std::size_t>(pick(rng))]);
        }
    };

    const int num_threads = 12;
    std::vector<std::thread> threads;
    threads.reserve(static_cast<std::size_t>(num_threads));
    for (int t = 0; t < num_threads; ++t) {
        threads.emplace_back(worker, t + 1);
    }
    for (auto& th : threads) th.join();

    std::cout << "successful_ops=" << successful_ops.load() << "\n";
    std::cout << "total_balance=" << ledger.total_balance() << "\n";
    for (const auto& id : ids) {
        std::cout << id << "=" << ledger.balance(id) << "\n";
    }
    return 0;
}
