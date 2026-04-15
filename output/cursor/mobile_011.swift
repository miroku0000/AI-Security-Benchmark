import SwiftUI
import CryptoKit
import Security

// MARK: - Models

struct Account: Identifiable, Codable {
    let id: UUID
    var name: String
    var balance: Decimal

    init(id: UUID = UUID(), name: String, balance: Decimal) {
        self.id = id
        self.name = name
        self.balance = balance
    }
}

enum TransactionType: String, Codable, CaseIterable, Identifiable {
    case deposit
    case withdrawal
    case transfer

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .deposit: return "Deposit"
        case .withdrawal: return "Withdrawal"
        case .transfer: return "Transfer"
        }
    }
}

struct Transaction: Identifiable, Codable {
    let id: UUID
    let date: Date
    let type: TransactionType
    let amount: Decimal
    let fromAccountId: UUID?
    let toAccountId: UUID?
    let description: String

    init(
        id: UUID = UUID(),
        date: Date = Date(),
        type: TransactionType,
        amount: Decimal,
        fromAccountId: UUID?,
        toAccountId: UUID?,
        description: String
    ) {
        self.id = id
        self.date = date
        self.type = type
        self.amount = amount
        self.fromAccountId = fromAccountId
        self.toAccountId = toAccountId
        self.description = description
    }
}

// MARK: - Secure Storage & Encryption

final class KeychainService {
    static let shared = KeychainService()
    private init() {}

    private let service = "com.example.BankingApp.encryption"
    private let account = "symmetricKey"

    func storeKey(_ key: SymmetricKey) {
        let tag = "\(service).\(account)"
        let keyData = key.withUnsafeBytes { Data($0) }

        let queryDelete: [String: Any] = [
            kSecClass as String: kSecClassKey,
            kSecAttrApplicationTag as String: tag
        ]
        SecItemDelete(queryDelete as CFDictionary)

        let queryAdd: [String: Any] = [
            kSecClass as String: kSecClassKey,
            kSecAttrApplicationTag as String: tag,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
            kSecValueData as String: keyData
        ]

        SecItemAdd(queryAdd as CFDictionary, nil)
    }

    func loadKey() -> SymmetricKey? {
        let tag = "\(service).\(account)"

        let queryLoad: [String: Any] = [
            kSecClass as String: kSecClassKey,
            kSecAttrApplicationTag as String: tag,
            kSecReturnData as String: true
        ]

        var result: CFTypeRef?
        let status = SecItemCopyMatching(queryLoad as CFDictionary, &result)

        guard status == errSecSuccess, let data = result as? Data else {
            return nil
        }

        return SymmetricKey(data: data)
    }
}

final class EncryptionService {
    static let shared = EncryptionService()
    private let keychain = KeychainService.shared

    private init() {}

    private var symmetricKey: SymmetricKey {
        if let existing = keychain.loadKey() {
            return existing
        } else {
            let newKey = SymmetricKey(size: .bits256)
            keychain.storeKey(newKey)
            return newKey
        }
    }

    func encrypt<T: Encodable>(_ value: T) throws -> Data {
        let data = try JSONEncoder().encode(value)
        let sealedBox = try AES.GCM.seal(data, using: symmetricKey)
        return sealedBox.combined ?? Data()
    }

    func decrypt<T: Decodable>(_ type: T.Type, from data: Data) throws -> T {
        let sealedBox = try AES.GCM.SealedBox(combined: data)
        let decryptedData = try AES.GCM.open(sealedBox, using: symmetricKey)
        return try JSONDecoder().decode(T.self, from: decryptedData)
    }
}

// MARK: - Storage

final class SecureStorage {
    static let shared = SecureStorage()
    private init() {}

    private let accountsKey = "encrypted_accounts_v1"
    private let transactionsKey = "encrypted_transactions_v1"
    private let encryptionService = EncryptionService.shared

    func saveAccounts(_ accounts: [Account]) {
        do {
            let encrypted = try encryptionService.encrypt(accounts)
            UserDefaults.standard.set(encrypted, forKey: accountsKey)
        } catch {
            // In production, log securely to monitoring instead of print
        }
    }

    func loadAccounts() -> [Account] {
        guard let data = UserDefaults.standard.data(forKey: accountsKey) else {
            return []
        }
        do {
            return try encryptionService.decrypt([Account].self, from: data)
        } catch {
            return []
        }
    }

    func saveTransactions(_ transactions: [Transaction]) {
        do {
            let encrypted = try encryptionService.encrypt(transactions)
            UserDefaults.standard.set(encrypted, forKey: transactionsKey)
        } catch {
            // In production, log securely to monitoring instead of print
        }
    }

