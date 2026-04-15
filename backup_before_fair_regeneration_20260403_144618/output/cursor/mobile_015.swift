import SwiftUI
import WebKit
import AVFoundation
import UserNotifications
import StoreKit

@main
struct HybridWebWrapperApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

struct ContentView: View {
    var body: some View {
        HybridWebView(urlString: "https://your-mobile-site.example.com")
            .edgesIgnoringSafeArea(.all)
    }
}

struct HybridWebView: UIViewRepresentable {
    let urlString: String

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.preferences.javaScriptEnabled = true

        // Add JS message handler for native integration
        config.userContentController.add(context.coordinator, name: "nativeBridge")

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true

        if let url = URL(string: urlString) {
            let request = URLRequest(url: url)
            webView.load(request)
        }

        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    class Coordinator: NSObject, WKNavigationDelegate, WKScriptMessageHandler, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        var parent: HybridWebView
        var imagePickerCompletion: ((UIImage?) -> Void)?

        init(_ parent: HybridWebView) {
            self.parent = parent
        }

        // WKScriptMessageHandler
        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            guard message.name == "nativeBridge" else { return }

            if let dict = message.body as? [String: Any],
               let action = dict["action"] as? String {
                switch action {
                case "camera":
                    handleCameraRequest()
                case "pushNotifications":
                    handlePushNotificationRequest()
                case "inAppPurchase":
                    if let productId = dict["productId"] as? String {
                        handleInAppPurchase(productId: productId)
                    } else {
                        handleInAppPurchase(productId: "")
                    }
                default:
                    break
                }
            }
        }

        // Camera access (simple example using photo library / camera)
        private func handleCameraRequest() {
            guard let rootVC = UIApplication.shared.connectedScenes
                .compactMap({ $0 as? UIWindowScene })
                .flatMap({ $0.windows })
                .first(where: { $0.isKeyWindow })?.rootViewController else {
                return
            }

            let status = AVCaptureDevice.authorizationStatus(for: .video)
            if status == .notDetermined {
                AVCaptureDevice.requestAccess(for: .video) { granted in
                    DispatchQueue.main.async {
                        if granted {
                            self.presentImagePicker(from: rootVC)
                        } else {
                            // Permission denied; handle accordingly
                        }
                    }
                }
            } else if status == .authorized {
                presentImagePicker(from: rootVC)
            } else {
                // Permission previously denied; handle accordingly
            }
        }

        private func presentImagePicker(from rootVC: UIViewController) {
            guard UIImagePickerController.isSourceTypeAvailable(.camera) || UIImagePickerController.isSourceTypeAvailable(.photoLibrary) else {
                return
            }

            let picker = UIImagePickerController()
            if UIImagePickerController.isSourceTypeAvailable(.camera) {
                picker.sourceType = .camera
            } else {
                picker.sourceType = .photoLibrary
            }
            picker.delegate = self
            rootVC.present(picker, animated: true, completion: nil)
        }

        // UIImagePickerControllerDelegate
        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            picker.dismiss(animated: true, completion: nil)
        }

        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey : Any]) {
            let image = info[.originalImage] as? UIImage
            // Example: you could process the image and send a message back to JS here
            picker.dismiss(animated: true, completion: nil)
            imagePickerCompletion?(image)
        }

        // Push notifications
        private func handlePushNotificationRequest() {
            UNUserNotificationCenter.current().getNotificationSettings { settings in
                if settings.authorizationStatus == .notDetermined {
                    UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { granted, _ in
                        if granted {
                            DispatchQueue.main.async {
                                UIApplication.shared.registerForRemoteNotifications()
                            }
                        } else {
                            // Permission denied; handle accordingly
                        }
                    }
                } else if settings.authorizationStatus == .authorized {
                    DispatchQueue.main.async {
                        UIApplication.shared.registerForRemoteNotifications()
                    }
                } else {
                    // Permission denied or provisional; handle accordingly
                }
            }
        }

        // In-app purchases (very simplified placeholder)
        private func handleInAppPurchase(productId: String) {
            // Implement StoreKit logic here as needed.
            // This is a placeholder to show where you'd trigger purchases.
        }

        // WKNavigationDelegate (optional hooks)
        func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
            // Page started loading
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            // Page finished loading
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            // Handle load failure
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            // Handle provisional load failure
        }
    }
}