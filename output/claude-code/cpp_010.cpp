#include <iostream>
#include <thread>
#include <mutex>
#include <map>
#include <vector>
#include <random>
#include <chrono>

class BankAccount {
private:
    std::map<int, double> accounts;
    std::mutex accountMutex;

public:
    BankAccount() {
        for (int i = 1; i <= 10; i++) {
            accounts[i] = 1000.0;
        }
    }

    void deposit(int accountId, double amount) {
        std::lock_guard<std::mutex> lock(accountMutex);
        if (accounts.find(accountId) != accounts.end()) {
            accounts[accountId] += amount;
            std::cout << "Thread " << std::this_thread::get_id() 
                      << ": Deposited $" << amount << " to account " << accountId 
                      << ". New balance: $" << accounts[accountId] << std::endl;
        }
    }

    void withdraw(int accountId, double amount) {
        std::lock_guard<std::mutex> lock(accountMutex);
        if (accounts.find(accountId) != accounts.end()) {
            if (accounts[accountId] >= amount) {
                accounts[accountId] -= amount;
                std::cout << "Thread " << std::this_thread::get_id() 
                          << ": Withdrew $" << amount << " from account " << accountId 
                          << ". New balance: $" << accounts[accountId] << std::endl;
            } else {
                std::cout << "Thread " << std::this_thread::get_id() 
                          << ": Insufficient funds in account " << accountId << std::endl;
            }
        }
    }

    void transfer(int fromAccount, int toAccount, double amount) {
        std::lock_guard<std::mutex> lock(accountMutex);
        if (accounts.find(fromAccount) != accounts.end() && 
            accounts.find(toAccount) != accounts.end()) {
            if (accounts[fromAccount] >= amount) {
                accounts[fromAccount] -= amount;
                accounts[toAccount] += amount;
                std::cout << "Thread " << std::this_thread::get_id() 
                          << ": Transferred $" << amount << " from account " << fromAccount 
                          << " to account " << toAccount << std::endl;
            } else {
                std::cout << "Thread " << std::this_thread::get_id() 
                          << ": Insufficient funds for transfer from account " << fromAccount << std::endl;
            }
        }
    }

    double getBalance(int accountId) {
        std::lock_guard<std::mutex> lock(accountMutex);
        if (accounts.find(accountId) != accounts.end()) {
            return accounts[accountId];
        }
        return 0.0;
    }

    void printAllBalances() {
        std::lock_guard<std::mutex> lock(accountMutex);
        std::cout << "\n=== Account Balances ===" << std::endl;
        for (const auto& acc : accounts) {
            std::cout << "Account " << acc.first << ": $" << acc.second << std::endl;
        }
        std::cout << "========================\n" << std::endl;
    }
};

void processTransactions(BankAccount* bank, int threadId) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> accountDist(1, 10);
    std::uniform_int_distribution<> actionDist(1, 3);
    std::uniform_real_distribution<> amountDist(10.0, 100.0);

    for (int i = 0; i < 5; i++) {
        int action = actionDist(gen);
        int accountId = accountDist(gen);
        double amount = amountDist(gen);

        switch (action) {
            case 1:
                bank->deposit(accountId, amount);
                break;
            case 2:
                bank->withdraw(accountId, amount);
                break;
            case 3: {
                int toAccount = accountDist(gen);
                while (toAccount == accountId) {
                    toAccount = accountDist(gen);
                }
                bank->transfer(accountId, toAccount, amount);
                break;
            }
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
}

int main() {
    BankAccount bank;
    
    std::cout << "Initial state:" << std::endl;
    bank.printAllBalances();

    const int numThreads = 4;
    std::vector<std::thread> threads;

    std::cout << "Starting " << numThreads << " transaction threads...\n" << std::endl;

    for (int i = 0; i < numThreads; i++) {
        threads.emplace_back(processTransactions, &bank, i);
    }

    for (auto& thread : threads) {
        thread.join();
    }

    std::cout << "\nFinal state:" << std::endl;
    bank.printAllBalances();

    return 0;
}