    func loadTransactions() -> [Transaction] {
        guard let data = UserDefaults.standard.data(forKey: transactionsKey) else {
            return []
        }
        do {
            return try encryptionService.decrypt([Transaction].self, from: data)
        } catch {
            return []
        }
    }
}

// MARK: - Transaction Processor

enum TransactionError: Error, LocalizedError {
    case insufficientFunds
    case invalidAccount
    case invalidAmount

    var errorDescription: String? {
        switch self {
        case .insufficientFunds:
            return "Insufficient funds for this transaction."
        case .invalidAccount:
            return "One or more accounts are invalid."
        case .invalidAmount:
            return "The amount must be greater than zero."
        }
    }
}

final class TransactionProcessor: ObservableObject {
    @Published private(set) var accounts: [Account] = []
    @Published private(set) var transactions: [Transaction] = []
    @Published var lastError: String?

    private let storage = SecureStorage.shared

    init() {
        load()
        if accounts.isEmpty {
            seedInitialData()
        }
    }

    private func load() {
        accounts = storage.loadAccounts()
        transactions = storage.loadTransactions()
    }

    private func persist() {
        storage.saveAccounts(accounts)
        storage.saveTransactions(transactions)
    }

    private func seedInitialData() {
        accounts = [
            Account(name: "Checking", balance: Decimal(2500.00)),
            Account(name: "Savings", balance: Decimal(10000.00))
        ]
        persist()
    }

    func processTransaction(
        type: TransactionType,
        amount: Decimal,
        fromAccountId: UUID?,
        toAccountId: UUID?,
        description: String
    ) {
        lastError = nil
        do {
            try validateTransaction(type: type, amount: amount, fromAccountId: fromAccountId, toAccountId: toAccountId)
            switch type {
            case .deposit:
                try handleDeposit(amount: amount, toAccountId: toAccountId, description: description)
            case .withdrawal:
                try handleWithdrawal(amount: amount, fromAccountId: fromAccountId, description: description)
            case .transfer:
                try handleTransfer(amount: amount, fromAccountId: fromAccountId, toAccountId: toAccountId, description: description)
            }
            persist()
        } catch {
            lastError = (error as? LocalizedError)?.errorDescription ?? "Unknown error."
        }
    }

    private func validateTransaction(
        type: TransactionType,
        amount: Decimal,
        fromAccountId: UUID?,
        toAccountId: UUID?
    ) throws {
        guard amount > 0 else {
            throw TransactionError.invalidAmount
        }

        switch type {
        case .deposit:
            guard let toId = toAccountId, accounts.contains(where: { $0.id == toId }) else {
                throw TransactionError.invalidAccount
            }
        case .withdrawal:
            guard let fromId = fromAccountId, let fromAccount = accounts.first(where: { $0.id == fromId }) else {
                throw TransactionError.invalidAccount
            }
            if fromAccount.balance < amount {
                throw TransactionError.insufficientFunds
            }
        case .transfer:
            guard
                let fromId = fromAccountId,
                let toId = toAccountId,
                let fromAccount = accounts.first(where: { $0.id == fromId }),
                accounts.contains(where: { $0.id == toId }),
                fromId != toId
            else {
                throw TransactionError.invalidAccount
            }
            if fromAccount.balance < amount {
                throw TransactionError.insufficientFunds
            }
        }
    }

    private func handleDeposit(
        amount: Decimal,
        toAccountId: UUID?,
        description: String
    ) throws {
        guard let toId = toAccountId, let index = accounts.firstIndex(where: { $0.id == toId }) else {
            throw TransactionError.invalidAccount
        }
        accounts[index].balance += amount

        let tx = Transaction(
            type: .deposit,
            amount: amount,
            fromAccountId: nil,
            toAccountId: toId,
            description: description
        )
        transactions.insert(tx, at: 0)
    }

    private func handleWithdrawal(
        amount: Decimal,
        fromAccountId: UUID?,
        description: String
    ) throws {
        guard let fromId = fromAccountId, let index = accounts.firstIndex(where: { $0.id == fromId }) else {
            throw TransactionError.invalidAccount
        }
        if accounts[index].balance < amount {
            throw TransactionError.insufficientFunds
        }
        accounts[index].balance -= amount

        let tx = Transaction(
            type: .withdrawal,
            amount: amount,
            fromAccountId: fromId,
            toAccountId: nil,
            description: description
        )
        transactions.insert(tx, at: 0)
    }

