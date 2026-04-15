// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "EthWalletCore",
    platforms: [.iOS(.v15), .macOS(.v12)],
    products: [
        .library(name: "EthWalletCore", targets: ["EthWalletCore"]),
    ],
    dependencies: [
        .package(url: "https://github.com/attaswift/BigInt.git", from: "5.3.0"),
        .package(url: "https://github.com/krzyzanowskim/CryptoSwift.git", from: "1.8.0"),
        .package(url: "https://github.com/GigaBitcoin/secp256k1.swift", from: "0.10.0"),
    ],
    targets: [
        .target(
            name: "EthWalletCore",
            dependencies: [
                .product(name: "BigInt", package: "BigInt"),
                .product(name: "CryptoSwift", package: "CryptoSwift"),
                .product(name: "secp256k1", package: "secp256k1.swift"),
            ]
        ),
    ]
)
