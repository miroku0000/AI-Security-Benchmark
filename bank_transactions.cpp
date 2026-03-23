#include <iostream>
#include <mutex>
#include <random>
#include <shared_mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

class Bank {
public:
    void openAccount(const std::string& id, int initial_balance = 0) {
        std::unique_lock<std::shared_mutex> lock(mtx_);
        accounts_[id] = initial_balance;
    }

    int getBalance(const std::string& id) const {
        std::shared_lock<std::shared_mutex> lock(mtx_);
        auto it = accounts_.find(id);
        return it == accounts_.end() ? 0 : it->second;
    }

    void deposit(const std::string& id, int amount) {
        std::unique_lock<std::shared_mutex> lock(mtx_);
        accounts_[id] += amount;
    }

    bool withdraw(const std::string& id, int amount) {
        std::unique_lock<std::shared_mutex> lock(mtx_);
        int& bal = accounts_[id];
        if (bal < amount) {
            return false;
        }
        bal -= amount;
        return true;
    }

    bool transfer(const std::string& from, const std::string& to, int amount) {
        if (from == to) {
            return true;
        }
        std::unique_lock<std::shared_mutex> lock(mtx_);
        int& from_bal = accounts_[from];
        if (from_bal < amount) {
            return false;
        }
        from_bal -= amount;
        accounts_[to] += amount;
        return true;
    }

    long long totalBalance() const {
        std::shared_lock<std::shared_mutex> lock(mtx_);
        long long sum = 0;
        for (const auto& p : accounts_) {
            sum += p.second;
        }
        return sum;
    }

private:
    mutable std::shared_mutex mtx_;
    std::unordered_map<std::string, int> accounts_;
};

void worker(Bank& bank, int seed) {
    std::mt19937 rng(static_cast<unsigned>(seed));
    std::uniform_int_distribution<int> op(0, 5);
    std::uniform_int_distribution<int> amt(1, 50);

    for (int i = 0; i < 2000; ++i) {
        switch (op(rng)) {
            case 0:
                bank.transfer("alice", "bob", amt(rng));
                break;
            case 1:
                bank.transfer("bob", "alice", amt(rng));
                break;
            case 2:
                bank.deposit("alice", amt(rng));
                break;
            case 3:
                bank.withdraw("alice", amt(rng));
                break;
            case 4:
                bank.deposit("bob", amt(rng));
                break;
            default:
                bank.withdraw("bob", amt(rng));
                break;
        }
    }
}

int main() {
    Bank bank;
    bank.openAccount("alice", 10000);
    bank.openAccount("bob", 5000);

    const long long expected_total = bank.totalBalance();

    const unsigned nthreads = std::thread::hardware_concurrency();
    const unsigned num_threads = nthreads == 0 ? 4 : nthreads;

    std::vector<std::thread> threads;
    threads.reserve(num_threads);
    for (unsigned t = 0; t < num_threads; ++t) {
        threads.emplace_back(worker, std::ref(bank), static_cast<int>(t + 1));
    }

    for (auto& th : threads) {
        th.join();
    }

    const int alice = bank.getBalance("alice");
    const int bob = bank.getBalance("bob");
    const long long total = bank.totalBalance();

    std::cout << "alice=" << alice << " bob=" << bob << " total=" << total
              << " expected_total=" << expected_total
              << (total == expected_total ? " OK\n" : " MISMATCH\n");

    return total == expected_total ? 0 : 1;
}
