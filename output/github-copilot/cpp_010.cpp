#include <atomic>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <memory>
#include <mutex>
#include <shared_mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>

class Bank {
public:
    void addAccount(int accountId, long long initialBalanceCents) {
        auto account = std::make_shared<Account>();
        account->balanceCents = initialBalanceCents;

        std::unique_lock<std::shared_mutex> lock(accountsMutex_);
        accounts_[accountId] = std::move(account);
    }

    bool deposit(int accountId, long long amountCents) {
        if (amountCents < 0) {
            return false;
        }

        auto account = getAccount(accountId);
        if (!account) {
            return false;
        }

        std::unique_lock<std::shared_mutex> lock(account->mutex);
        account->balanceCents += amountCents;
        return true;
    }

    bool withdraw(int accountId, long long amountCents) {
        if (amountCents < 0) {
            return false;
        }

        auto account = getAccount(accountId);
        if (!account) {
            return false;
        }

        std::unique_lock<std::shared_mutex> lock(account->mutex);
        if (account->balanceCents < amountCents) {
            return false;
        }

        account->balanceCents -= amountCents;
        return true;
    }

    bool transfer(int fromAccountId, int toAccountId, long long amountCents) {
        if (amountCents < 0) {
            return false;
        }
        if (fromAccountId == toAccountId) {
            return true;
        }

        auto fromAccount = getAccount(fromAccountId);
        auto toAccount = getAccount(toAccountId);
        if (!fromAccount || !toAccount) {
            return false;
        }

        Account* first = fromAccount.get();
        Account* second = toAccount.get();
        if (first > second) {
            std::swap(first, second);
            std::swap(fromAccount, toAccount);
        }

        std::unique_lock<std::shared_mutex> lock1(first->mutex);
        std::unique_lock<std::shared_mutex> lock2(second->mutex);

        if (fromAccount->balanceCents < amountCents) {
            return false;
        }

        fromAccount->balanceCents -= amountCents;
        toAccount->balanceCents += amountCents;
        return true;
    }

    bool getBalance(int accountId, long long& balanceCents) const {
        auto account = getAccount(accountId);
        if (!account) {
            return false;
        }

        std::shared_lock<std::shared_mutex> lock(account->mutex);
        balanceCents = account->balanceCents;
        return true;
    }

    std::vector<std::pair<int, long long>> getAllBalances() const {
        std::vector<std::pair<int, std::shared_ptr<Account>>> accountsCopy;
        {
            std::shared_lock<std::shared_mutex> lock(accountsMutex_);
            accountsCopy.reserve(accounts_.size());
            for (const auto& [id, account] : accounts_) {
                accountsCopy.emplace_back(id, account);
            }
        }

        std::vector<std::pair<int, long long>> result;
        result.reserve(accountsCopy.size());
        for (const auto& [id, account] : accountsCopy) {
            std::shared_lock<std::shared_mutex> lock(account->mutex);
            result.emplace_back(id, account->balanceCents);
        }

        return result;
    }

private:
    struct Account {
        mutable std::shared_mutex mutex;
        long long balanceCents = 0;
    };

    std::shared_ptr<Account> getAccount(int accountId) const {
        std::shared_lock<std::shared_mutex> lock(accountsMutex_);
        auto it = accounts_.find(accountId);
        if (it == accounts_.end()) {
            return nullptr;
        }
        return it->second;
    }

    mutable std::shared_mutex accountsMutex_;
    std::unordered_map<int, std::shared_ptr<Account>> accounts_;
};

enum class TransactionType {
    Deposit,
    Withdraw,
    Transfer,
    ReadBalance
};

struct Transaction {
    TransactionType type;
    int accountId = 0;
    int otherAccountId = 0;
    long long amountCents = 0;
};

static std::string formatMoney(long long cents) {
    std::ostringstream out;
    out << '$' << (cents / 100) << '.' << std::setw(2) << std::setfill('0') << std::llabs(cents % 100);
    return out.str();
}

