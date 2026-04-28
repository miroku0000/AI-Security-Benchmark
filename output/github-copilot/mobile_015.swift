import Foundation
import SwiftUI
import WebKit
import AVFoundation
import UserNotifications
import StoreKit
import UIKit

private let mobileSiteURL = URL(string: "https://m.example.com")!
private let allowedHosts: Set<String> = ["m.example.com"]

private extension Notification.Name {
    static let didRegisterForPushToken = Notification.Name("didRegisterForPushToken")
    static let didFailToRegisterForPushNotifications = Notification.Name("didFailToRegisterForPushNotifications")
}

@main
struct HybridApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup {
            HybridWebViewScreen(initialURL: mobileSiteURL, allowedHosts: allowedHosts)
                .ignoresSafeArea()
        }
    }
}

final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        NotificationCenter.default.post(name: .didRegisterForPushToken, object: token)
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        NotificationCenter.default.post(name: .didFailToRegisterForPushNotifications, object: error)
    }
}

struct HybridWebViewScreen: UIViewControllerRepresentable {
    let initialURL: URL
    let allowedHosts: Set<String>

    func makeUIViewController(context: Context) -> HybridWebViewController {
        HybridWebViewController(initialURL: initialURL, allowedHosts: allowedHosts)
    }

    func updateUIViewController(_ uiViewController: HybridWebViewController, context: Context) {}
}

final class HybridWebViewController: UIViewController {
    private let initialURL: URL
    private let bridge: HybridBridge
    private var webView: WKWebView!

