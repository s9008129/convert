import AVFAudio
import CoreMedia
import Foundation
import Speech

/// Result of a locale/asset evaluation performed without inference.
public struct LocaleReport: Sendable, Equatable {
    public var requestedIdentifier: String
    public var canonicalRequested: String
    public var resolvedIdentifier: String?
    public var isSupported: Bool
    public var isInSupportedList: Bool
    public var isInstalled: Bool
    public var assetStatus: String
    public var supportedLocalesCount: Int
    public var installedLocalesCount: Int
    public var supportedLocales: [String]
    public var installedLocales: [String]
    public var maximumReservedLocales: Int
    public var reservedLocales: [String]
    public var transcriberIsAvailable: Bool
}

public struct AssetInstallReport: Sendable, Equatable {
    public var attempted: Bool
    public var installed: Bool
    public var seconds: Double?
    public var errorMessage: String?
}

public struct TranscriptionOutcome: Sendable {
    public var text: String
    public var segments: [TranscriptSegment]
    public var totalResults: Int
    public var finalResults: Int
    public var volatileResults: Int
    public var audioDurationSeconds: Double?
    public var audioSampleRate: Double
    public var audioChannels: Int
    public var audioFrames: Int64
    public var preset: String
    public var segmentSource: String
    public var localeResolved: String?
    public var assetStatusBefore: String
    public var assetStatusAfter: String
    public var assetInstall: AssetInstallReport
    public var analysisSeconds: Double
    public var elapsedSeconds: Double
}

/// Thin, availability-guarded wrapper around the macOS 26 Speech framework.
public enum SpeechRuntime {
    public static let minimumMacOSMajorVersion = 26

    public static var isFrameworkImported: Bool { true }

    public static var isAPIAvailable: Bool {
        if #available(macOS 26.0, *) { return true }
        return false
    }

    @available(macOS 26.0, *)
    public static func assetStatusName(_ status: AssetInventory.Status) -> String {
        switch status {
        case .unsupported: return "unsupported"
        case .supported: return "supported"
        case .downloading: return "downloading"
        case .installed: return "installed"
        @unknown default: return "unknown"
        }
    }

    public static func localeReport(for identifier: String) async throws -> LocaleReport {
        guard HostInfo.isAppleSilicon else {
            throw AppleSpeechError(
                code: .unavailable,
                message: "Apple SpeechAnalyzer provider requires Apple Silicon; host architecture is \(HostInfo.architecture)"
            )
        }
        guard #available(macOS 26.0, *) else {
            throw AppleSpeechError(
                code: .unavailable,
                message: "SpeechAnalyzer requires macOS \(minimumMacOSMajorVersion) or newer; host is \(HostInfo.operatingSystemVersion)"
            )
        }
        return try await buildLocaleReport(for: identifier)
    }

    @available(macOS 26.0, *)
    private static func buildLocaleReport(for identifier: String) async throws -> LocaleReport {
        let requested = Locale(identifier: identifier)
        let supported = await SpeechTranscriber.supportedLocales
        let installed = await SpeechTranscriber.installedLocales
        let resolved = await SpeechTranscriber.supportedLocale(equivalentTo: requested)
        let transcriber = SpeechTranscriber(
            locale: resolved ?? requested,
            preset: .timeIndexedTranscriptionWithAlternatives
        )
        let status = await AssetInventory.status(forModules: [transcriber])
        let reserved = await AssetInventory.reservedLocales
        // `supportedLocale(equivalentTo:)` is NOT authoritative: it resolves
        // identifiers such as `th-TH` that have no assets at all. The asset
        // status is the load-bearing signal.
        let inSupportedList = resolved.map { resolvedLocale in
            supported.contains { LocaleEquivalence.isEquivalent($0.identifier, resolvedLocale.identifier) }
        } ?? false
        let isSupported = resolved != nil && status != .unsupported

        return LocaleReport(
            requestedIdentifier: identifier,
            canonicalRequested: LocaleEquivalence.canonicalIdentifier(identifier),
            resolvedIdentifier: resolved?.identifier,
            isSupported: isSupported,
            isInSupportedList: inSupportedList,
            isInstalled: status == .installed,
            assetStatus: assetStatusName(status),
            supportedLocalesCount: supported.count,
            installedLocalesCount: installed.count,
            supportedLocales: supported.map(\.identifier),
            installedLocales: installed.map(\.identifier),
            maximumReservedLocales: AssetInventory.maximumReservedLocales,
            reservedLocales: reserved.map(\.identifier),
            transcriberIsAvailable: SpeechTranscriber.isAvailable
        )
    }

    @available(macOS 26.0, *)
    public static func preset(named name: String) -> SpeechTranscriber.Preset {
        switch name {
        case "plain": return .transcription
        case "plain-alternatives": return .transcriptionWithAlternatives
        case "progressive": return .progressiveTranscription
        case "time-indexed-progressive": return .timeIndexedProgressiveTranscription
        default: return .timeIndexedTranscriptionWithAlternatives
        }
    }
}

