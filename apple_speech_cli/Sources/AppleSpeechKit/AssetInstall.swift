import Foundation
import Speech

// MARK: - Readiness policy

/// The asset/reservation facts needed to decide whether this invocation may
/// attempt an install.
public struct AssetReadiness: Sendable, Equatable {
    public var statusName: String
    public var reservedLocaleCount: Int
    public var maximumReservedLocaleCount: Int
    public var localeAlreadyReserved: Bool

    public init(
        statusName: String,
        reservedLocaleCount: Int,
        maximumReservedLocaleCount: Int,
        localeAlreadyReserved: Bool
    ) {
        self.statusName = statusName
        self.reservedLocaleCount = reservedLocaleCount
        self.maximumReservedLocaleCount = maximumReservedLocaleCount
        self.localeAlreadyReserved = localeAlreadyReserved
    }

    public var isInstalled: Bool { statusName == "installed" }
}

public enum AssetInstallDecision: String, Sendable, Equatable {
    case alreadyInstalled = "already_installed"
    case install
    case reservationExhausted = "reservation_exhausted"
}

public enum AssetInstallPolicy {
    /// DEC-06: install when the asset is missing, but never release another
    /// locale's reservation to make room. Reservation exhaustion is a typed
    /// asset error, not a silent failure.
    public static func decide(_ readiness: AssetReadiness) -> AssetInstallDecision {
        if readiness.isInstalled { return .alreadyInstalled }
        let maximum = readiness.maximumReservedLocaleCount
        if maximum > 0,
           readiness.reservedLocaleCount >= maximum,
           !readiness.localeAlreadyReserved {
            return .reservationExhausted
        }
        return .install
    }
}

// MARK: - Progress line protocol

/// Events emitted on stderr while the install phase runs. stdout stays
/// reserved for the single JSON document.
public enum AssetProgressEvent: Sendable, Equatable {
    /// The installation attempt began (including request acquisition).
    case started
    case progress(fractionCompleted: Double)
    case finished(seconds: Double)
    case failed(seconds: Double?, code: String, message: String)
}

/// Encodes the bounded, machine-parseable stderr progress protocol:
///
///     apple-speech-cli:progress {"phase":"asset_install","status":"started"}
///     apple-speech-cli:progress {"phase":"asset_install","status":"progress","fractionCompleted":0.42}
///     apple-speech-cli:progress {"phase":"asset_install","status":"finished","seconds":12.3}
///     apple-speech-cli:progress {"phase":"asset_install","status":"failed","seconds":12.3,"error_code":"APPLE_ASSET_ERROR","message":"…"}
///
/// Lines never carry transcript text, decoded audio or raw input bytes; every
/// free-form field is bounded.
public enum AssetProgressLine {
    public static let prefix = "apple-speech-cli:progress "
    public static let phase = "asset_install"
    public static let maximumMessageLength = 200
    public static let maximumLineLength = 512

    public static func encode(_ event: AssetProgressEvent) -> String {
        var pairs: [(key: String, value: JSONValue)] = [("phase", .string(phase))]
        switch event {
        case .started:
            pairs.append(("status", .string("started")))
        case .progress(let fractionCompleted):
            pairs.append(("status", .string("progress")))
            pairs.append(("fractionCompleted", .number(roundedFraction(fractionCompleted))))
        case .finished(let seconds):
            pairs.append(("status", .string("finished")))
            pairs.append(("seconds", .number(roundedSeconds(seconds))))
        case .failed(let seconds, let code, let message):
            pairs.append(("status", .string("failed")))
            if let seconds {
                pairs.append(("seconds", .number(roundedSeconds(seconds))))
            }
            pairs.append(("error_code", .string(Diagnostics.bounded(code, limit: 64))))
            pairs.append(("message", .string(Diagnostics.bounded(message, limit: maximumMessageLength))))
        }
        let body = JSONValue.object(pairs).serialized()
        guard body.count > maximumLineLength else { return prefix + body }
        return prefix + String(body.prefix(maximumLineLength))
    }

    /// `Progress.fractionCompleted` is clamped to `0...1` and rounded to two
    /// decimals so repeated sampling cannot produce unbounded line churn.
    public static func roundedFraction(_ value: Double) -> Double {
        guard value.isFinite else { return 0 }
        return (min(max(value, 0), 1) * 100).rounded() / 100
    }

