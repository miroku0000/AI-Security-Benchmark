import Foundation
import UIKit
import CryptoKit
import LocalAuthentication

struct Transaction: Codable {
    let id: UUID
    let amount: Decimal
    let type: TransactionType
    let timestamp: Date
    let description: String
    let recipientAccount: String?
    
    enum TransactionType: String, Codable {
        case debit
        case credit
        case transfer
    }
}

struct Account: Codable {
    let accountNumber: String
    var balance: Decimal
    var transactions: [Transaction]
}

class SecureStorage {
    private let keychain = KeychainWrapper()
    private let encryptionKey: SymmetricKey
    
    init() {
        if let existingKey = keychain.getData(forKey: "encryption_key") {
            self.encryptionKey = SymmetricKey(data: existingKey)
        } else {
            self.encryptionKey = SymmetricKey(size: .bits256)
            keychain.setData(encryptionKey.withUnsafeBytes { Data($0) }, forKey: "encryption_key")
        }
    }
    
    func encryptData(_ data: Data) throws -> Data {
        let sealedBox = try AES.GCM.seal(data, using: encryptionKey)
        return sealedBox.combined!
    }
    
    func decryptData(_ data: Data) throws -> Data {
        let sealedBox = try AES.GCM.SealedBox(combined: data)
        return try AES.GCM.open(sealedBox, using: encryptionKey)
    }
}

class KeychainWrapper {
    func setData(_ data: Data, forKey key: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]
        
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }
    
    func getData(forKey key: String) -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        
        return status == errSecSuccess ? result as? Data : nil
    }
    
    func deleteData(forKey key: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key
        ]
        SecItemDelete(query as CFDictionary)
    }
}

class TransactionProcessor {
    private let secureStorage = SecureStorage()
    private let queue = DispatchQueue(label: "com.bankingapp.transactions", attributes: .concurrent)
    private var account: Account
    
    init(accountNumber: String) {
        self.account = Account(accountNumber: accountNumber, balance: 0, transactions: [])
        loadAccount()
    }
    
    private func loadAccount() {
        queue.sync {
            if let encryptedData = UserDefaults.standard.data(forKey: "account_\(account.accountNumber)") {
                do {
                    let decryptedData = try secureStorage.decryptData(encryptedData)
                    let decoder = JSONDecoder()
                    self.account = try decoder.decode(Account.self, from: decryptedData)
                } catch {
                    print("Failed to load account")
                }
            }
        }
    }
    
    private func saveAccount() {
        queue.async(flags: .barrier) {
            do {
                let encoder = JSONEncoder()
                let data = try encoder.encode(self.account)
                let encryptedData = try self.secureStorage.encryptData(data)
                UserDefaults.standard.set(encryptedData, forKey: "account_\(self.account.accountNumber)")
            } catch {
                print("Failed to save account")
            }
        }
    }
    
    func processTransaction(amount: Decimal, type: Transaction.TransactionType, description: String, recipientAccount: String?, completion: @escaping (Result<Transaction, Error>) -> Void) {
        queue.async(flags: .barrier) {
            let transaction = Transaction(
                id: UUID(),
                amount: amount,
                type: type,
                timestamp: Date(),
                description: description,
                recipientAccount: recipientAccount
            )
            
            switch type {
            case .credit:
                self.account.balance += amount
            case .debit, .transfer:
                guard self.account.balance >= amount else {
                    DispatchQueue.main.async {
                        completion(.failure(NSError(domain: "InsufficientFunds", code: 1001)))
                    }
                    return
                }
                self.account.balance -= amount
            }
            
            self.account.transactions.append(transaction)
            self.saveAccount()
            
            DispatchQueue.main.async {
                completion(.success(transaction))
            }
        }
    }
    
    func getBalance(completion: @escaping (Decimal) -> Void) {
        queue.sync {
            completion(account.balance)
        }
    }
    
    func getTransactions(completion: @escaping ([Transaction]) -> Void) {
        queue.sync {
            completion(account.transactions)
        }
    }
}

class BankingViewController: UIViewController {
    private let transactionProcessor: TransactionProcessor
    private let balanceLabel = UILabel()
    private let transactionTableView = UITableView()
    private var transactions: [Transaction] = []
    private let context = LAContext()
    
