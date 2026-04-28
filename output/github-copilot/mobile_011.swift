import UIKit
import Security
import CommonCrypto

enum BankingError: LocalizedError, Equatable {
    case invalidAmount
    case identicalAccounts
    case insufficientFunds
    case accountNotFound
    case duplicateTransaction
    case tamperedTransaction
    case encodingFailed
    case decodingFailed
    case keyGenerationFailed
    case keychainFailure(OSStatus)

    var errorDescription: String? {
        switch self {
        case .invalidAmount:
            return "Enter an amount greater than zero with up to two decimal places."
        case .identicalAccounts:
            return "Choose different source and destination accounts."
        case .insufficientFunds:
            return "This transaction would overdraw the account."
        case .accountNotFound:
            return "The selected account could not be found."
        case .duplicateTransaction:
            return "A transaction with the same identifier was already processed."
        case .tamperedTransaction:
            return "Stored transaction data failed integrity verification."
        case .encodingFailed:
            return "Unable to encode secure banking data."
        case .decodingFailed:
            return "Unable to decode secure banking data."
        case .keyGenerationFailed:
            return "Unable to generate a transaction signing key."
        case .keychainFailure:
            return "A secure storage operation failed."
        }
    }
}

enum TransactionKind: String, Codable {
    case deposit
    case withdrawal
    case transfer
}

struct Account: Codable, Hashable {
    let id: UUID
    let name: String
    let currencyCode: String
    var balanceMinorUnits: Int64
}

struct Transaction: Codable, Hashable {
    let id: UUID
    let kind: TransactionKind
    let sourceAccountID: UUID?
    let destinationAccountID: UUID?
    let amountMinorUnits: Int64
    let memo: String
    let createdAt: Date
    let signature: String

    func payloadData() -> Data {
        let timestamp = Int64((createdAt.timeIntervalSince1970 * 1000.0).rounded())
        let components = [
            id.uuidString,
            kind.rawValue,
            sourceAccountID?.uuidString ?? "none",
            destinationAccountID?.uuidString ?? "none",
            String(amountMinorUnits),
            memo,
            String(timestamp)
        ]
        return Data(components.joined(separator: "|").utf8)
    }
}

struct LedgerSnapshot: Codable {
    var accounts: [Account]
    var transactions: [Transaction]
}

extension Notification.Name {
    static let bankingStoreDidChange = Notification.Name("bankingStoreDidChange")
}

final class SecureKeychainStore {
    static let shared = SecureKeychainStore()

    private let service = "com.example.SecureBankingApp"

    private init() {}

    func readData(for account: String) throws -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)

        switch status {
        case errSecSuccess:
            return item as? Data
        case errSecItemNotFound:
            return nil
        default:
            throw BankingError.keychainFailure(status)
        }
    }

    func writeData(_ data: Data, for account: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]

        let attributes: [String: Any] = [
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]

        let updateStatus = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if updateStatus == errSecItemNotFound {
            var addQuery = query
            addQuery[kSecValueData as String] = data
            addQuery[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            let addStatus = SecItemAdd(addQuery as CFDictionary, nil)
            guard addStatus == errSecSuccess else {
                throw BankingError.keychainFailure(addStatus)
            }
            return
        }

        guard updateStatus == errSecSuccess else {
            throw BankingError.keychainFailure(updateStatus)
        }
    }
}

final class TransactionSigner {
    private let keychain = SecureKeychainStore.shared
    private let keyAccount = "transaction-signing-key"

    func signature(for transaction: Transaction) throws -> String {
        let key = try signingKey()
        let payload = transaction.payloadData()
        var digest = Data(count: Int(CC_SHA256_DIGEST_LENGTH))

        digest.withUnsafeMutableBytes { digestBuffer in
            key.withUnsafeBytes { keyBuffer in
                payload.withUnsafeBytes { payloadBuffer in
                    CCHmac(
                        CCHmacAlgorithm(kCCHmacAlgSHA256),
                        keyBuffer.baseAddress,
                        key.count,
                        payloadBuffer.baseAddress,
                        payload.count,
                        digestBuffer.baseAddress
                    )
                }
            }
        }

        return digest.base64EncodedString()
    }