    public static func roundedSeconds(_ value: Double) -> Double {
        guard value.isFinite else { return 0 }
        return (max(value, 0) * 1000).rounded() / 1000
    }
}

/// Rate-limits and caps the progress lines emitted for one install. Pure and
/// therefore deterministic under test.
public struct AssetProgressSampler: Sendable {
    public let minimumFractionDelta: Double
    public let maximumLines: Int

    private var lastEmittedFraction: Double?
    private var emittedLines = 0
    private var reachedCompletion = false

    public init(minimumFractionDelta: Double = 0.01, maximumLines: Int = 200) {
        self.minimumFractionDelta = minimumFractionDelta
        self.maximumLines = maximumLines
    }

    public var emittedProgressLines: Int { emittedLines }
    public var isExhausted: Bool { emittedLines >= maximumLines || reachedCompletion }

    public mutating func sample(fractionCompleted: Double) -> AssetProgressEvent? {
        guard !isExhausted, fractionCompleted.isFinite else { return nil }
        let fraction = AssetProgressLine.roundedFraction(fractionCompleted)
        if let last = lastEmittedFraction,
           fraction - last < minimumFractionDelta,
           fraction < 1 {
            return nil
        }
        lastEmittedFraction = fraction
        emittedLines += 1
        if fraction >= 1 { reachedCompletion = true }
        return .progress(fractionCompleted: fraction)
    }
}

// MARK: - Framework seam

/// Non-blocking, isolation-safe read of `Foundation.Progress.fractionCompleted`.
public protocol AssetProgressSource: Sendable {
    func fractionCompleted() -> Double
}

/// `Progress` is safe to read from any thread but is not declared `Sendable`,
/// so the wrapper carries the unchecked conformance.
public final class ProgressFractionSource: AssetProgressSource, @unchecked Sendable {
    private let progress: Progress

    public init(progress: Progress) {
        self.progress = progress
    }

    public func fractionCompleted() -> Double {
        progress.fractionCompleted
    }
}

/// One installable asset request (`AssetInstallationRequest` in the real API).
public protocol AssetInstallOperation: Sendable {
    func progressSource() -> any AssetProgressSource
    func downloadAndInstall() async throws
}

public struct AssetReservationState: Sendable, Equatable {
    public var reservedLocaleCount: Int
    public var maximumReservedLocaleCount: Int
    public var localeAlreadyReserved: Bool

    public init(reservedLocaleCount: Int, maximumReservedLocaleCount: Int, localeAlreadyReserved: Bool) {
        self.reservedLocaleCount = reservedLocaleCount
        self.maximumReservedLocaleCount = maximumReservedLocaleCount
        self.localeAlreadyReserved = localeAlreadyReserved
    }
}

/// Everything the install flow needs from the Speech framework. Injecting it
/// keeps the flow and its tests free of network, assets and macOS 26.
public protocol SpeechAssetEnvironment: Sendable {
    func statusName() async -> String
    func reservationState(localeIdentifier: String) async -> AssetReservationState
    /// `nil` when the framework reports that no installation request applies.
    func makeInstallationRequest() async throws -> (any AssetInstallOperation)?
}

// MARK: - Progress monitor

/// Samples install progress concurrently with `downloadAndInstall()`. The
/// sampler never blocks the install and stops as soon as the install ends.
public actor AssetProgressMonitor {
    private let source: any AssetProgressSource
    private let intervalSeconds: Double
    private let sampleInterval: @Sendable (Double) async -> Void
    private let emitter: @Sendable (AssetProgressEvent) -> Void
    private var sampler: AssetProgressSampler
    private var task: Task<Void, Never>?

    public init(
        source: any AssetProgressSource,
        intervalSeconds: Double = 0.5,
        minimumFractionDelta: Double = 0.01,
        maximumLines: Int = 200,
        sampleInterval: @escaping @Sendable (Double) async -> Void,
        emit: @escaping @Sendable (AssetProgressEvent) -> Void
    ) {
        self.source = source
        self.intervalSeconds = intervalSeconds
        self.sampleInterval = sampleInterval
        self.emitter = emit
        self.sampler = AssetProgressSampler(
            minimumFractionDelta: minimumFractionDelta,
            maximumLines: maximumLines
        )
    }

    /// Begins sampling. The caller emits `started` before calling this, so the
    /// line order stays under the flow's control. Returns immediately; the
    /// install itself is awaited by the caller.
    public func start() {
        guard task == nil else { return }
        task = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                await self.pause()
                if Task.isCancelled { return }
                guard let event = await self.takeSample() else {
                    if await self.isExhausted() { return }
                    continue
                }
                await self.publish(event)
                if await self.isExhausted() { return }
            }
        }
    }

    /// Cancels sampling and waits for the sampler to finish so that emitted
    /// lines stay strictly ordered before `finished`/`failed`.
    public func stop() async {
        task?.cancel()
        await task?.value
        task = nil
    }

    public func progressLines() -> Int {
        sampler.emittedProgressLines
    }

    private func pause() async {
        await sampleInterval(intervalSeconds)
    }

    private func takeSample() -> AssetProgressEvent? {
        guard !sampler.isExhausted else { return nil }
        return sampler.sample(fractionCompleted: source.fractionCompleted())
    }

    private func publish(_ event: AssetProgressEvent) {
        emitter(event)
    }

    private func isExhausted() -> Bool {
        sampler.isExhausted
    }
}