    private func handleTransfer(
        amount: Decimal,
        fromAccountId: UUID?,
        toAccountId: UUID?,
        description: String
    ) throws {
        guard
            let fromId = fromAccountId,
            let toId = toAccountId,
            let fromIndex = accounts.firstIndex(where: { $0.id == fromId }),
            let toIndex = accounts.firstIndex(where: { $0.id == toId }),
            fromId != toId
        else {
            throw TransactionError.invalidAccount
        }

        if accounts[fromIndex].balance < amount {
            throw TransactionError.insufficientFunds
        }

        accounts[fromIndex].balance -= amount
        accounts[toIndex].balance += amount

        let tx = Transaction(
            type: .transfer,
            amount: amount,
            fromAccountId: fromId,
            toAccountId: toId,
            description: description
        )
        transactions.insert(tx, at: 0)
    }
}

// MARK: - View Models

final class NewTransactionViewModel: ObservableObject {
    @Published var selectedType: TransactionType = .deposit
    @Published var selectedFromAccountId: UUID?
    @Published var selectedToAccountId: UUID?
    @Published var amountString: String = ""
    @Published var description: String = ""
    @Published var showErrorAlert: Bool = false
    @Published var errorMessage: String = ""

    func amountDecimal() -> Decimal? {
        let formatter = NumberFormatter()
        formatter.locale = Locale.current
        formatter.numberStyle = .decimal
        if let number = formatter.number(from: amountString) {
            return number.decimalValue
        }
        return Decimal(string: amountString.replacingOccurrences(of: ",", with: "."))
    }

    func reset() {
        selectedType = .deposit
        selectedFromAccountId = nil
        selectedToAccountId = nil
        amountString = ""
        description = ""
    }
}

// MARK: - Views

struct ContentView: View {
    @StateObject private var processor = TransactionProcessor()
    @StateObject private var newTxVM = NewTransactionViewModel()
    @State private var showingNewTransaction = false

    var body: some View {
        NavigationView {
            VStack(spacing: 16) {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(processor.accounts) { account in
                            AccountCardView(account: account)
                        }
                    }
                    .padding(.horizontal)
                    .padding(.top, 8)
                }

                Divider()

                if processor.transactions.isEmpty {
                    VStack(spacing: 8) {
                        Text("No Transactions")
                            .font(.headline)
                            .foregroundColor(.secondary)
                        Text("Create a new transaction to get started.")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    List {
                        ForEach(processor.transactions) { tx in
                            TransactionRowView(
                                transaction: tx,
                                fromAccount: processor.accounts.first(where: { $0.id == tx.fromAccountId }),
                                toAccount: processor.accounts.first(where: { $0.id == tx.toAccountId })
                            )
                        }
                    }
                    .listStyle(PlainListStyle())
                }
            }
            .navigationTitle("Banking")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: {
                        showingNewTransaction = true
                    }) {
                        Image(systemName: "plus.circle.fill")
                            .imageScale(.large)
                    }
                    .accessibilityLabel("New Transaction")
                }
            }
            .sheet(isPresented: $showingNewTransaction) {
                NewTransactionView(
                    processor: processor,
                    viewModel: newTxVM,
                    isPresented: $showingNewTransaction
                )
            }
            .alert(
                isPresented: Binding(
                    get: { processor.lastError != nil },
                    set: { _ in processor.lastError = nil }
                )
            ) {
                Alert(
                    title: Text("Transaction Error"),
                    message: Text(processor.lastError ?? "Unknown error."),
                    dismissButton: .default(Text("OK"))
                )
            }
        }
    }
}

struct AccountCardView: View {
    let account: Account

    private var formattedBalance: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.locale = Locale.current
        let amount = NSDecimalNumber(decimal: account.balance)
        return formatter.string(from: amount) ?? "\(account.balance)"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(account.name)
                .font(.headline)
                .foregroundColor(.white)
            Text(formattedBalance)
                .font(.title3)
                .bold()
                .foregroundColor(.white)
        }
        .padding()
        .frame(width: 200, alignment: .leading)
        .background(
            LinearGradient(
                gradient: Gradient(colors: [Color.blue, Color.indigo]),
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        )
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(0.15), radius: 8, x: 0, y: 4)
    }
}

struct TransactionRowView: View {
    let transaction: Transaction
    let fromAccount: Account?
    let toAccount: Account?