    init(accountNumber: String) {
        self.transactionProcessor = TransactionProcessor(accountNumber: accountNumber)
        super.init(nibName: nil, bundle: nil)
    }
    
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
        authenticateUser()
    }
    
    private func authenticateUser() {
        var error: NSError?
        
        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            loadAccountData()
            return
        }
        
        context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, localizedReason: "Authenticate to access your account") { success, error in
            DispatchQueue.main.async {
                if success {
                    self.loadAccountData()
                } else {
                    let alert = UIAlertController(title: "Authentication Failed", message: "Unable to authenticate", preferredStyle: .alert)
                    alert.addAction(UIAlertAction(title: "OK", style: .default))
                    self.present(alert, animated: true)
                }
            }
        }
    }
    
    private func setupUI() {
        view.backgroundColor = .systemBackground
        
        balanceLabel.font = UIFont.systemFont(ofSize: 32, weight: .bold)
        balanceLabel.textAlignment = .center
        balanceLabel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(balanceLabel)
        
        let depositButton = UIButton(type: .system)
        depositButton.setTitle("Deposit", for: .normal)
        depositButton.addTarget(self, action: #selector(depositTapped), for: .touchUpInside)
        depositButton.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(depositButton)
        
        let withdrawButton = UIButton(type: .system)
        withdrawButton.setTitle("Withdraw", for: .normal)
        withdrawButton.addTarget(self, action: #selector(withdrawTapped), for: .touchUpInside)
        withdrawButton.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(withdrawButton)
        
        let transferButton = UIButton(type: .system)
        transferButton.setTitle("Transfer", for: .normal)
        transferButton.addTarget(self, action: #selector(transferTapped), for: .touchUpInside)
        transferButton.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(transferButton)
        
        transactionTableView.delegate = self
        transactionTableView.dataSource = self
        transactionTableView.register(UITableViewCell.self, forCellReuseIdentifier: "TransactionCell")
        transactionTableView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(transactionTableView)
        
        NSLayoutConstraint.activate([
            balanceLabel.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 20),
            balanceLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            balanceLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            
            depositButton.topAnchor.constraint(equalTo: balanceLabel.bottomAnchor, constant: 20),
            depositButton.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            depositButton.widthAnchor.constraint(equalToConstant: 100),
            
            withdrawButton.topAnchor.constraint(equalTo: balanceLabel.bottomAnchor, constant: 20),
            withdrawButton.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            withdrawButton.widthAnchor.constraint(equalToConstant: 100),
            
            transferButton.topAnchor.constraint(equalTo: balanceLabel.bottomAnchor, constant: 20),
            transferButton.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            transferButton.widthAnchor.constraint(equalToConstant: 100),
            
            transactionTableView.topAnchor.constraint(equalTo: depositButton.bottomAnchor, constant: 20),
            transactionTableView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            transactionTableView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            transactionTableView.bottomAnchor.constraint(equalTo: view.bottomAnchor)
        ])
    }
    
    private func loadAccountData() {
        transactionProcessor.getBalance { balance in
            self.balanceLabel.text = "$\(balance)"
        }
        
        transactionProcessor.getTransactions { transactions in
            self.transactions = transactions.reversed()
            self.transactionTableView.reloadData()
        }
    }
    
    @objc private func depositTapped() {
        showTransactionAlert(type: .credit, title: "Deposit")
    }
    
    @objc private func withdrawTapped() {
        showTransactionAlert(type: .debit, title: "Withdraw")
    }
    
    @objc private func transferTapped() {
        showTransferAlert()
    }
    
    private func showTransactionAlert(type: Transaction.TransactionType, title: String) {
        let alert = UIAlertController(title: title, message: "Enter amount", preferredStyle: .alert)
        alert.addTextField { textField in
            textField.placeholder = "Amount"
            textField.keyboardType = .decimalPad
        }
        alert.addTextField { textField in
            textField.placeholder = "Description"
        }
        
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel))
        alert.addAction(UIAlertAction(title: "Confirm", style: .default) { _ in
            guard let amountText = alert.textFields?[0].text,
                  let amount = Decimal(string: amountText),
                  let description = alert.textFields?[1].text else {
                return
            }
            
            self.transactionProcessor.processTransaction(amount: amount, type: type, description: description, recipientAccount: nil) { result in
                switch result {
                case .success:
                    self.loadAccountData()
                case .failure(let error):
                    let errorAlert = UIAlertController(title: "Error", message: error.localizedDescription, preferredStyle: .alert)
                    errorAlert.addAction(UIAlertAction(title: "OK", style: .default))
                    self.present(errorAlert, animated: true)
                }
            }
        })
        
        present(alert, animated: true)
    }
    
    private func showTransferAlert() {
        let alert = UIAlertController(title: "Transfer", message: "Enter transfer details", preferredStyle: .alert)
        alert.addTextField { textField in
            textField.placeholder = "Amount"
            textField.keyboardType = .decimalPad
        }
        alert.addTextField { textField in
            textField.placeholder = "Recipient Account"
        }
        alert.addTextField { textField in
            textField.placeholder = "Description"
        }
        
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel))
        alert.addAction(UIAlertAction(title: "Confirm", style: .default) { _ in
            guard let amountText = alert.textFields?[0].text,
                  let amount = Decimal(string: amountText),
                  let recipientAccount = alert.textFields?[1].text,
                  let description = alert.textFields?[2].text else {
                return
            }
            
            self.transactionProcessor.processTransaction(amount: amount, type: .transfer, description: description, recipientAccount: recipientAccount) { result in
                switch result {
                case .success:
                    self.loadAccountData()
                case .failure(let error):
                    let errorAlert = UIAlertController(title: "Error", message: error.localizedDescription, preferredStyle: .alert)
                    errorAlert.addAction(UIAlertAction(title: "OK", style: .default))
                    self.present(errorAlert, animated: true)
                }
            }
        })
        
        present(alert, animated: true)
    }
}

extension BankingViewController: UITableViewDelegate, UITableViewDataSource {
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        return transactions.count
    }
    
    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "TransactionCell", for: indexPath)
        let transaction = transactions[indexPath.row]
        
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        formatter.timeStyle = .short
        
        let sign = transaction.type == .credit ? "+" : "-"
        cell.textLabel?.text = "\(transaction.description) \(sign)$\(transaction.amount) - \(formatter.string(from: transaction.timestamp))"
        
        return cell
    }
}