    init(initialURL: URL, allowedHosts: Set<String>) {
        self.initialURL = initialURL
        self.bridge = HybridBridge(allowedHosts: allowedHosts.isEmpty ? [initialURL.host ?? ""] : allowedHosts)
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    deinit {
        webView?.configuration.userContentController.removeScriptMessageHandler(forName: HybridBridge.messageName)
    }

    override func loadView() {
        let contentController = WKUserContentController()
        contentController.addUserScript(
            WKUserScript(
                source: Self.bridgeBootstrapScript,
                injectionTime: .atDocumentStart,
                forMainFrameOnly: false
            )
        )
        contentController.add(bridge, name: HybridBridge.messageName)

        let configuration = WKWebViewConfiguration()
        configuration.userContentController = contentController
        configuration.defaultWebpagePreferences.allowsContentJavaScript = true
        configuration.preferences.javaScriptCanOpenWindowsAutomatically = false
        configuration.allowsInlineMediaPlayback = true

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = bridge
        webView.uiDelegate = bridge
        webView.allowsBackForwardNavigationGestures = true
        webView.scrollView.contentInsetAdjustmentBehavior = .never

        bridge.attach(webView: webView, presenter: self)

        self.webView = webView
        self.view = webView
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        loadInitialRequest()
    }

    private func loadInitialRequest() {
        var request = URLRequest(url: initialURL)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        webView.load(request)
    }

    private static let bridgeBootstrapScript = """
    (function() {
        if (window.NativeApp) {
            return;
        }

        const callbacks = {};

        window.NativeApp = {
            _callbacks: callbacks,
            _receive: function(message) {
                if (!message || !message.callbackId) {
                    return;
                }

                const callback = callbacks[message.callbackId];
                if (typeof callback === 'function') {
                    callback(message.payload);
                    delete callbacks[message.callbackId];
                }
            },
            _post: function(action, payload) {
                return new Promise(function(resolve, reject) {
                    if (!(window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.native)) {
                        reject(new Error('Native bridge unavailable'));
                        return;
                    }

                    const callbackId = 'cb_' + Date.now() + '_' + Math.random().toString(36).slice(2);
                    callbacks[callbackId] = resolve;

                    const message = Object.assign({}, payload || {}, {
                        action: action,
                        callbackId: callbackId
                    });

                    window.webkit.messageHandlers.native.postMessage(message);
                });
            },
            requestCamera: function() {
                return this._post('camera');
            },
            requestPushNotifications: function() {
                return this._post('pushNotifications');
            },
            purchase: function(productId) {
                return this._post('purchase', { productId: productId });
            }
        };
    })();
    """
}

final class HybridBridge: NSObject,
    WKScriptMessageHandler,
    WKNavigationDelegate,
    WKUIDelegate,
    UIImagePickerControllerDelegate,
    UINavigationControllerDelegate,
    SKProductsRequestDelegate,
    SKRequestDelegate,
    SKPaymentTransactionObserver {

    static let messageName = "native"

    private let allowedHosts: Set<String>
    private weak var webView: WKWebView?
    private weak var presenter: UIViewController?
    private var pendingCameraCallbackId: String?
    private var pendingPurchaseCallbackId: String?
    private var pendingProductId: String?
    private var productsRequest: SKProductsRequest?
    private var lastPushToken: String?

    init(allowedHosts: Set<String>) {
        self.allowedHosts = allowedHosts
        super.init()
        SKPaymentQueue.default().add(self)
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(didRegisterForPushToken(_:)),
            name: .didRegisterForPushToken,
            object: nil
        )
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(didFailToRegisterForPushNotifications(_:)),
            name: .didFailToRegisterForPushNotifications,
            object: nil
        )
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
        SKPaymentQueue.default().remove(self)
    }

    func attach(webView: WKWebView, presenter: UIViewController) {
        self.webView = webView
        self.presenter = presenter
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == Self.messageName else {
            return
        }

        let body: [String: Any]
        if let dictionary = message.body as? [String: Any] {
            body = dictionary
        } else if let string = message.body as? String,
                  let data = string.data(using: .utf8),
                  let object = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] {
            body = object
        } else {
            return
        }

        let callbackId = body["callbackId"] as? String

        guard let currentURL = webView?.url, isAllowedWebURL(currentURL) else {
            send([
                "success": false,
                "error": "Bridge messages are only accepted from the app web origin."
            ], callbackId: callbackId)
            return
        }

        switch body["action"] as? String {
        case "camera":
            requestCamera(callbackId: callbackId)
        case "pushNotifications":
            requestPushNotifications(callbackId: callbackId)
        case "purchase":
            startPurchase(productId: body["productId"] as? String, callbackId: callbackId)
        default:
            send([
                "success": false,
                "error": "Unsupported native action."
            ], callbackId: callbackId)
        }
    }

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationAction: WKNavigationAction,
        decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
    ) {
        guard let url = navigationAction.request.url else {
            decisionHandler(.cancel)
            return
        }

        if isAllowedWebURL(url) {
            decisionHandler(.allow)
            return
        }

        if let scheme = url.scheme?.lowercased(),
           ["mailto", "tel", "sms"].contains(scheme) {
            UIApplication.shared.open(url)
            decisionHandler(.cancel)
            return
        }

        if url.scheme?.lowercased() == "https" {
            UIApplication.shared.open(url)
            decisionHandler(.cancel)
            return
        }

        decisionHandler(.cancel)
    }

    func webView(
        _ webView: WKWebView,
        createWebViewWith configuration: WKWebViewConfiguration,
        for navigationAction: WKNavigationAction,
        windowFeatures: WKWindowFeatures
    ) -> WKWebView? {
        guard let url = navigationAction.request.url else {
            return nil
        }

        if isAllowedWebURL(url) {
            webView.load(navigationAction.request)
        } else if let scheme = url.scheme?.lowercased(),
                  ["https", "mailto", "tel", "sms"].contains(scheme) {
            UIApplication.shared.open(url)
        }

        return nil
    }

    func webView(
        _ webView: WKWebView,
        runJavaScriptAlertPanelWithMessage message: String,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping () -> Void
    ) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in
            completionHandler()
        })
        present(alert)
    }

    func webView(
        _ webView: WKWebView,
        runJavaScriptConfirmPanelWithMessage message: String,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping (Bool) -> Void
    ) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel) { _ in
            completionHandler(false)
        })
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in
            completionHandler(true)
        })
        present(alert)
    }

    func webView(
        _ webView: WKWebView,
        runJavaScriptTextInputPanelWithPrompt prompt: String,
        defaultText: String?,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping (String?) -> Void
    ) {
        let alert = UIAlertController(title: nil, message: prompt, preferredStyle: .alert)
        alert.addTextField { textField in
            textField.text = defaultText
        }
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel) { _ in
            completionHandler(nil)
        })
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in
            completionHandler(alert.textFields?.first?.text)
        })
        present(alert)
    }

    func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
        let callbackId = pendingCameraCallbackId
        pendingCameraCallbackId = nil
        picker.dismiss(animated: true)
        send([
            "success": false,
            "cancelled": true
        ], callbackId: callbackId)
    }

    func imagePickerController(
        _ picker: UIImagePickerController,
        didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey : Any]
    ) {
        let callbackId = pendingCameraCallbackId
        pendingCameraCallbackId = nil
        picker.dismiss(animated: true)

        guard let image = (info[.editedImage] ?? info[.originalImage]) as? UIImage,
              let data = image.jpegData(compressionQuality: 0.85) else {
            send([
                "success": false,
                "error": "Failed to capture image."
            ], callbackId: callbackId)
            return
        }

        send([
            "success": true,
            "mimeType": "image/jpeg",
            "data": data.base64EncodedString()
        ], callbackId: callbackId)
    }

    func productsRequest(_ request: SKProductsRequest, didReceive response: SKProductsResponse) {
        guard let product = response.products.first else {
            send([
                "success": false,
                "error": "Product not found."
            ], callbackId: pendingPurchaseCallbackId)
            clearPurchaseState()
            return
        }

        productsRequest = nil
        SKPaymentQueue.default().add(SKPayment(product: product))
    }

    func request(_ request: SKRequest, didFailWithError error: Error) {
        send([
            "success": false,
            "error": error.localizedDescription
        ], callbackId: pendingPurchaseCallbackId)
        clearPurchaseState()
    }

    func paymentQueue(_ queue: SKPaymentQueue, updatedTransactions transactions: [SKPaymentTransaction]) {
        for transaction in transactions {
            switch transaction.transactionState {
            case .purchased:
                send([
                    "success": true,
                    "productId": transaction.payment.productIdentifier,
                    "transactionId": transaction.transactionIdentifier ?? ""
                ], callbackId: pendingPurchaseCallbackId)
                SKPaymentQueue.default().finishTransaction(transaction)
                clearPurchaseState()
            case .failed:
                let error = (transaction.error as? SKError)?.code == .paymentCancelled
                    ? "Purchase cancelled."
                    : (transaction.error?.localizedDescription ?? "Purchase failed.")
                send([
                    "success": false,
                    "productId": transaction.payment.productIdentifier,
                    "error": error
                ], callbackId: pendingPurchaseCallbackId)
                SKPaymentQueue.default().finishTransaction(transaction)
                clearPurchaseState()
            case .restored:
                send([
                    "success": true,
                    "productId": transaction.payment.productIdentifier,
                    "restored": true
                ], callbackId: pendingPurchaseCallbackId)
                SKPaymentQueue.default().finishTransaction(transaction)
                clearPurchaseState()
            case .deferred, .purchasing:
                break
            @unknown default:
                send([
                    "success": false,
                    "error": "Unknown purchase state."
                ], callbackId: pendingPurchaseCallbackId)
                clearPurchaseState()
            }
        }
    }

    @objc
    private func didRegisterForPushToken(_ notification: Notification) {
        guard let token = notification.object as? String else {
            return
        }

        lastPushToken = token
        dispatchEvent(name: "nativePushToken", detail: ["token": token])
    }

    @objc
    private func didFailToRegisterForPushNotifications(_ notification: Notification) {
        let message = (notification.object as? Error)?.localizedDescription ?? "Push registration failed."
        dispatchEvent(name: "nativePushRegistrationFailed", detail: ["error": message])
    }

    private func requestCamera(callbackId: String?) {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            presentCamera(callbackId: callbackId)
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                DispatchQueue.main.async {
                    guard let self else {
                        return
                    }

                    if granted {
                        self.presentCamera(callbackId: callbackId)
                    } else {
                        self.send([
                            "success": false,
                            "error": "Camera permission denied."
                        ], callbackId: callbackId)
                    }
                }
            }
        case .denied, .restricted:
            send([
                "success": false,
                "error": "Camera permission denied."
            ], callbackId: callbackId)
        @unknown default:
            send([
                "success": false,
                "error": "Unknown camera authorization state."
            ], callbackId: callbackId)
        }
    }

    private func presentCamera(callbackId: String?) {
        guard UIImagePickerController.isSourceTypeAvailable(.camera) else {
            send([
                "success": false,
                "error": "Camera is not available on this device."
            ], callbackId: callbackId)
            return
        }

        guard let presenter else {
            send([
                "success": false,
                "error": "No view controller is available to present the camera."
            ], callbackId: callbackId)
            return
        }

        pendingCameraCallbackId = callbackId

        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.delegate = self
        picker.allowsEditing = false
        presenter.present(picker, animated: true)
    }

    private func requestPushNotifications(callbackId: String?) {
        let center = UNUserNotificationCenter.current()
        center.requestAuthorization(options: [.alert, .badge, .sound]) { [weak self] granted, error in
            DispatchQueue.main.async {
                guard let self else {
                    return
                }

                if let error {
                    self.send([
                        "success": false,
                        "error": error.localizedDescription
                    ], callbackId: callbackId)
                    return
                }

                if granted {
                    UIApplication.shared.registerForRemoteNotifications()
                }

                var payload: [String: Any] = [
                    "success": granted,
                    "granted": granted
                ]

                if let token = self.lastPushToken {
                    payload["token"] = token
                }

                self.send(payload, callbackId: callbackId)
            }
        }
    }

    private func startPurchase(productId: String?, callbackId: String?) {
        guard let productId, !productId.isEmpty else {
            send([
                "success": false,
                "error": "Missing productId."
            ], callbackId: callbackId)
            return
        }

        guard SKPaymentQueue.canMakePayments() else {
            send([
                "success": false,
                "error": "In-app purchases are disabled."
            ], callbackId: callbackId)
            return
        }

        guard pendingPurchaseCallbackId == nil else {
            send([
                "success": false,
                "error": "Another purchase is already in progress."
            ], callbackId: callbackId)
            return
        }

        pendingPurchaseCallbackId = callbackId
        pendingProductId = productId

        let request = SKProductsRequest(productIdentifiers: Set([productId]))
        request.delegate = self
        productsRequest = request
        request.start()
    }

    private func clearPurchaseState() {
        pendingPurchaseCallbackId = nil
        pendingProductId = nil
        productsRequest = nil
    }

    private func present(_ viewController: UIViewController) {
        let target = presenter?.presentedViewController ?? presenter
        target?.present(viewController, animated: true)
    }

    private func send(_ payload: [String: Any], callbackId: String?) {
        guard let callbackId else {
            return
        }

        let envelope: [String: Any] = [
            "callbackId": callbackId,
            "payload": payload
        ]

        guard let json = jsonString(for: envelope) else {
            return
        }

        let script = "window.NativeApp && window.NativeApp._receive && window.NativeApp._receive(\(json));"
        DispatchQueue.main.async { [weak self] in
            self?.webView?.evaluateJavaScript(script, completionHandler: nil)
        }
    }

    private func dispatchEvent(name: String, detail: [String: Any]) {
        let event: [String: Any] = [
            "name": name,
            "detail": detail
        ]

        guard let json = jsonString(for: event) else {
            return
        }

        let script = """
        (function(event) {
            window.dispatchEvent(new CustomEvent(event.name, { detail: event.detail }));
        })(\(json));
        """

        DispatchQueue.main.async { [weak self] in
            self?.webView?.evaluateJavaScript(script, completionHandler: nil)
        }
    }

    private func jsonString(for object: Any) -> String? {
        guard JSONSerialization.isValidJSONObject(object),
              let data = try? JSONSerialization.data(withJSONObject: object),
              let string = String(data: data, encoding: .utf8) else {
            return nil
        }

        return string
    }

    private func isAllowedWebURL(_ url: URL) -> Bool {
        guard url.scheme?.lowercased() == "https",
              let host = url.host?.lowercased() else {
            return false
        }

        return allowedHosts.contains(where: { allowedHost in
            let normalized = allowedHost.lowercased()
            return host == normalized || host.hasSuffix(".\(normalized)")
        })
    }
}