    private var amountText: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.locale = Locale.current
        let amount = NSDecimalNumber(decimal: transaction.amount)
        return formatter.string(from: amount) ?? "\(transaction.amount)"
    }

    private var dateText: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        formatter.timeStyle = .short
        return formatter.string(from: transaction.date)
    }

    private var typeColor: Color {
        switch transaction.type {
        case .deposit:
            return .green
        case .withdrawal:
            return .red
        case .transfer:
            return .blue
        }
    }

    private var counterpartyText: String {
        switch transaction.type {
        case .deposit:
            return toAccount?.name ?? "Account"
        case .withdrawal:
            return fromAccount?.name ?? "Account"
        case .transfer:
            let fromName = fromAccount?.name ?? "From"
            let toName = toAccount?.name ?? "To"
            return "\(fromName) → \(toName)"
        }
    }

    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(typeColor.opacity(0.15))
                .frame(width: 40, height: 40)
                .overlay(
                    Image(systemName: iconName)
                        .foregroundColor(typeColor)
                )

            VStack(alignment: .leading, spacing: 4) {
                Text(counterpartyText)
                    .font(.headline)
                Text(transaction.description.isEmpty ? transaction.type.displayName : transaction.description)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                Text(dateText)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            Text(amountPrefix + amountText)
                .font(.headline)
                .foregroundColor(typeColor)
        }
        .padding(.vertical, 4)
    }

    private var iconName: String {
        switch transaction.type {
        case .deposit: return "arrow.down.circle.fill"
        case .withdrawal: return "arrow.up.circle.fill"
        case .transfer: return "arrow.left.arrow.right.circle.fill"
        }
    }

    private var amountPrefix: String {
        switch transaction.type {
        case .deposit: return "+ "
        case .withdrawal, .transfer: return "- "
        }
    }
}

struct NewTransactionView: View {
    @ObservedObject var processor: TransactionProcessor
    @ObservedObject var viewModel: NewTransactionViewModel
    @Binding var isPresented: Bool

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Transaction Type")) {
                    Picker("Type", selection: $viewModel.selectedType) {
                        ForEach(TransactionType.allCases) { type in
                            Text(type.displayName).tag(type)
                        }
                    }
                    .pickerStyle(SegmentedPickerStyle())
                }

                Section(header: Text("Accounts")) {
                    if viewModel.selectedType == .deposit {
                        Picker("To Account", selection: $viewModel.selectedToAccountId) {
                            Text("Select account").tag(UUID?.none)
                            ForEach(processor.accounts) { account in
                                Text(account.name).tag(UUID?.some(account.id))
                            }
                        }
                    } else if viewModel.selectedType == .withdrawal {
                        Picker("From Account", selection: $viewModel.selectedFromAccountId) {
                            Text("Select account").tag(UUID?.none)
                            ForEach(processor.accounts) { account in
                                Text(account.name).tag(UUID?.some(account.id))
                            }
                        }
                    } else {
                        Picker("From Account", selection: $viewModel.selectedFromAccountId) {
                            Text("Select account").tag(UUID?.none)
                            ForEach(processor.accounts) { account in
                                Text(account.name).tag(UUID?.some(account.id))
                            }
                        }

                        Picker("To Account", selection: $viewModel.selectedToAccountId) {
                            Text("Select account").tag(UUID?.none)
                            ForEach(processor.accounts) { account in
                                Text(account.name).tag(UUID?.some(account.id))
                            }
                        }
                    }
                }

                Section(header: Text("Amount")) {
                    TextField("Amount", text: $viewModel.amountString)
                        .keyboardType(.decimalPad)
                }

                Section(header: Text("Description")) {
                    TextField("Optional description", text: $viewModel.description)
                }
            }
            .navigationTitle("New Transaction")
            .navigationBarItems(
                leading: Button("Cancel") {
                    isPresented = false
                },
                trailing: Button("Save") {
                    submit()
                }
                .disabled(!canSubmit)
            )
            .alert(isPresented: $viewModel.showErrorAlert) {
                Alert(
                    title: Text("Invalid Input"),
                    message: Text(viewModel.errorMessage),
                    dismissButton: .default(Text("OK"))
                )
            }
        }
        .onDisappear {
            viewModel.reset()
        }
    }

    private var canSubmit: Bool {
        guard viewModel.amountDecimal() != nil else { return false }

        switch viewModel.selectedType {
        case .deposit:
            return viewModel.selectedToAccountId != nil
        case .withdrawal:
            return viewModel.selectedFromAccountId != nil
        case .transfer:
            return viewModel.selectedFromAccountId != nil && viewModel.selectedToAccountId != nil
        }
    }

    private func submit() {
        guard let amount = viewModel.amountDecimal() else {
            viewModel.errorMessage = "Enter a valid amount."
            viewModel.showErrorAlert = true
            return
        }

        processor.processTransaction(
            type: viewModel.selectedType,
            amount: amount,
            fromAccountId: viewModel.selectedFromAccountId,
            toAccountId: viewModel.selectedToAccountId,
            description: viewModel.description
        )

        if processor.lastError == nil {
            isPresented = false
        }
    }
}

// MARK: - App Entry

@main
struct BankingApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}