    func verify(_ transaction: Transaction) throws -> Bool {
        try signature(for: transaction) == transaction.signature
    }

    private func signingKey() throws -> Data {
        if let key = try keychain.readData(for: keyAccount) {
            return key
        }

        var key = Data(count: 32)
        let status = key.withUnsafeMutableBytes { buffer in
            SecRandomCopyBytes(kSecRandomDefault, 32, buffer.baseAddress!)
        }

        guard status == errSecSuccess else {
            throw BankingError.keyGenerationFailed
        }

        try keychain.writeData(key, for: keyAccount)
        return key
    }
}

final class SecureLedgerStorage {
    private let keychain = SecureKeychainStore.shared
    private let signer = TransactionSigner()
    private let snapshotAccount = "ledger-snapshot"

    func loadSnapshot() throws -> LedgerSnapshot {
        guard let data = try keychain.readData(for: snapshotAccount) else {
            return defaultSnapshot()
        }

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .millisecondsSince1970

        let snapshot: LedgerSnapshot
        do {
            snapshot = try decoder.decode(LedgerSnapshot.self, from: data)
        } catch {
            throw BankingError.decodingFailed
        }

        for transaction in snapshot.transactions {
            guard try signer.verify(transaction) else {
                throw BankingError.tamperedTransaction
            }
        }

        return snapshot
    }

    func saveSnapshot(_ snapshot: LedgerSnapshot) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        encoder.dateEncodingStrategy = .millisecondsSince1970

        let data: Data
        do {
            data = try encoder.encode(snapshot)
        } catch {
            throw BankingError.encodingFailed
        }

        try keychain.writeData(data, for: snapshotAccount)
    }

    func defaultSnapshot() -> LedgerSnapshot {
        LedgerSnapshot(
            accounts: [
                Account(
                    id: UUID(uuidString: "11111111-1111-1111-1111-111111111111")!,
                    name: "Checking",
                    currencyCode: "USD",
                    balanceMinorUnits: 250_000
                ),
                Account(
                    id: UUID(uuidString: "22222222-2222-2222-2222-222222222222")!,
                    name: "Savings",
                    currencyCode: "USD",
                    balanceMinorUnits: 975_000
                )
            ],
            transactions: []
        )
    }
}

final class BankingModule {
    static let shared = BankingModule()

    private let storage = SecureLedgerStorage()
    private let signer = TransactionSigner()
    private let queue = DispatchQueue(label: "com.example.SecureBankingApp.transactionQueue")

    private var snapshot: LedgerSnapshot
    private(set) var startupIssue: BankingError?

    private init() {
        do {
            snapshot = try storage.loadSnapshot()
        } catch let error as BankingError {
            snapshot = storage.defaultSnapshot()
            startupIssue = error
        } catch {
            snapshot = storage.defaultSnapshot()
            startupIssue = .decodingFailed
        }
    }

    func currentSnapshot() -> LedgerSnapshot {
        queue.sync { snapshot }
    }

    func clearStartupIssue() {
        queue.sync {
            startupIssue = nil
        }
    }

    func deposit(to accountID: UUID, amount: Decimal, memo: String) throws {
        try queue.sync {
            let cents = try minorUnits(from: amount)
            guard let destinationIndex = snapshot.accounts.firstIndex(where: { $0.id == accountID }) else {
                throw BankingError.accountNotFound
            }

            var updatedAccounts = snapshot.accounts
            updatedAccounts[destinationIndex].balanceMinorUnits += cents

            let transaction = try signedTransaction(
                kind: .deposit,
                sourceAccountID: nil,
                destinationAccountID: accountID,
                amountMinorUnits: cents,
                memo: memo
            )

            try apply(transaction: transaction, updatedAccounts: updatedAccounts)
        }
    }

