import UIKit
import WebKit
import UserNotifications
import AVFoundation
import StoreKit

class WebViewController: UIViewController, WKNavigationDelegate, WKScriptMessageHandler, WKUIDelegate, SKProductsRequestDelegate, SKPaymentTransactionObserver {
    
    private var webView: WKWebView!
    private var products: [SKProduct] = []
    private var productRequest: SKProductsRequest?
    private var purchaseCompletion: ((Bool, String) -> Void)?
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        let configuration = WKWebViewConfiguration()
        configuration.preferences.javaScriptEnabled = true
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = []
        
        let contentController = WKUserContentController()
        contentController.add(self, name: "nativeCamera")
        contentController.add(self, name: "nativePushNotifications")
        contentController.add(self, name: "nativeInAppPurchase")
        configuration.userContentController = contentController
        
        webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.translatesAutoresizingMaskIntoConstraints = false
        
        view.addSubview(webView)
        
        NSLayoutConstraint.activate([
            webView.topAnchor.constraint(equalTo: view.topAnchor),
            webView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            webView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: view.trailingAnchor)
        ])
        
        SKPaymentQueue.default().add(self)
        
        if let url = URL(string: "https://yourdomain.com") {
            let request = URLRequest(url: url)
            webView.load(request)
        }
    }
    
    deinit {
        SKPaymentQueue.default().remove(self)
        webView.configuration.userContentController.removeScriptMessageHandler(forName: "nativeCamera")
        webView.configuration.userContentController.removeScriptMessageHandler(forName: "nativePushNotifications")
        webView.configuration.userContentController.removeScriptMessageHandler(forName: "nativeInAppPurchase")
    }
    
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        switch message.name {
        case "nativeCamera":
            handleCameraRequest(message: message)
        case "nativePushNotifications":
            handlePushNotificationsRequest(message: message)
        case "nativeInAppPurchase":
            handleInAppPurchaseRequest(message: message)
        default:
            break
        }
    }
    
    private func handleCameraRequest(message: WKScriptMessage) {
        guard let body = message.body as? [String: Any],
              let action = body["action"] as? String else {
            sendResponse(callbackId: nil, success: false, data: ["error": "Invalid camera request"])
            return
        }
        
        let callbackId = body["callbackId"] as? String
        
        switch action {
        case "requestPermission":
            AVCaptureDevice.requestAccess(for: .video) { granted in
                DispatchQueue.main.async {
                    self.sendResponse(callbackId: callbackId, success: granted, data: ["granted": granted])
                }
            }
        case "openCamera":
            DispatchQueue.main.async {
                self.openCamera(callbackId: callbackId)
            }
        default:
            sendResponse(callbackId: callbackId, success: false, data: ["error": "Unknown camera action"])
        }
    }
    
    private func openCamera(callbackId: String?) {
        let status = AVCaptureDevice.authorizationStatus(for: .video)
        
        guard status == .authorized else {
            sendResponse(callbackId: callbackId, success: false, data: ["error": "Camera permission not granted"])
            return
        }
        
        guard UIImagePickerController.isSourceTypeAvailable(.camera) else {
            sendResponse(callbackId: callbackId, success: false, data: ["error": "Camera not available"])
            return
        }
        
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.delegate = self
        picker.allowsEditing = false
        
        if let callbackId = callbackId {
            picker.accessibilityIdentifier = callbackId
        }
        
        present(picker, animated: true)
    }
    
    private func handlePushNotificationsRequest(message: WKScriptMessage) {
        guard let body = message.body as? [String: Any],
              let action = body["action"] as? String else {
            sendResponse(callbackId: nil, success: false, data: ["error": "Invalid push notification request"])
            return
        }
        
        let callbackId = body["callbackId"] as? String
        
        switch action {
        case "requestPermission":
            UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { granted, error in
                DispatchQueue.main.async {
                    if let error = error {
                        self.sendResponse(callbackId: callbackId, success: false, data: ["error": error.localizedDescription])
                    } else {
                        UIApplication.shared.registerForRemoteNotifications()
                        self.sendResponse(callbackId: callbackId, success: granted, data: ["granted": granted])
                    }
                }
            }
        case "getPermissionStatus":
            UNUserNotificationCenter.current().getNotificationSettings { settings in
                DispatchQueue.main.async {
                    let status = settings.authorizationStatus == .authorized
                    self.sendResponse(callbackId: callbackId, success: true, data: ["granted": status])
                }
            }
        default:
            sendResponse(callbackId: callbackId, success: false, data: ["error": "Unknown push notification action"])
        }
    }
    
    private func handleInAppPurchaseRequest(message: WKScriptMessage) {
        guard let body = message.body as? [String: Any],
              let action = body["action"] as? String else {
            sendResponse(callbackId: nil, success: false, data: ["error": "Invalid in-app purchase request"])
            return
        }
        
        let callbackId = body["callbackId"] as? String
        
        switch action {
        case "getProducts":
            guard let productIds = body["productIds"] as? [String] else {
                sendResponse(callbackId: callbackId, success: false, data: ["error": "Missing productIds"])
                return
            }
            fetchProducts(productIds: Set(productIds), callbackId: callbackId)
            
        case "purchase":
            guard let productId = body["productId"] as? String else {
                sendResponse(callbackId: callbackId, success: false, data: ["error": "Missing productId"])
                return
            }
            purchaseProduct(productId: productId, callbackId: callbackId)
            
        case "restorePurchases":
            restorePurchases(callbackId: callbackId)
            
        default:
            sendResponse(callbackId: callbackId, success: false, data: ["error": "Unknown in-app purchase action"])
        }
    }
    
    private func fetchProducts(productIds: Set<String>, callbackId: String?) {
        productRequest = SKProductsRequest(productIdentifiers: productIds)
        productRequest?.delegate = self
        
        if let callbackId = callbackId {
            objc_setAssociatedObject(productRequest as Any, "callbackId", callbackId, .OBJC_ASSOCIATION_RETAIN)
        }
        
        productRequest?.start()
    }
    
    func productsRequest(_ request: SKProductsRequest, didReceive response: SKProductsResponse) {
        products = response.products
        
        let callbackId = objc_getAssociatedObject(request, "callbackId") as? String
        
        let productsData = products.map { product in
            return [
                "productId": product.productIdentifier,
                "title": product.localizedTitle,
                "description": product.localizedDescription,
                "price": product.price.stringValue,
                "priceLocale": product.priceLocale.currencyCode ?? "USD"
            ]
        }
        
        sendResponse(callbackId: callbackId, success: true, data: ["products": productsData])
    }
    
    private func purchaseProduct(productId: String, callbackId: String?) {
        guard let product = products.first(where: { $0.productIdentifier == productId }) else {
            sendResponse(callbackId: callbackId, success: false, data: ["error": "Product not found"])
            return
        }
        
        if let callbackId = callbackId {
            purchaseCompletion = { [weak self] success, transactionId in
                self?.sendResponse(callbackId: callbackId, success: success, data: ["transactionId": transactionId])
            }
        }
        
        let payment = SKPayment(product: product)
        SKPaymentQueue.default().add(payment)
    }
    
    private func restorePurchases(callbackId: String?) {
        if let callbackId = callbackId {
            purchaseCompletion = { [weak self] success, message in
                self?.sendResponse(callbackId: callbackId, success: success, data: ["message": message])
            }
        }
        
        SKPaymentQueue.default().restoreCompletedTransactions()
    }
    
    func paymentQueue(_ queue: SKPaymentQueue, updatedTransactions transactions: [SKPaymentTransaction]) {
        for transaction in transactions {
            switch transaction.transactionState {
            case .purchased:
                SKPaymentQueue.default().finishTransaction(transaction)
                purchaseCompletion?(true, transaction.transactionIdentifier ?? "")
                purchaseCompletion = nil
                
            case .failed:
                SKPaymentQueue.default().finishTransaction(transaction)
                let errorMessage = transaction.error?.localizedDescription ?? "Purchase failed"
                purchaseCompletion?(false, errorMessage)
                purchaseCompletion = nil
                
            case .restored:
                SKPaymentQueue.default().finishTransaction(transaction)
                purchaseCompletion?(true, "Restored")
                purchaseCompletion = nil
                
            case .deferred, .purchasing:
                break
                
            @unknown default:
                break
            }
        }
    }
    
    private func sendResponse(callbackId: String?, success: Bool, data: [String: Any]) {
        var response: [String: Any] = [
            "success": success,
            "data": data
        ]
        
        if let callbackId = callbackId {
            response["callbackId"] = callbackId
        }
        
        if let jsonData = try? JSONSerialization.data(withJSONObject: response, options: []),
           let jsonString = String(data: jsonData, encoding: .utf8) {
            let script = "window.nativeResponse(\(jsonString));"
            webView.evaluateJavaScript(script, completionHandler: nil)
        }
    }
    
    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        decisionHandler(.allow)
    }
    
    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in
            completionHandler()
        })
        present(alert, animated: true)
    }
    
    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel) { _ in
            completionHandler(false)
        })
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in
            completionHandler(true)
        })
        present(alert, animated: true)
    }
}

extension WebViewController: UIImagePickerControllerDelegate, UINavigationControllerDelegate {
    func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey : Any]) {
        let callbackId = picker.accessibilityIdentifier
        
        picker.dismiss(animated: true) {
            guard let image = info[.originalImage] as? UIImage,
                  let imageData = image.jpegData(compressionQuality: 0.8) else {
                self.sendResponse(callbackId: callbackId, success: false, data: ["error": "Failed to process image"])
                return
            }
            
            let base64String = imageData.base64EncodedString()
            self.sendResponse(callbackId: callbackId, success: true, data: ["image": base64String])
        }
    }
    
    func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
        let callbackId = picker.accessibilityIdentifier
        
        picker.dismiss(animated: true) {
            self.sendResponse(callbackId: callbackId, success: false, data: ["error": "User cancelled"])
        }
    }
}