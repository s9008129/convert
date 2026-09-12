// swift-tools-version: 6.0
import PackageDescription

// Deployment target is intentionally lower than macOS 26 so that the same
// binary can still be launched on older macOS hosts and truthfully report
// APPLE_UNAVAILABLE instead of failing at load time.
let package = Package(
    name: "apple_speech_cli",
    platforms: [.macOS(.v14)],
    products: [
        .library(name: "AppleSpeechKit", targets: ["AppleSpeechKit"]),
        .executable(name: "apple-speech-cli", targets: ["AppleSpeechCLI"]),
    ],
    targets: [
        .target(name: "AppleSpeechKit"),
        .executableTarget(
            name: "AppleSpeechCLI",
            dependencies: ["AppleSpeechKit"],
            path: "Sources/apple-speech-cli"
        ),
        .testTarget(
            name: "AppleSpeechKitTests",
            dependencies: ["AppleSpeechKit"]
        ),
    ]
)
