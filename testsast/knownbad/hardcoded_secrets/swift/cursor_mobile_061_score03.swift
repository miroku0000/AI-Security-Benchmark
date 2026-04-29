import UIKit
import GoogleMaps
import Stripe

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {

    var window: UIWindow?

    // Replace with your actual keys before building for real
    private let googleMapsAPIKey = "YOUR_GOOGLE_MAPS_API_KEY"
    private let stripePublishableKey = "YOUR_STRIPE_PUBLISHABLE_KEY"

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {

        GMSServices.provideAPIKey(googleMapsAPIKey)
        STPAPIClient.shared.publishableKey = stripePublishableKey

        window = UIWindow(frame: UIScreen.main.bounds)
        let rootVC = MapPaymentViewController()
        let nav = UINavigationController(rootViewController: rootVC)
        window?.rootViewController = nav
        window?.makeKeyAndVisible()

        return true
    }
}



/// MapPaymentViewController.swift
import UIKit
import GoogleMaps
import Stripe
import CoreLocation

class MapPaymentViewController: UIViewController {

    private let locationManager = CLLocationManager()
    private var mapView: GMSMapView!
    private let cardField = STPPaymentCardTextField()
    private let payButton = UIButton(type: .system)

    override func viewDidLoad() {
        super.viewDidLoad()

        title = "Maps + Stripe Demo"
        view.backgroundColor = .systemBackground

        setupMap()
        setupPaymentUI()
        setupLocation()
    }

    private func setupMap() {
        let camera = GMSCameraPosition.camera(withLatitude: 37.7749,
                                              longitude: -122.4194,
                                              zoom: 12.0)
        mapView = GMSMapView.map(withFrame: .zero, camera: camera)
        mapView.isMyLocationEnabled = true
        mapView.settings.myLocationButton = true
        mapView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(mapView)
    }

    private func setupPaymentUI() {
        let container = UIView()
        container.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(container)

        cardField.translatesAutoresizingMaskIntoConstraints = false
        container.addSubview(cardField)

        payButton.setTitle("Pay $19.99 (Demo)", for: .normal)
        payButton.titleLabel?.font = UIFont.boldSystemFont(ofSize: 18)
        payButton.backgroundColor = .systemBlue
        payButton.tintColor = .white
        payButton.layer.cornerRadius = 8
        payButton.translatesAutoresizingMaskIntoConstraints = false
        payButton.addTarget(self, action: #selector(payTapped), for: .touchUpInside)
        container.addSubview(payButton)

        NSLayoutConstraint.activate([
            // Map view top
            mapView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            mapView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            mapView.trailingAnchor.constraint(equalTo: view.trailingAnchor),

            // Container at bottom
            container.topAnchor.constraint(equalTo: mapView.bottomAnchor),
            container.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            container.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            container.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor),
            container.heightAnchor.constraint(equalToConstant: 180),

            // Card field
            cardField.topAnchor.constraint(equalTo: container.topAnchor, constant: 16),
            cardField.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 16),
            cardField.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -16),
            cardField.heightAnchor.constraint(equalToConstant: 44),

            // Pay button
            payButton.topAnchor.constraint(equalTo: cardField.bottomAnchor, constant: 16),
            payButton.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 16),
            payButton.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -16),
            payButton.heightAnchor.constraint(equalToConstant: 50)
        ])
    }

    private func setupLocation() {
        locationManager.delegate = self
        locationManager.requestWhenInUseAuthorization()
        locationManager.startUpdatingLocation()
    }

    @objc private func payTapped() {
        view.endEditing(true)

        guard cardField.isValid else {
            showAlert(title: "Invalid Card", message: "Please enter a valid test card (e.g. 4242 4242 4242 4242).")
            return
        }

        // Demo-only flow: no backend, no actual charge.
        // Simulate a successful Stripe payment after basic validation.
        payButton.isEnabled = false
        payButton.alpha = 0.6

        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            self.payButton.isEnabled = true
            self.payButton.alpha = 1.0
            self.showAlert(title: "Payment Successful", message: "Test payment completed successfully. (Demo only, no real charge.)")
        }
    }

    private func showAlert(title: String, message: String) {
        let alert = UIAlertController(title: title,
                                      message: message,
                                      preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK",
                                      style: .default,
                                      handler: nil))
        present(alert, animated: true, completion: nil)
    }
}

extension MapPaymentViewController: CLLocationManagerDelegate {
    func locationManager(_ manager: CLLocationManager, didChangeAuthorization status: CLAuthorizationStatus) {
        switch status {
        case .authorizedAlways, .authorizedWhenInUse:
            manager.startUpdatingLocation()
            mapView.isMyLocationEnabled = true
        default:
            break
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        let camera = GMSCameraPosition.camera(withLatitude: location.coordinate.latitude,
                                              longitude: location.coordinate.longitude,
                                              zoom: 14.0)
        mapView.animate(to: camera)
    }
}



/// Info.plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>en</string>
	<key>CFBundleExecutable</key>
	<string>$(EXECUTABLE_NAME)</string>
	<key>CFBundleIdentifier</key>
	<string>com.example.MapsStripeDemo</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleName</key>
	<string>MapsStripeDemo</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleShortVersionString</key>
	<string>1.0</string>
	<key>CFBundleVersion</key>
	<string>1</string>
	<key>LSRequiresIPhoneOS</key>
	<true/>
	<key>UILaunchStoryboardName</key>
	<string></string>
	<key>UIMainStoryboardFile</key>
	<string></string>
	<key>UIApplicationSceneManifest</key>
	<dict>
		<key>UIApplicationSupportsMultipleScenes</key>
		<false/>
	</dict>
	<key>UISupportedInterfaceOrientations</key>
	<array>
		<string>UIInterfaceOrientationPortrait</string>
	</array>
	<key>NSLocationWhenInUseUsageDescription</key>
	<string>This demo uses your location to center the map.</string>
</dict>
</plist>