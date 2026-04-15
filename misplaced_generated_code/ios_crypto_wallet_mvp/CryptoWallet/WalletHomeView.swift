import Combine
import SwiftUI

@MainActor
final class WalletViewModel: ObservableObject {
    @Published var rpcURLText = "https://cloudflare-eth.com"
    @Published var messageText = "Hello from MVP wallet"
    @Published var outputText = ""
    @Published var addressText = ""
    @Published var balanceText = ""
    @Published var hasKey = false
    @Published var toAddress = ""
    @Published var valueWeiHex = "0x0"
    @Published var gasLimitHex = "0x5208"
    @Published var gasPriceHex = ""
    @Published var chainIdText = "1"
    @Published var rawTxHex = ""

    func refreshKeyState() {
        hasKey = KeychainWalletStore.hasKey()
        if !hasKey {
            addressText = ""
            balanceText = ""
        }
    }

    func loadAddress() async {
        do {
            let priv = try KeychainWalletStore.loadPrivateKey()
            let addr = try WalletCore.ethereumAddress(fromPrivateKey: priv)
            addressText = addr
        } catch {
            outputText = error.localizedDescription
        }
    }

    func refreshBalance() async {
        guard let u = URL(string: rpcURLText) else {
            outputText = "Invalid RPC URL"
            return
        }
        do {
            let priv = try KeychainWalletStore.loadPrivateKey()
            let addr = try WalletCore.ethereumAddress(fromPrivateKey: priv)
            let rpc = EthereumRPCClient(rpcURL: u)
            let bal = try await rpc.getBalance(address: addr)
            balanceText = bal
            outputText = "Balance updated"
        } catch {
            outputText = error.localizedDescription
        }
    }

    func generateKey() async {
        do {
            let priv = try WalletCore.generatePrivateKey()
            try KeychainWalletStore.savePrivateKey(priv)
            refreshKeyState()
            await loadAddress()
            outputText = "New key generated and stored in Keychain"
        } catch {
            outputText = error.localizedDescription
        }
    }

    func deleteKey() async {
        do {
            try KeychainWalletStore.deletePrivateKeyIfExists()
            refreshKeyState()
            outputText = "Key removed"
        } catch {
            outputText = error.localizedDescription
        }
    }

    func signMessage() async {
        do {
            let priv = try KeychainWalletStore.loadPrivateKey()
            let msg = Data(messageText.utf8)
            let sig = try WalletCore.personalSign(message: msg, priv: priv)
            outputText = sig
        } catch {
            outputText = error.localizedDescription
        }
    }

    func buildSignedLegacyTx() async {
        guard let u = URL(string: rpcURLText) else {
            outputText = "Invalid RPC URL"
            return
        }
        do {
            let priv = try KeychainWalletStore.loadPrivateKey()
            let fromAddr = try WalletCore.ethereumAddress(fromPrivateKey: priv)
            let rpc = EthereumRPCClient(rpcURL: u)
            let nonceHex = try await rpc.getTransactionCount(address: fromAddr, block: "pending")
            let nonce = try WalletCore.parseHexBigInt(nonceHex)
            let gasPrice: BigInt
            if gasPriceHex.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                let gp = try await rpc.gasPrice()
                gasPrice = try WalletCore.parseHexBigInt(gp)
            } else {
                gasPrice = try WalletCore.parseHexBigInt(gasPriceHex)
            }
            let gasLimit = try WalletCore.parseHexBigInt(gasLimitHex)
            let value = try WalletCore.parseHexBigInt(valueWeiHex)
            let toBytes = try WalletCore.addressBytes20(toAddress)
            let chainId: BigInt
            if chainIdText.lowercased().hasPrefix("0x") {
                chainId = try WalletCore.parseHexBigInt(chainIdText)
            } else {
                guard let cid = UInt64(chainIdText.trimmingCharacters(in: .whitespacesAndNewlines)) else {
                    outputText = "Invalid chain id"
                    return
                }
                chainId = BigInt(cid)
            }
            let raw = try WalletCore.signLegacyEIP155Raw(
                nonce: nonce,
                gasPrice: gasPrice,
                gasLimit: gasLimit,
                toAddress20: toBytes,
                value: value,
                data: Data(),
                chainId: chainId,
                priv: priv
            )
            rawTxHex = "0x" + Hex.string(from: raw)
            outputText = rawTxHex
        } catch {
            outputText = error.localizedDescription
        }
    }

    func sendRawTx() async {
        guard let u = URL(string: rpcURLText) else {
            outputText = "Invalid RPC URL"
            return
        }
        let hex = rawTxHex.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !hex.isEmpty else {
            outputText = "Build a transaction first"
            return
        }
        do {
            let rpc = EthereumRPCClient(rpcURL: u)
            let txid = try await rpc.sendRawTransaction(hex)
            outputText = "Submitted: \(txid)"
        } catch {
            outputText = error.localizedDescription
        }
    }
}

struct WalletHomeView: View {
    @StateObject private var vm = WalletViewModel()

    var body: some View {
        NavigationView {
            Form {
                Section("RPC") {
                    TextField("RPC URL", text: $vm.rpcURLText)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                }
                Section("Wallet") {
                    Text(vm.addressText.isEmpty ? "Address: —" : "Address: \(vm.addressText)")
                        .font(.system(.body, design: .monospaced))
                    Text(vm.balanceText.isEmpty ? "Balance: —" : "Balance: \(vm.balanceText)")
                    HStack {
                        Button("Generate key") { Task { await vm.generateKey() } }
                            .disabled(vm.hasKey)
                        Button("Delete key", role: .destructive) { Task { await vm.deleteKey() } }
                            .disabled(!vm.hasKey)
                    }
                    Button("Refresh balance") { Task { await vm.refreshBalance() } }
                        .disabled(!vm.hasKey)
                }
                Section("Sign message (personal_sign)") {
                    TextField("Message", text: $vm.messageText)
                    Button("Sign") { Task { await vm.signMessage() } }
                        .disabled(!vm.hasKey)
                }
                Section("Legacy EIP-155 transaction") {
                    TextField("To (0x… 20 bytes)", text: $vm.toAddress)
                        .textInputAutocapitalization(.never)
                    TextField("Value wei (hex)", text: $vm.valueWeiHex)
                    TextField("Gas limit (hex)", text: $vm.gasLimitHex)
                    TextField("Gas price (hex, empty=RPC)", text: $vm.gasPriceHex)
                    TextField("Chain ID (decimal or 0x hex)", text: $vm.chainIdText)
                    Button("Build signed raw tx") { Task { await vm.buildSignedLegacyTx() } }
                        .disabled(!vm.hasKey)
                    Button("Broadcast raw tx") { Task { await vm.sendRawTx() } }
                        .disabled(!vm.hasKey || vm.rawTxHex.isEmpty)
                }
                Section("Output") {
                    Text(vm.outputText)
                        .font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled)
                }
            }
            .navigationTitle("Crypto Wallet MVP")
            .navigationBarTitleDisplayMode(.inline)
            .onAppear {
                vm.refreshKeyState()
                Task {
                    if vm.hasKey { await vm.loadAddress() }
                }
            }
            .onChange(of: vm.hasKey) { new in
                if new { Task { await vm.loadAddress() } }
            }
        }
    }
}

struct WalletHomeView_Previews: PreviewProvider {
    static var previews: some View {
        WalletHomeView()
    }
}
