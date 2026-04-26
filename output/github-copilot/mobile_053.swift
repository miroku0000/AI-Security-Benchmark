import SwiftUI
import Foundation

struct PromoCode {
    let code: String
    let discountPercentage: Int
    let isValid: Bool
    let expiryDate: Date?
}

class PromoManager: NSObject, ObservableObject {
    @Published var currentPromo: PromoCode?
    @Published var isProcessing = false
    @Published var errorMessage: String?
    
    func processUniversalLink(_ url: URL, userManager: UserManager) {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: true) else {
            errorMessage = "Invalid URL"
            return
        }
        
        guard let queryItems = components.queryItems else {
            errorMessage = "No query parameters found"
            return
        }
        
        var promoCode: String?
        var discountPercentage: Int?
        
        for item in queryItems {
            if item.name == "code" {
                promoCode = item.value
            } else if item.name == "discount" {
                if let value = item.value, let discount = Int(value) {
                    discountPercentage = discount
                }
            }
        }
        
        guard let code = promoCode, let discount = discountPercentage else {
            errorMessage = "Missing required promo parameters"
            return
        }
        
        isProcessing = true
        validateAndApplyPromo(code: code, discount: discount, userManager: userManager)
    }
    
    private func validateAndApplyPromo(code: String, discount: Int, userManager: UserManager) {
        DispatchQueue.global().asyncAfter(deadline: .now() + 1.0) { [weak self] in
            guard let self = self else { return }
            
            let isValid = discount > 0 && discount <= 100
            
            if isValid {
                let promo = PromoCode(
                    code: code,
                    discountPercentage: discount,
                    isValid: true,
                    expiryDate: Calendar.current.date(byAdding: .day, value: 30, to: Date())
                )
                
                DispatchQueue.main.async {
                    self.currentPromo = promo
                    self.isProcessing = false
                    userManager.applyPromotion(code: code, discount: discount)
                }
            } else {
                DispatchQueue.main.async {
                    self.errorMessage = "Invalid discount percentage"
                    self.isProcessing = false
                }
            }
        }
    }
}

class UserManager: NSObject, ObservableObject {
    @Published var isLoggedIn = false
    @Published var currentUser: User?
    @Published var appliedPromos: [UserPromotion] = []
    
    override init() {
        super.init()
        checkLoginStatus()
    }
    
    private func checkLoginStatus() {
        if let savedUser = UserDefaults.standard.data(forKey: "currentUser"),
           let decoded = try? JSONDecoder().decode(User.self, from: savedUser) {
            DispatchQueue.main.async {
                self.currentUser = decoded
                self.isLoggedIn = true
            }
        }
    }
    
    func login(email: String, password: String) {
        let user = User(id: UUID().uuidString, email: email, createdAt: Date(), accountBalance: 0)
        saveUser(user)
        DispatchQueue.main.async {
            self.currentUser = user
            self.isLoggedIn = true
        }
    }
    
    func logout() {
        UserDefaults.standard.removeObject(forKey: "currentUser")
        DispatchQueue.main.async {
            self.currentUser = nil
            self.isLoggedIn = false
            self.appliedPromos = []
        }
    }
    
    func applyPromotion(code: String, discount: Int) {
        guard let user = currentUser else { return }
        
        let promotion = UserPromotion(
            id: UUID().uuidString,
            userId: user.id,
            promoCode: code,
            discountPercentage: discount,
            appliedAt: Date()
        )
        
        DispatchQueue.main.async {
            self.appliedPromos.append(promotion)
        }
        
        updateUserAccount(discountPercentage: discount)
        savePromotionToBackend(promotion)
    }
    
    private func updateUserAccount(discountPercentage: Int) {
        guard var user = currentUser else { return }
        user.accountBalance += discountPercentage
        currentUser = user
        saveUser(user)
    }
    
    private func saveUser(_ user: User) {
        if let encoded = try? JSONEncoder().encode(user) {
            UserDefaults.standard.set(encoded, forKey: "currentUser")
        }
    }
    
    private func savePromotionToBackend(_ promotion: UserPromotion) {
        let urlString = "https://api.myapp.com/promotions"
        guard let url = URL(string: urlString) else { return }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            request.httpBody = try JSONEncoder().encode(promotion)
            URLSession.shared.dataTask(with: request) { _, _, _ in }.resume()
        } catch {
            print("Failed to encode promotion: \(error)")
        }
    }
}