// MARK: - Flow

public struct AssetInstallFlowResult: Sendable, Equatable {
    public var decision: AssetInstallDecision
    public var statusBefore: String
    public var statusAfter: String
    public var attempted: Bool
    public var installed: Bool
    public var seconds: Double?
    public var errorMessage: String?
    public var progressLines: Int
}

public enum AssetInstallFlow {
    public static let defaultProgressIntervalSeconds = 0.5
    public static let defaultMaximumProgressLines = 200

    /// REQ-06 / DEC-06. Returns only when the asset is installed for this
    /// invocation; every other outcome throws `APPLE_ASSET_ERROR` (exit 4).
    /// No locale reservation is ever released here: reservation exhaustion is
    /// reported as a typed asset error instead.
    public static func ensureReady(
        statusBefore: String,
        localeIdentifier: String,
        environment: any SpeechAssetEnvironment,
        emit: @escaping @Sendable (AssetProgressEvent) -> Void = { _ in },
        progressIntervalSeconds: Double = AssetInstallFlow.defaultProgressIntervalSeconds,
        minimumFractionDelta: Double = 0.01,
        maximumProgressLines: Int = AssetInstallFlow.defaultMaximumProgressLines,
        sampleInterval: @escaping @Sendable (Double) async -> Void = { seconds in
            let nanoseconds = UInt64(max(seconds, 0.001) * 1_000_000_000)
            try? await Task.sleep(nanoseconds: nanoseconds)
        },
        now: @escaping @Sendable () -> Double = { Date().timeIntervalSinceReferenceDate }
    ) async throws -> AssetInstallFlowResult {
        let reservation = await environment.reservationState(localeIdentifier: localeIdentifier)
        let readiness = AssetReadiness(
            statusName: statusBefore,
            reservedLocaleCount: reservation.reservedLocaleCount,
            maximumReservedLocaleCount: reservation.maximumReservedLocaleCount,
            localeAlreadyReserved: reservation.localeAlreadyReserved
        )

        switch AssetInstallPolicy.decide(readiness) {
        case .alreadyInstalled:
            return AssetInstallFlowResult(
                decision: .alreadyInstalled,
                statusBefore: statusBefore,
                statusAfter: statusBefore,
                attempted: false,
                installed: true,
                seconds: nil,
                errorMessage: nil,
                progressLines: 0
            )
        case .reservationExhausted:
            let message = "speech asset reservations are exhausted (\(reservation.reservedLocaleCount)/\(reservation.maximumReservedLocaleCount)) and '\(localeIdentifier)' is not reserved"
            let bounded = Diagnostics.bounded(message)
            emit(.failed(seconds: nil, code: AppleSpeechErrorCode.assetError.rawValue, message: bounded))
            throw AppleSpeechError(code: .assetError, message: bounded)
        case .install:
            break
        }

        let installStarted = now()
        emit(.started)

        let request: (any AssetInstallOperation)?
        do {
            request = try await environment.makeInstallationRequest()
        } catch {
            let seconds = AssetProgressLine.roundedSeconds(now() - installStarted)
            let bounded = Diagnostics.bounded(error.localizedDescription)
            emit(.failed(seconds: seconds, code: AppleSpeechErrorCode.assetError.rawValue, message: bounded))
            throw AppleSpeechError(
                code: .assetError,
                message: "speech asset installation request failed for '\(localeIdentifier)': \(bounded)"
            )
        }

        guard let request else {
            let seconds = AssetProgressLine.roundedSeconds(now() - installStarted)
            let statusAfter = await environment.statusName()
            guard statusAfter == "installed" else {
                let bounded = Diagnostics.bounded(
                    "no asset installation request was offered and the asset status is '\(statusAfter)'"
                )
                emit(.failed(seconds: seconds, code: AppleSpeechErrorCode.assetError.rawValue, message: bounded))
                throw AppleSpeechError(
                    code: .assetError,
                    message: "speech asset for '\(localeIdentifier)' is not ready for this invocation: \(bounded)"
                )
            }
            emit(.finished(seconds: seconds))
            return AssetInstallFlowResult(
                decision: .install,
                statusBefore: statusBefore,
                statusAfter: statusAfter,
                attempted: false,
                installed: true,
                seconds: seconds,
                errorMessage: nil,
                progressLines: 0
            )
        }

        let monitor = AssetProgressMonitor(
            source: request.progressSource(),
            intervalSeconds: progressIntervalSeconds,
            minimumFractionDelta: minimumFractionDelta,
            maximumLines: maximumProgressLines,
            sampleInterval: sampleInterval,
            emit: emit
        )
        await monitor.start()
        do {
            try await request.downloadAndInstall()
        } catch {
            await monitor.stop()
            let seconds = AssetProgressLine.roundedSeconds(now() - installStarted)
            let bounded = Diagnostics.bounded(error.localizedDescription)
            emit(.failed(seconds: seconds, code: AppleSpeechErrorCode.assetError.rawValue, message: bounded))
            throw AppleSpeechError(
                code: .assetError,
                message: "speech asset installation failed for '\(localeIdentifier)' after \(seconds)s: \(bounded)"
            )
        }
        await monitor.stop()

        let seconds = AssetProgressLine.roundedSeconds(now() - installStarted)
        let progressLines = await monitor.progressLines()
        let statusAfter = await environment.statusName()
        guard statusAfter == "installed" else {
            let bounded = Diagnostics.bounded(
                "downloadAndInstall() returned but the asset status is '\(statusAfter)'; a deferred install is not ready for this invocation"
            )
            emit(.failed(seconds: seconds, code: AppleSpeechErrorCode.assetError.rawValue, message: bounded))
            throw AppleSpeechError(
                code: .assetError,
                message: "speech asset for '\(localeIdentifier)' is not installed: \(bounded)"
            )
        }
        emit(.finished(seconds: seconds))
        return AssetInstallFlowResult(
            decision: .install,
            statusBefore: statusBefore,
            statusAfter: statusAfter,
            attempted: true,
            installed: true,
            seconds: seconds,
            errorMessage: nil,
            progressLines: progressLines
        )
    }
}