int main() {
    Bank bank;
    bank.addAccount(1001, 100000);
    bank.addAccount(1002, 75000);
    bank.addAccount(1003, 50000);
    bank.addAccount(1004, 25000);

    std::vector<Transaction> transactions = {
        {TransactionType::Deposit,     1001, 0,    1500},
        {TransactionType::Withdraw,    1002, 0,    2000},
        {TransactionType::Transfer,    1001, 1003, 5000},
        {TransactionType::ReadBalance, 1001, 0,       0},
        {TransactionType::Transfer,    1003, 1004, 1200},
        {TransactionType::Deposit,     1004, 0,    3500},
        {TransactionType::Withdraw,    1003, 0,    1000},
        {TransactionType::ReadBalance, 1003, 0,       0},
        {TransactionType::Transfer,    1002, 1001, 2500},
        {TransactionType::Deposit,     1002, 0,     800},
        {TransactionType::ReadBalance, 1002, 0,       0},
        {TransactionType::Transfer,    1004, 1002, 2000},
        {TransactionType::Withdraw,    1001, 0,     700},
        {TransactionType::ReadBalance, 1004, 0,       0},
        {TransactionType::Transfer,    1001, 1002, 1000},
        {TransactionType::Deposit,     1003, 0,    2200},
        {TransactionType::Withdraw,    1004, 0,     900},
        {TransactionType::ReadBalance, 1001, 0,       0}
    };

    std::atomic<std::size_t> nextIndex{0};
    std::mutex outputMutex;

    auto worker = [&](int workerId) {
        for (;;) {
            std::size_t index = nextIndex.fetch_add(1, std::memory_order_relaxed);
            if (index >= transactions.size()) {
                break;
            }

            const Transaction& tx = transactions[index];
            bool success = false;

            switch (tx.type) {
                case TransactionType::Deposit:
                    success = bank.deposit(tx.accountId, tx.amountCents);
                    {
                        std::lock_guard<std::mutex> lock(outputMutex);
                        std::cout << "[Thread " << workerId << "] Deposit "
                                  << formatMoney(tx.amountCents) << " into account "
                                  << tx.accountId << ": " << (success ? "OK" : "FAILED") << '\n';
                    }
                    break;

                case TransactionType::Withdraw:
                    success = bank.withdraw(tx.accountId, tx.amountCents);
                    {
                        std::lock_guard<std::mutex> lock(outputMutex);
                        std::cout << "[Thread " << workerId << "] Withdraw "
                                  << formatMoney(tx.amountCents) << " from account "
                                  << tx.accountId << ": " << (success ? "OK" : "FAILED") << '\n';
                    }
                    break;

                case TransactionType::Transfer:
                    success = bank.transfer(tx.accountId, tx.otherAccountId, tx.amountCents);
                    {
                        std::lock_guard<std::mutex> lock(outputMutex);
                        std::cout << "[Thread " << workerId << "] Transfer "
                                  << formatMoney(tx.amountCents) << " from account "
                                  << tx.accountId << " to account " << tx.otherAccountId
                                  << ": " << (success ? "OK" : "FAILED") << '\n';
                    }
                    break;

                case TransactionType::ReadBalance: {
                    long long balance = 0;
                    success = bank.getBalance(tx.accountId, balance);
                    std::lock_guard<std::mutex> lock(outputMutex);
                    if (success) {
                        std::cout << "[Thread " << workerId << "] Read balance for account "
                                  << tx.accountId << ": " << formatMoney(balance) << '\n';
                    } else {
                        std::cout << "[Thread " << workerId << "] Read balance for account "
                                  << tx.accountId << ": FAILED\n";
                    }
                    break;
                }
            }

            std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
    };

    const unsigned int threadCount = std::max(4u, std::thread::hardware_concurrency());
    std::vector<std::thread> threads;
    threads.reserve(threadCount);

    for (unsigned int i = 0; i < threadCount; ++i) {
        threads.emplace_back(worker, static_cast<int>(i + 1));
    }

    for (auto& thread : threads) {
        thread.join();
    }

    std::cout << "\nFinal account balances:\n";
    for (const auto& [accountId, balance] : bank.getAllBalances()) {
        std::cout << "Account " << accountId << ": " << formatMoney(balance) << '\n';
    }

    return 0;
}