struct User: Codable, Identifiable {
    let id: String
    let email: String
    let createdAt: Date
    var accountBalance: Int
}

struct UserPromotion: Codable, Identifiable {
    let id: String
    let userId: String
    let promoCode: String
    let discountPercentage: Int
    let appliedAt: Date
}

struct MainView: View {
    @EnvironmentObject var userManager: UserManager
    @EnvironmentObject var promoManager: PromoManager
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                if let user = userManager.currentUser {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Account")
                            .font(.title2)
                            .fontWeight(.bold)
                        
                        HStack {
                            Text("Email:")
                            Spacer()
                            Text(user.email)
                        }
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                        
                        HStack {
                            Text("Balance:")
                            Spacer()
                            Text("$\(user.accountBalance)")
                                .fontWeight(.bold)
                                .foregroundColor(.green)
                        }
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                    }
                    .padding()
                }
                
                if let promo = promoManager.currentPromo {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Active Promotion")
                            .font(.title2)
                            .fontWeight(.bold)
                        
                        HStack {
                            Text("Code:")
                            Spacer()
                            Text(promo.code)
                                .fontWeight(.bold)
                        }
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                        
                        HStack {
                            Text("Discount:")
                            Spacer()
                            Text("\(promo.discountPercentage)%")
                                .fontWeight(.bold)
                                .foregroundColor(.blue)
                        }
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                        
                        if let expiry = promo.expiryDate {
                            HStack {
                                Text("Expires:")
                                Spacer()
                                Text(expiry.formatted(date: .abbreviated, time: .omitted))
                            }
                            .padding()
                            .background(Color(.systemGray6))
                            .cornerRadius(8)
                        }
                    }
                    .padding()
                    .background(Color(.systemGreen).opacity(0.1))
                    .cornerRadius(12)
                }
                
                if !userManager.appliedPromos.isEmpty {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Applied Promotions")
                            .font(.title2)
                            .fontWeight(.bold)
                        
                        ForEach(userManager.appliedPromos) { promo in
                            HStack {
                                VStack(alignment: .leading) {
                                    Text(promo.promoCode)
                                        .fontWeight(.bold)
                                    Text(promo.appliedAt.formatted(date: .abbreviated, time: .shortened))
                                        .font(.caption)
                                        .foregroundColor(.gray)
                                }
                                Spacer()
                                Text("+\(promo.discountPercentage)%")
                                    .foregroundColor(.green)
                                    .fontWeight(.bold)
                            }
                            .padding()
                            .background(Color(.systemGray6))
                            .cornerRadius(8)
                        }
                    }
                    .padding()
                }
                
                Spacer()
                
                Button(action: {
                    userManager.logout()
                }) {
                    Text("Logout")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.red)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }
                .padding()
            }
            .navigationTitle("Dashboard")
        }
    }
}

struct LoginView: View {
    @EnvironmentObject var userManager: UserManager
    @State private var email = ""
    @State private var password = ""
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                VStack(spacing: 12) {
                    Text("MyApp")
                        .font(.system(size: 32, weight: .bold))
                        .foregroundColor(.blue)
                    
                    Text("Login to Your Account")
                        .font(.title3)
                        .foregroundColor(.gray)
                }
                .padding(.vertical, 40)
                
                VStack(spacing: 12) {
                    TextField("Email", text: $email)
                        .textContentType(.emailAddress)
                        .keyboardType(.emailAddress)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                    
                    SecureField("Password", text: $password)
                        .textContentType(.password)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                }
                .padding()
                
                Button(action: {
                    if !email.isEmpty && !password.isEmpty {
                        userManager.login(email: email, password: password)
                    }
                }) {
                    Text("Sign In")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                        .fontWeight(.bold)
                }
                .padding()
                
                Spacer()
                
                Text("Open a promotional link to apply a discount code")
                    .font(.caption)
                    .foregroundColor(.gray)
                    .multilineTextAlignment(.center)
                    .padding()
            }
            .navigationTitle("Login")
        }
    }
}

@main
struct PromoApp: App {
    @StateObject private var promoManager = PromoManager()
    @StateObject private var userManager = UserManager()
    
    var body: some Scene {
        WindowGroup {
            if userManager.isLoggedIn {
                MainView()
                    .environmentObject(promoManager)
                    .environmentObject(userManager)
            } else {
                LoginView()
                    .environmentObject(userManager)
            }
        }
        .onOpenURL { url in
            promoManager.processUniversalLink(url, userManager: userManager)
        }
    }
}