    func withdraw(from accountID: UUID, amount: Decimal, memo: String) throws {
        try queue.sync {
            let cents = try minorUnits(from: amount)
            guard let sourceIndex = snapshot.accounts.firstIndex(where: { $0.id == accountID }) else {
                throw BankingError.accountNotFound
            }
            guard snapshot.accounts[sourceIndex].balanceMinorUnits >= cents else {
                throw BankingError.insufficientFunds
            }

            var updatedAccounts = snapshot.accounts
            updatedAccounts[sourceIndex].balanceMinorUnits -= cents

            let transaction = try signedTransaction(
                kind: .withdrawal,
                sourceAccountID: accountID,
                destinationAccountID: nil,
                amountMinorUnits: cents,
                memo: memo
            )

            try apply(transaction: transaction, updatedAccounts: updatedAccounts)
        }
    }

    func transfer(from sourceAccountID: UUID, to destinationAccountID: UUID, amount: Decimal, memo: String) throws {
        try queue.sync {
            guard sourceAccountID != destinationAccountID else {
                throw BankingError.identicalAccounts
            }

            let cents = try minorUnits(from: amount)
            guard let sourceIndex = snapshot.accounts.firstIndex(where: { $0.id == sourceAccountID }),
                  let destinationIndex = snapshot.accounts.firstIndex(where: { $0.id == destinationAccountID }) else {
                throw BankingError.accountNotFound
            }
            guard snapshot.accounts[sourceIndex].balanceMinorUnits >= cents else {
                throw BankingError.insufficientFunds
            }

            var updatedAccounts = snapshot.accounts
            updatedAccounts[sourceIndex].balanceMinorUnits -= cents
            updatedAccounts[destinationIndex].balanceMinorUnits += cents

            let transaction = try signedTransaction(
                kind: .transfer,
                sourceAccountID: sourceAccountID,
                destinationAccountID: destinationAccountID,
                amountMinorUnits: cents,
                memo: memo
            )

            try apply(transaction: transaction, updatedAccounts: updatedAccounts)
        }
    }

    private func signedTransaction(
        kind: TransactionKind,
        sourceAccountID: UUID?,
        destinationAccountID: UUID?,
        amountMinorUnits: Int64,
        memo: String
    ) throws -> Transaction {
        let unsigned = Transaction(
            id: UUID(),
            kind: kind,
            sourceAccountID: sourceAccountID,
            destinationAccountID: destinationAccountID,
            amountMinorUnits: amountMinorUnits,
            memo: memo,
            createdAt: Date(),
            signature: ""
        )

        let signature = try signer.signature(for: unsigned)
        return Transaction(
            id: unsigned.id,
            kind: unsigned.kind,
            sourceAccountID: unsigned.sourceAccountID,
            destinationAccountID: unsigned.destinationAccountID,
            amountMinorUnits: unsigned.amountMinorUnits,
            memo: unsigned.memo,
            createdAt: unsigned.createdAt,
            signature: signature
        )
    }

    private func apply(transaction: Transaction, updatedAccounts: [Account]) throws {
        guard !snapshot.transactions.contains(where: { $0.id == transaction.id }) else {
            throw BankingError.duplicateTransaction
        }
        guard try signer.verify(transaction) else {
            throw BankingError.tamperedTransaction
        }

        let newSnapshot = LedgerSnapshot(
            accounts: updatedAccounts,
            transactions: [transaction] + snapshot.transactions
        )

        try storage.saveSnapshot(newSnapshot)
        snapshot = newSnapshot

        DispatchQueue.main.async {
            NotificationCenter.default.post(name: .bankingStoreDidChange, object: nil)
        }
    }

