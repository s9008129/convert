import Foundation

/// Stable, machine-readable error codes shared with the Python adapter.
/// These strings are part of the CLI contract; do not rename them.
public enum AppleSpeechErrorCode: String, Sendable, CaseIterable {
    case unavailable = "APPLE_UNAVAILABLE"
    case localeUnsupported = "APPLE_LOCALE_UNSUPPORTED"
    case assetError = "APPLE_ASSET_ERROR"
    case inputError = "APPLE_INPUT_ERROR"
    case transcriptionError = "APPLE_TRANSCRIPTION_ERROR"
    case timeout = "APPLE_TIMEOUT"
    case cancelled = "APPLE_CANCELLED"
    case outputInvalid = "APPLE_OUTPUT_INVALID"
}

/// Typed error carrying both the JSON `code` and the process exit code.
public struct AppleSpeechError: Error, Sendable, CustomStringConvertible {
    /// The error document travels on stdout, so its message is bounded too.
    public static let maximumMessageLength = 1000

    public let code: AppleSpeechErrorCode
    public let message: String

    public init(code: AppleSpeechErrorCode, message: String) {
        self.code = code
        self.message = AppleSpeechError.bounded(message)
    }

    /// Single-line, length-limited message. Messages inside the limit are
    /// returned untouched, so existing messages stay byte for byte identical.
    public static func bounded(_ message: String, limit: Int = AppleSpeechError.maximumMessageLength) -> String {
        guard message.count > limit else { return message }
        let collapsed = message
            .replacingOccurrences(of: "\r", with: " ")
            .replacingOccurrences(of: "\n", with: " ")
        return String(collapsed.prefix(limit)) + "…"
    }

    /// Exit code contract (mandatory):
    /// 0 success, 1 generic/transcription failure, 2 unsupported platform/API,
    /// 3 locale unsupported, 4 asset error, 5 invalid input,
    /// 6 transcription failure, 7 cancelled.
    ///
    /// `APPLE_TIMEOUT` and `APPLE_OUTPUT_INVALID` have no dedicated slot in the
    /// contract, so they use the generic `1`.
    public var exitCode: Int32 { code.exitCode }

    public var description: String { "\(code.rawValue): \(message)" }
}

extension AppleSpeechErrorCode {
    public var exitCode: Int32 {
        switch self {
        case .unavailable: return 2
        case .localeUnsupported: return 3
        case .assetError: return 4
        case .inputError: return 5
        case .transcriptionError: return 6
        case .cancelled: return 7
        case .timeout, .outputInvalid: return 1
        }
    }
}