// MARK: - Live environment

@available(macOS 26.0, *)
public struct LiveAssetInstallOperation: AssetInstallOperation {
    private let request: AssetInstallationRequest

    public init(request: AssetInstallationRequest) {
        self.request = request
    }

    public func progressSource() -> any AssetProgressSource {
        ProgressFractionSource(progress: request.progress)
    }

    public func downloadAndInstall() async throws {
        try await request.downloadAndInstall()
    }
}

@available(macOS 26.0, *)
public struct LiveSpeechAssetEnvironment: SpeechAssetEnvironment {
    private let transcriber: SpeechTranscriber

    public init(transcriber: SpeechTranscriber) {
        self.transcriber = transcriber
    }

    public func statusName() async -> String {
        SpeechRuntime.assetStatusName(await AssetInventory.status(forModules: [transcriber]))
    }

    public func reservationState(localeIdentifier: String) async -> AssetReservationState {
        let reserved = await AssetInventory.reservedLocales
        return AssetReservationState(
            reservedLocaleCount: reserved.count,
            maximumReservedLocaleCount: AssetInventory.maximumReservedLocales,
            localeAlreadyReserved: reserved.contains {
                LocaleEquivalence.isEquivalent($0.identifier, localeIdentifier)
            }
        )
    }

    public func makeInstallationRequest() async throws -> (any AssetInstallOperation)? {
        guard let request = try await AssetInventory.assetInstallationRequest(supporting: [transcriber]) else {
            return nil
        }
        return LiveAssetInstallOperation(request: request)
    }
}