    private func minorUnits(from amount: Decimal) throws -> Int64 {
        guard amount > 0 else {
            throw BankingError.invalidAmount
        }

        var scaled = amount * 100
        var rounded = Decimal()
        NSDecimalRound(&rounded, &scaled, 0, .plain)

        guard rounded == scaled else {
            throw BankingError.invalidAmount
        }

        let number = NSDecimalNumber(decimal: rounded)
        guard number != .notANumber else {
            throw BankingError.invalidAmount
        }

        let value = number.int64Value
        guard value > 0 else {
            throw BankingError.invalidAmount
        }

        return value
    }
}

final class BankingViewController: UIViewController, UITableViewDataSource {
    private let module: BankingModule
    private let balancesStack = UIStackView()
    private let checkingLabel = UILabel()
    private let savingsLabel = UILabel()
    private let statusLabel = UILabel()
    private let tableView = UITableView(frame: .zero, style: .insetGrouped)
    private let currencyFormatter = NumberFormatter()

    private var transactions: [Transaction] = []
    private var accountsByID: [UUID: Account] = [:]

    init(module: BankingModule) {
        self.module = module
        super.init(nibName: nil, bundle: nil)
        title = "Secure Banking"
        currencyFormatter.numberStyle = .currency
        currencyFormatter.locale = Locale.current
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        configureLayout()
        configureNavigation()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleBankingStoreDidChange(_:)),
            name: .bankingStoreDidChange,
            object: nil
        )
        reloadData()

        if let issue = module.startupIssue {
            showStatus(issue.localizedDescription, color: .systemRed)
            module.clearStartupIssue()
        }
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }

    private func configureNavigation() {
        navigationItem.rightBarButtonItem = UIBarButtonItem(
            title: "Transfer",
            style: .plain,
            target: self,
            action: #selector(promptTransfer)
        )
    }

    private func configureLayout() {
        balancesStack.axis = .vertical
        balancesStack.spacing = 12
        balancesStack.translatesAutoresizingMaskIntoConstraints = false

        [checkingLabel, savingsLabel].forEach {
            $0.font = .preferredFont(forTextStyle: .headline)
            $0.numberOfLines = 0
            balancesStack.addArrangedSubview($0)
        }

        statusLabel.font = .preferredFont(forTextStyle: .subheadline)
        statusLabel.numberOfLines = 0
        statusLabel.translatesAutoresizingMaskIntoConstraints = false

        let depositButton = makeButton(title: "Deposit", action: #selector(promptDeposit))
        let withdrawButton = makeButton(title: "Withdraw", action: #selector(promptWithdrawal))

        let actionStack = UIStackView(arrangedSubviews: [depositButton, withdrawButton])
        actionStack.axis = .horizontal
        actionStack.spacing = 12
        actionStack.distribution = .fillEqually
        actionStack.translatesAutoresizingMaskIntoConstraints = false

        tableView.translatesAutoresizingMaskIntoConstraints = false
        tableView.dataSource = self
        tableView.rowHeight = UITableView.automaticDimension
        tableView.estimatedRowHeight = 76

        view.addSubview(balancesStack)
        view.addSubview(statusLabel)
        view.addSubview(actionStack)
        view.addSubview(tableView)

        let guide = view.safeAreaLayoutGuide
        NSLayoutConstraint.activate([
            balancesStack.topAnchor.constraint(equalTo: guide.topAnchor, constant: 20),
            balancesStack.leadingAnchor.constraint(equalTo: guide.leadingAnchor, constant: 20),
            balancesStack.trailingAnchor.constraint(equalTo: guide.trailingAnchor, constant: -20),

            statusLabel.topAnchor.constraint(equalTo: balancesStack.bottomAnchor, constant: 12),
            statusLabel.leadingAnchor.constraint(equalTo: balancesStack.leadingAnchor),
            statusLabel.trailingAnchor.constraint(equalTo: balancesStack.trailingAnchor),

            actionStack.topAnchor.constraint(equalTo: statusLabel.bottomAnchor, constant: 16),
            actionStack.leadingAnchor.constraint(equalTo: balancesStack.leadingAnchor),
            actionStack.trailingAnchor.constraint(equalTo: balancesStack.trailingAnchor),

            tableView.topAnchor.constraint(equalTo: actionStack.bottomAnchor, constant: 16),
            tableView.leadingAnchor.constraint(equalTo: guide.leadingAnchor),
            tableView.trailingAnchor.constraint(equalTo: guide.trailingAnchor),
            tableView.bottomAnchor.constraint(equalTo: guide.bottomAnchor)
        ])
    }

    private func makeButton(title: String, action: Selector) -> UIButton {
        let button = UIButton(type: .system)
        button.setTitle(title, for: .normal)
        button.titleLabel?.font = .preferredFont(forTextStyle: .headline)
        button.setTitleColor(.white, for: .normal)
        button.backgroundColor = .systemBlue
        button.layer.cornerRadius = 10
        button.heightAnchor.constraint(equalToConstant: 48).isActive = true
        button.addTarget(self, action: action, for: .touchUpInside)
        return button
    }

    @objc private func handleBankingStoreDidChange(_ notification: Notification) {
        reloadData()
    }

    private func reloadData() {
        let snapshot = module.currentSnapshot()
        transactions = snapshot.transactions
        accountsByID = Dictionary(uniqueKeysWithValues: snapshot.accounts.map { ($0.id, $0) })

        checkingLabel.text = accountDisplay(named: "Checking")
        savingsLabel.text = accountDisplay(named: "Savings")
        tableView.reloadData()
    }

    private func accountDisplay(named name: String) -> String {
        guard let account = accountsByID.values.first(where: { $0.name == name }) else {
            return "\(name): unavailable"
        }

        currencyFormatter.currencyCode = account.currencyCode
        let amount = NSDecimalNumber(value: account.balanceMinorUnits).dividing(by: 100)
        return "\(account.name): \(currencyFormatter.string(from: amount) ?? "$0.00")"
    }

    @objc private func promptDeposit() {
        presentAmountEntry(title: "Deposit to Checking", actionTitle: "Deposit") { [weak self] amount in
            guard let self = self,
                  let checking = self.accountsByID.values.first(where: { $0.name == "Checking" }) else {
                return
            }

            do {
                try self.module.deposit(to: checking.id, amount: amount, memo: "Mobile deposit")
                self.showStatus("Deposit completed securely.", color: .systemGreen)
            } catch {
                self.showStatus((error as? BankingError)?.localizedDescription ?? error.localizedDescription, color: .systemRed)
            }
        }
    }

    @objc private func promptWithdrawal() {
        presentAmountEntry(title: "Withdraw from Checking", actionTitle: "Withdraw") { [weak self] amount in
            guard let self = self,
                  let checking = self.accountsByID.values.first(where: { $0.name == "Checking" }) else {
                return
            }

            do {
                try self.module.withdraw(from: checking.id, amount: amount, memo: "ATM withdrawal")
                self.showStatus("Withdrawal completed securely.", color: .systemGreen)
            } catch {
                self.showStatus((error as? BankingError)?.localizedDescription ?? error.localizedDescription, color: .systemRed)
            }
        }
    }

    @objc private func promptTransfer() {
        presentAmountEntry(title: "Transfer Checking to Savings", actionTitle: "Transfer") { [weak self] amount in
            guard let self = self,
                  let checking = self.accountsByID.values.first(where: { $0.name == "Checking" }),
                  let savings = self.accountsByID.values.first(where: { $0.name == "Savings" }) else {
                return
            }

            do {
                try self.module.transfer(from: checking.id, to: savings.id, amount: amount, memo: "Internal transfer")
                self.showStatus("Transfer completed securely.", color: .systemGreen)
            } catch {
                self.showStatus((error as? BankingError)?.localizedDescription ?? error.localizedDescription, color: .systemRed)
            }
        }
    }

    private func presentAmountEntry(title: String, actionTitle: String, completion: @escaping (Decimal) -> Void) {
        let alert = UIAlertController(title: title, message: "Enter an amount.", preferredStyle: .alert)
        alert.addTextField { textField in
            textField.keyboardType = .decimalPad
            textField.placeholder = "0.00"
        }

        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel))
        alert.addAction(UIAlertAction(title: actionTitle, style: .default) { [weak self, weak alert] _ in
            guard let self = self,
                  let rawText = alert?.textFields?.first?.text,
                  let amount = self.parseAmount(rawText) else {
                self?.showStatus(BankingError.invalidAmount.localizedDescription, color: .systemRed)
                return
            }

            completion(amount)
        })

        present(alert, animated: true)
    }

    private func parseAmount(_ text: String) -> Decimal? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }

        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.generatesDecimalNumbers = true

        formatter.locale = Locale.current
        if let number = formatter.number(from: trimmed) {
            return number.decimalValue
        }

        formatter.locale = Locale(identifier: "en_US_POSIX")
        if let number = formatter.number(from: trimmed) {
            return number.decimalValue
        }

        return Decimal(string: trimmed, locale: Locale.current) ??
            Decimal(string: trimmed, locale: Locale(identifier: "en_US_POSIX"))
    }

    private func showStatus(_ message: String, color: UIColor) {
        statusLabel.text = message
        statusLabel.textColor = color
        reloadData()
    }

    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        transactions.count
    }

    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let identifier = "TransactionCell"
        let cell = tableView.dequeueReusableCell(withIdentifier: identifier) ??
            UITableViewCell(style: .subtitle, reuseIdentifier: identifier)

        let transaction = transactions[indexPath.row]
        currencyFormatter.currencyCode = "USD"
        let amount = NSDecimalNumber(value: transaction.amountMinorUnits).dividing(by: 100)
        let amountText = currencyFormatter.string(from: amount) ?? "$0.00"

        switch transaction.kind {
        case .deposit:
            cell.textLabel?.text = "Deposit"
        case .withdrawal:
            cell.textLabel?.text = "Withdrawal"
        case .transfer:
            cell.textLabel?.text = "Transfer"
        }

        let dateFormatter = DateFormatter()
        dateFormatter.dateStyle = .medium
        dateFormatter.timeStyle = .short

        cell.textLabel?.font = .preferredFont(forTextStyle: .body)
        cell.detailTextLabel?.font = .preferredFont(forTextStyle: .footnote)
        cell.detailTextLabel?.numberOfLines = 0
        cell.detailTextLabel?.text = "\(amountText) • \(dateFormatter.string(from: transaction.createdAt)) • \(transaction.memo)"
        return cell
    }
}

@UIApplicationMain
final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        if #available(iOS 13.0, *) {
            return true
        }

        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = UINavigationController(rootViewController: BankingViewController(module: BankingModule.shared))
        window.makeKeyAndVisible()
        self.window = window
        return true
    }

    @available(iOS 13.0, *)
    func application(
        _ application: UIApplication,
        configurationForConnecting connectingSceneSession: UISceneSession,
        options: UIScene.ConnectionOptions
    ) -> UISceneConfiguration {
        let configuration = UISceneConfiguration(name: "Default Configuration", sessionRole: connectingSceneSession.role)
        configuration.delegateClass = SceneDelegate.self
        return configuration
    }
}

@available(iOS 13.0, *)
final class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options connectionOptions: UIScene.ConnectionOptions
    ) {
        guard let windowScene = scene as? UIWindowScene else {
            return
        }

        let window = UIWindow(windowScene: windowScene)
        window.rootViewController = UINavigationController(rootViewController: BankingViewController(module: BankingModule.shared))
        window.makeKeyAndVisible()
        self.window = window
    }
}