/// Collects final results only. Volatile results are counted but never added to
/// the transcript.
public actor TranscriptionCollector {
    private var finalSegments: [TranscriptSegment] = []
    private var finalText: [String] = []
    private var totalResults = 0
    private var finalResults = 0
    private var volatileResults = 0

    public init() {}

    @available(macOS 26.0, *)
    public func record(text: AttributedString, range: CMTimeRange, isFinal: Bool, splitRuns: Bool) {
        totalResults += 1
        guard isFinal else {
            volatileResults += 1
            return
        }
        let pieces = TranscriptionCollector.segments(
            text: text,
            range: range,
            splitRuns: splitRuns
        )
        for piece in pieces {
            Diagnostics.debug(
                "final segment range=\(piece.start.map { String($0) } ?? "nil")..\(piece.end.map { String($0) } ?? "nil") text_chars=\(piece.text.count)"
            )
            finalSegments.append(piece)
        }
        finalText.append(String(text.characters))
        finalResults += 1
    }

    public func snapshot() -> (text: String, segments: [TranscriptSegment], total: Int, final: Int, volatile: Int) {
        let ordered = finalSegments.sorted { lhs, rhs in
            switch (lhs.start, rhs.start) {
            case let (l?, r?): return l < r
            case (nil, _?): return false
            case (_?, nil): return true
            default: return false
            }
        }
        return (finalText.joined(), ordered, totalResults, finalResults, volatileResults)
    }

    /// Splits an attributed transcript into run-level pieces when the
    /// time-indexed attribute is present, otherwise falls back to the result
    /// level range.
    @available(macOS 26.0, *)
    nonisolated static func segments(text: AttributedString, range: CMTimeRange, splitRuns: Bool) -> [TranscriptSegment] {
        if splitRuns {
            let attributed = attributedPieces(text)
            if !attributed.isEmpty {
                return attributed
            }
        }
        let bounds = TimeMapping.bounds(range)
        let trimmed = String(text.characters).trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return [] }
        return [TranscriptSegment(start: bounds.start, end: bounds.end, text: trimmed)]
    }

    @available(macOS 26.0, *)
    nonisolated static func attributedPieces(_ attributed: AttributedString) -> [TranscriptSegment] {
        var pieces: [TranscriptSegment] = []
        var currentRange: CMTimeRange?
        var currentText = ""
        for run in attributed.runs {
            let audioRange = run[AttributeScopes.SpeechAttributes.TimeRangeAttribute.self]
            if let currentRange, let audioRange, currentRange != audioRange {
                let bounds = TimeMapping.bounds(currentRange)
                let trimmed = currentText.trimmingCharacters(in: .whitespacesAndNewlines)
                if !trimmed.isEmpty {
                    pieces.append(TranscriptSegment(start: bounds.start, end: bounds.end, text: trimmed))
                }
                currentText = ""
            }
            if let audioRange { currentRange = audioRange }
            currentText += String(attributed[run.range].characters)
        }
        if let currentRange {
            let bounds = TimeMapping.bounds(currentRange)
            let trimmed = currentText.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty {
                pieces.append(TranscriptSegment(start: bounds.start, end: bounds.end, text: trimmed))
            }
        }
        return pieces
    }
}
