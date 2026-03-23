#include <iostream>
#include <thread>
#include <mutex>
#include <unordered_map>
#include <vector>
#include <random>
#include <chrono>
#include <iomanip>

class BankAccount {
private:
    double balance;
    mutable std::mutex account_mutex;
    
public:
    BankAccount(double initial_balance = 0.0) : balance(initial_balance) {}
    
    void deposit(double amount) {
        std::lock_guard<std::mutex> lock(account_mutex);
        balance += amount;
    }
    
    bool withdraw(double amount) {
        std::lock_guard<std::mutex> lock(account_mutex);
        if (balance >= amount) {
            balance -= amount;
            return true;
        }
        return false;
    }
    
    double get_balance() const {
        std::lock_guard<std::mutex> lock(account_mutex);
        return balance;
    }
    
    bool transfer_to(BankAccount& target, double amount) {
        std::unique_lock<std::mutex> lock1(account_mutex, std::defer_lock);
        std::unique_lock<std::mutex> lock2(target.account_mutex, std::defer_lock);
        std::lock(lock1, lock2);
        
        if (balance >= amount) {
            balance -= amount;
            target.balance += amount;
            return true;
        }
        return false;
    }
};

class Bank {
private:
    std::unordered_map<int, BankAccount> accounts;
    mutable std::mutex bank_mutex;
    
public:
    void create_account(int account_id, double initial_balance) {
        std::lock_guard<std::mutex> lock(bank_mutex);
        accounts.emplace(account_id, BankAccount(initial_balance));
    }
    
    BankAccount* get_account(int account_id) {
        std::lock_guard<std::mutex> lock(bank_mutex);
        auto it = accounts.find(account_id);
        if (it != accounts.end()) {
            return &(it->second);
        }
        return nullptr;
    }
    
    void print_all_balances() const {
        std::lock_guard<std::mutex> lock(bank_mutex);
        std::cout << "\n=== Account Balances ===" << std::endl;
        for (const auto& [id, account] : accounts) {
            std::cout << "Account " << id << ": $" << std::fixed 
                     << std::setprecision(2) << account.get_balance() << std::endl;
        }
        std::cout << "========================\n" << std::endl;
    }
    
    double get_total_balance() const {
        std::lock_guard<std::mutex> lock(bank_mutex);
        double total = 0.0;
        for (const auto& [id, account] : accounts) {
            total += account.get_balance();
        }
        return total;
    }
};

void process_deposits(Bank& bank, int thread_id, int num_transactions) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> account_dist(1, 5);
    std::uniform_real_distribution<> amount_dist(10.0, 500.0);
    
    for (int i = 0; i < num_transactions; ++i) {
        int account_id = account_dist(gen);
        double amount = amount_dist(gen);
        
        BankAccount* account = bank.get_account(account_id);
        if (account) {
            account->deposit(amount);
            std::cout << "Thread " << thread_id << " deposited $" 
                     << std::fixed << std::setprecision(2) << amount 
                     << " to account " << account_id << std::endl;
        }
        
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

void process_withdrawals(Bank& bank, int thread_id, int num_transactions) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> account_dist(1, 5);
    std::uniform_real_distribution<> amount_dist(5.0, 200.0);
    
    for (int i = 0; i < num_transactions; ++i) {
        int account_id = account_dist(gen);
        double amount = amount_dist(gen);
        
        BankAccount* account = bank.get_account(account_id);
        if (account) {
            if (account->withdraw(amount)) {
                std::cout << "Thread " << thread_id << " withdrew $" 
                         << std::fixed << std::setprecision(2) << amount 
                         << " from account " << account_id << std::endl;
            } else {
                std::cout << "Thread " << thread_id << " failed to withdraw $" 
                         << std::fixed << std::setprecision(2) << amount 
                         << " from account " << account_id << " (insufficient funds)" << std::endl;
            }
        }
        
        std::this_thread::sleep_for(std::chrono::milliseconds(15));
    }
}

void process_transfers(Bank& bank, int thread_id, int num_transactions) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> account_dist(1, 5);
    std::uniform_real_distribution<> amount_dist(10.0, 300.0);
    
    for (int i = 0; i < num_transactions; ++i) {
        int from_account_id = account_dist(gen);
        int to_account_id = account_dist(gen);
        
        while (to_account_id == from_account_id) {
            to_account_id = account_dist(gen);
        }
        
        double amount = amount_dist(gen);
        
        BankAccount* from_account = bank.get_account(from_account_id);
        BankAccount* to_account = bank.get_account(to_account_id);
        
        if (from_account && to_account) {
            if (from_account->transfer_to(*to_account, amount)) {
                std::cout << "Thread " << thread_id << " transferred $" 
                         << std::fixed << std::setprecision(2) << amount 
                         << " from account " << from_account_id 
                         << " to account " << to_account_id << std::endl;
            } else {
                std::cout << "Thread " << thread_id << " failed to transfer $" 
                         << std::fixed << std::setprecision(2) << amount 
                         << " from account " << from_account_id 
                         << " (insufficient funds)" << std::endl;
            }
        }
        
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
}

void balance_reader(Bank& bank, int thread_id, int num_reads) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> account_dist(1, 5);
    
    for (int i = 0; i < num_reads; ++i) {
        int account_id = account_dist(gen);
        BankAccount* account = bank.get_account(account_id);
        
        if (account) {
            double balance = account->get_balance();
            std::cout << "Thread " << thread_id << " read balance of account " 
                     << account_id << ": $" << std::fixed << std::setprecision(2) 
                     << balance << std::endl;
        }
        
        std::this_thread::sleep_for(std::chrono::milliseconds(25));
    }
}

int main() {
    Bank bank;
    
    std::cout << "Initializing bank accounts..." << std::endl;
    for (int i = 1; i <= 5; ++i) {
        bank.create_account(i, 1000.0);
    }
    
    bank.print_all_balances();
    double initial_total = bank.get_total_balance();
    std::cout << "Initial total balance: $" << std::fixed 
             << std::setprecision(2) << initial_total << std::endl;
    
    std::vector<std::thread> threads;
    
    std::cout << "\nStarting concurrent transactions...\n" << std::endl;
    
    threads.emplace_back(process_deposits, std::ref(bank), 1, 10);
    threads.emplace_back(process_deposits, std::ref(bank), 2, 10);
    
    threads.emplace_back(process_withdrawals, std::ref(bank), 3, 10);
    threads.emplace_back(process_withdrawals, std::ref(bank), 4, 10);
    
    threads.emplace_back(process_transfers, std::ref(bank), 5, 8);
    threads.emplace_back(process_transfers, std::ref(bank), 6, 8);
    
    threads.emplace_back(balance_reader, std::ref(bank), 7, 15);
    threads.emplace_back(balance_reader, std::ref(bank), 8, 15);
    
    for (auto& thread : threads) {
        thread.join();
    }
    
    std::cout << "\nAll transactions completed." << std::endl;
    
    bank.print_all_balances();
    
    double final_total = bank.get_total_balance();
    std::cout << "Final total balance: $" << std::fixed 
             << std::setprecision(2) << final_total << std::endl;
    
    std::cout << "\nNet change in total balance: $" << std::fixed 
             << std::setprecision(2) << (final_total - initial_total) 
             << " (from deposits minus withdrawals)" << std::endl;
    
    return 0;
}