import Foundation
import Speech
import XCTest

@testable import AppleSpeechKit

/// Deterministic coverage for the REQ-06 / DEC-06 asset install flow.
///
/// Nothing here touches the Speech framework, the network or a real asset: the
/// install seam (`SpeechAssetEnvironment`) is injected, so a test can never
/// trigger a model download and can never depend on whether an asset happens
/// to be installed on the host.
final class AssetInstallTests: XCTestCase {

    // MARK: - Policy

    func testPolicySkipsInstallWhenAssetIsInstalled() {
        let readiness = AssetReadiness(
            statusName: "installed",
            reservedLocaleCount: 5,
            maximumReservedLocaleCount: 5,
            localeAlreadyReserved: false
        )
        XCTAssertEqual(AssetInstallPolicy.decide(readiness), .alreadyInstalled)
    }

    func testPolicyInstallsWhenAssetIsMissing() {
        for status in ["supported", "downloading", "unknown"] {
            let readiness = AssetReadiness(
                statusName: status,
                reservedLocaleCount: 1,
                maximumReservedLocaleCount: 5,
                localeAlreadyReserved: true
            )
            XCTAssertEqual(AssetInstallPolicy.decide(readiness), .install, "status \(status)")
        }
    }

    func testPolicyInstallsWhileReservationsRemain() {
        let readiness = AssetReadiness(
            statusName: "supported",
            reservedLocaleCount: 4,
            maximumReservedLocaleCount: 5,
            localeAlreadyReserved: false
        )
        XCTAssertEqual(AssetInstallPolicy.decide(readiness), .install)
    }

    func testPolicyReportsReservationExhaustion() {
        let exhausted = AssetReadiness(
            statusName: "supported",
            reservedLocaleCount: 5,
            maximumReservedLocaleCount: 5,
            localeAlreadyReserved: false
        )
        XCTAssertEqual(AssetInstallPolicy.decide(exhausted), .reservationExhausted)
    }

    func testPolicyNeverTreatsAnExistingReservationAsExhaustion() {
        let alreadyReserved = AssetReadiness(
            statusName: "supported",
            reservedLocaleCount: 5,
            maximumReservedLocaleCount: 5,
            localeAlreadyReserved: true
        )
        XCTAssertEqual(AssetInstallPolicy.decide(alreadyReserved), .install)
    }

    func testPolicyIgnoresAnUnreportedReservationLimit() {
        // A host that reports no limit must not be treated as exhausted.
        let unknownMaximum = AssetReadiness(
            statusName: "supported",
            reservedLocaleCount: 0,
            maximumReservedLocaleCount: 0,
            localeAlreadyReserved: false
        )
        XCTAssertEqual(AssetInstallPolicy.decide(unknownMaximum), .install)
    }

    // MARK: - stderr progress-line protocol

    func testProgressLineProtocolIsVerbatimStable() {
        XCTAssertEqual(
            AssetProgressLine.encode(.started),
            "apple-speech-cli:progress {\"phase\":\"asset_install\",\"status\":\"started\"}"
        )
        XCTAssertEqual(
            AssetProgressLine.encode(.progress(fractionCompleted: 0.42)),
            "apple-speech-cli:progress {\"phase\":\"asset_install\",\"status\":\"progress\",\"fractionCompleted\":0.42}"
        )
        XCTAssertEqual(
            AssetProgressLine.encode(.finished(seconds: 12.3)),
            "apple-speech-cli:progress {\"phase\":\"asset_install\",\"status\":\"finished\",\"seconds\":12.3}"
        )
        XCTAssertEqual(
            AssetProgressLine.encode(.failed(seconds: 12.3, code: "APPLE_ASSET_ERROR", message: "no asset")),
            "apple-speech-cli:progress {\"phase\":\"asset_install\",\"status\":\"failed\",\"seconds\":12.3,\"error_code\":\"APPLE_ASSET_ERROR\",\"message\":\"no asset\"}"
        )
    }

    func testProgressLineAlwaysCarriesThePrefixAndASingleJSONBody() throws {
        let events: [AssetProgressEvent] = [
            .started,
            .progress(fractionCompleted: 0),
            .progress(fractionCompleted: 0.5),
            .progress(fractionCompleted: 1),
            .finished(seconds: 0.001),
            .failed(seconds: nil, code: "APPLE_ASSET_ERROR", message: "deferred"),
        ]
        for event in events {
            let line = AssetProgressLine.encode(event)
            XCTAssertTrue(line.hasPrefix("apple-speech-cli:progress "), line)
            XCTAssertFalse(line.contains("\n"), line)
            XCTAssertLessThanOrEqual(line.count, AssetProgressLine.prefix.count + AssetProgressLine.maximumLineLength)
            let body = String(line.dropFirst(AssetProgressLine.prefix.count))
            let parsed = try JSONSerialization.jsonObject(with: Data(body.utf8)) as? [String: Any]
            XCTAssertEqual(parsed?["phase"] as? String, "asset_install")
            XCTAssertNotNil(parsed?["status"] as? String)
        }
    }

    func testProgressLineClampsFractionsAndRejectsNonFiniteValues() {
        XCTAssertEqual(
            AssetProgressLine.encode(.progress(fractionCompleted: 1.7)),
            "apple-speech-cli:progress {\"phase\":\"asset_install\",\"status\":\"progress\",\"fractionCompleted\":1.0}"
        )
        XCTAssertEqual(
            AssetProgressLine.encode(.progress(fractionCompleted: -3)),
            "apple-speech-cli:progress {\"phase\":\"asset_install\",\"status\":\"progress\",\"fractionCompleted\":0.0}"
        )
        XCTAssertEqual(
            AssetProgressLine.roundedFraction(.nan),
            0
        )
        XCTAssertEqual(
            AssetProgressLine.roundedSeconds(.infinity),
            0
        )
    }

    func testProgressLineBoundsFreeFormFields() throws {
        let message = String(repeating: "x", count: 5_000)
        let line = AssetProgressLine.encode(.failed(seconds: 1, code: "APPLE_ASSET_ERROR", message: message))
        XCTAssertLessThan(line.count, 600)
        let body = String(line.dropFirst(AssetProgressLine.prefix.count))
        let parsed = try JSONSerialization.jsonObject(with: Data(body.utf8)) as? [String: Any]
        let encodedMessage = try XCTUnwrap(parsed?["message"] as? String)
        XCTAssertEqual(encodedMessage.count, AssetProgressLine.maximumMessageLength + 1)
        XCTAssertTrue(encodedMessage.hasSuffix("…"))
    }

    func testProgressLinesNeverCarryTranscriptText() throws {
        // The encoder has no transcript input at all; this asserts the one
        // free-form field is bounded and stripped of line breaks.
        let line = AssetProgressLine.encode(.failed(seconds: 2, code: "APPLE_ASSET_ERROR", message: "line1\nline2"))
        XCTAssertFalse(line.contains("\n"))
    }

    // MARK: - Sampler

    func testSamplerThrottlesSmallChangesAndCapsLines() {
        var sampler = AssetProgressSampler(minimumFractionDelta: 0.01, maximumLines: 2)
        XCTAssertEqual(sampler.sample(fractionCompleted: 0.25), .progress(fractionCompleted: 0.25))
        XCTAssertNil(sampler.sample(fractionCompleted: 0.2501))
        XCTAssertEqual(sampler.sample(fractionCompleted: 0.5), .progress(fractionCompleted: 0.5))
        XCTAssertNil(sampler.sample(fractionCompleted: 0.9))
        XCTAssertEqual(sampler.emittedProgressLines, 2)
        XCTAssertTrue(sampler.isExhausted)
    }

    func testSamplerEmitsCompletionExactlyOnce() {
        var sampler = AssetProgressSampler(minimumFractionDelta: 0.01, maximumLines: 10)
        XCTAssertEqual(sampler.sample(fractionCompleted: 0.4), .progress(fractionCompleted: 0.4))
        XCTAssertEqual(sampler.sample(fractionCompleted: 1.0), .progress(fractionCompleted: 1.0))
        XCTAssertNil(sampler.sample(fractionCompleted: 1.0))
        XCTAssertTrue(sampler.isExhausted)
    }

    func testSamplerIgnoresNonFiniteFractions() {
        var sampler = AssetProgressSampler()
        XCTAssertNil(sampler.sample(fractionCompleted: .nan))
        XCTAssertNil(sampler.sample(fractionCompleted: .infinity))
        XCTAssertEqual(sampler.emittedProgressLines, 0)
    }

    // MARK: - Flow

    func testEnsureReadyIsANoOpWhenTheAssetIsAlreadyInstalled() async throws {
        let recorder = AssetEventRecorder()
        let environment = FakeSpeechAssetEnvironment(statuses: ["installed"])

        let result = try await AssetInstallFlow.ensureReady(
            statusBefore: "installed",
            localeIdentifier: "zh_TW",
            environment: environment,
            emit: { recorder.record($0) },
            now: { 1000 }
        )

        XCTAssertEqual(result.decision, .alreadyInstalled)
        XCTAssertEqual(result.statusAfter, "installed")
        XCTAssertFalse(result.attempted)
        XCTAssertTrue(result.installed)
        XCTAssertNil(result.seconds)
        XCTAssertEqual(result.progressLines, 0)
        XCTAssertTrue(recorder.events.isEmpty)
        XCTAssertEqual(environment.calls.status, 0, "the fast path must not re-query the framework")
        XCTAssertEqual(environment.calls.request, 0, "the fast path must not ask for an installation request")
    }

    func testEnsureReadyInstallsAndReportsProgress() async throws {
        let recorder = AssetEventRecorder()
        let clock = FakeClock(start: 1_000, end: 1_012.3)
        let operation = FakeAssetInstallOperation(
            source: FakeProgressSource(fractions: [0.25, 0.5, 0.75, 1.0]),
            completion: .success,
            recorder: recorder,
            minimumProgressEventsBeforeFinishing: 2
        )
        let environment = FakeSpeechAssetEnvironment(statuses: ["installed"], operation: operation)

        let result = try await AssetInstallFlow.ensureReady(
            statusBefore: "supported",
            localeIdentifier: "zh_TW",
            environment: environment,
            emit: { recorder.record($0) },
            maximumProgressLines: 2,
            sampleInterval: { _ in await Task.yield() },
            now: { clock.now() }
        )

        XCTAssertEqual(recorder.events, [
            .started,
            .progress(fractionCompleted: 0.25),
            .progress(fractionCompleted: 0.5),
            .finished(seconds: 12.3),
        ])
        XCTAssertEqual(result.decision, .install)
        XCTAssertEqual(result.statusBefore, "supported")
        XCTAssertEqual(result.statusAfter, "installed")
        XCTAssertTrue(result.attempted)
        XCTAssertTrue(result.installed)
        XCTAssertEqual(result.seconds, 12.3)
        XCTAssertEqual(result.progressLines, 2)
        XCTAssertEqual(environment.calls.request, 1)
        XCTAssertEqual(environment.calls.status, 1)
        XCTAssertEqual(environment.calls.reservation, 1)
    }

    func testEnsureReadyFailsWithAssetErrorWhenInstallThrows() async throws {
        let recorder = AssetEventRecorder()
        let clock = FakeClock(start: 1_000, end: 1_012.3)
        let operation = FakeAssetInstallOperation(
            source: FakeProgressSource(fractions: [0.25, 0.5, 0.75]),
            completion: .failure("asset download failed"),
            recorder: recorder,
            minimumProgressEventsBeforeFinishing: 2
        )
        let environment = FakeSpeechAssetEnvironment(statuses: ["installed"], operation: operation)

        do {
            _ = try await AssetInstallFlow.ensureReady(
                statusBefore: "supported",
                localeIdentifier: "zh_TW",
                environment: environment,
                emit: { recorder.record($0) },
                maximumProgressLines: 2,
                sampleInterval: { _ in await Task.yield() },
                now: { clock.now() }
            )
            XCTFail("expected an asset error")
        } catch let error as AppleSpeechError {
            XCTAssertEqual(error.code, .assetError)
            XCTAssertEqual(error.exitCode, 4)
            XCTAssertTrue(error.message.contains("asset download failed"), error.message)
        }

        XCTAssertEqual(recorder.events, [
            .started,
            .progress(fractionCompleted: 0.25),
            .progress(fractionCompleted: 0.5),
            .failed(seconds: 12.3, code: "APPLE_ASSET_ERROR", message: "asset download failed"),
        ])
        XCTAssertEqual(environment.calls.status, 0, "a failed install is not re-queried")
    }

    func testEnsureReadyTreatsADeferredInstallAsNotReady() async throws {
        let recorder = AssetEventRecorder()
        let operation = FakeAssetInstallOperation(
            source: FakeProgressSource(fractions: [0.5, 1.0]),
            completion: .success,
            recorder: recorder,
            minimumProgressEventsBeforeFinishing: 2
        )
        let environment = FakeSpeechAssetEnvironment(statuses: ["supported"], operation: operation)

        do {
            _ = try await AssetInstallFlow.ensureReady(
                statusBefore: "supported",
                localeIdentifier: "zh_TW",
                environment: environment,
                emit: { recorder.record($0) },
                maximumProgressLines: 2,
                sampleInterval: { _ in await Task.yield() },
                now: { 1_000 }
            )
            XCTFail("expected an asset error")
        } catch let error as AppleSpeechError {
            XCTAssertEqual(error.code, .assetError)
            XCTAssertEqual(error.exitCode, 4)
            XCTAssertTrue(error.message.contains("deferred install"), error.message)
        }

        XCTAssertEqual(environment.calls.status, 1)
        guard case .failed(let seconds, let code, let message)? = recorder.events.last else {
            return XCTFail("expected a failed progress line, got \(recorder.events)")
        }
        XCTAssertEqual(seconds, 0)
        XCTAssertEqual(code, "APPLE_ASSET_ERROR")
        XCTAssertTrue(message.contains("deferred install"), message)
    }

    func testEnsureReadyRefusesToReleaseAnotherLocaleReservation() async throws {
        let recorder = AssetEventRecorder()
        let environment = FakeSpeechAssetEnvironment(
            statuses: ["supported"],
            reservation: AssetReservationState(
                reservedLocaleCount: 5,
                maximumReservedLocaleCount: 5,
                localeAlreadyReserved: false
            )
        )

        do {
            _ = try await AssetInstallFlow.ensureReady(
                statusBefore: "supported",
                localeIdentifier: "zh_TW",
                environment: environment,
                emit: { recorder.record($0) }
            )
            XCTFail("expected an asset error")
        } catch let error as AppleSpeechError {
            XCTAssertEqual(error.code, .assetError)
            XCTAssertEqual(error.exitCode, 4)
            XCTAssertTrue(error.message.contains("reservations are exhausted"), error.message)
        }

        XCTAssertEqual(recorder.events, [
            .failed(
                seconds: nil,
                code: "APPLE_ASSET_ERROR",
                message: "speech asset reservations are exhausted (5/5) and 'zh_TW' is not reserved"
            ),
        ])
        XCTAssertEqual(environment.calls.request, 0, "exhaustion must not reach the framework request")
    }

    func testEnsureReadyReportsAFailedInstallationRequest() async throws {
        let recorder = AssetEventRecorder()
        let environment = FakeSpeechAssetEnvironment(
            statuses: ["supported"],
            requestError: FakeAssetError(message: "request unavailable")
        )

        do {
            _ = try await AssetInstallFlow.ensureReady(
                statusBefore: "supported",
                localeIdentifier: "zh_TW",
                environment: environment,
                emit: { recorder.record($0) },
                now: { 1_000 }
            )
            XCTFail("expected an asset error")
        } catch let error as AppleSpeechError {
            XCTAssertEqual(error.code, .assetError)
            XCTAssertTrue(error.message.contains("request unavailable"), error.message)
        }

        XCTAssertEqual(recorder.events.count, 2)
        XCTAssertEqual(recorder.events.first, .started)
        guard case .failed(_, let code, let message)? = recorder.events.last else {
            return XCTFail("expected a failed progress line, got \(recorder.events)")
        }
        XCTAssertEqual(code, "APPLE_ASSET_ERROR")
        XCTAssertEqual(message, "request unavailable")
    }

    func testEnsureReadyAcceptsANilRequestWhenTheAssetIsInstalled() async throws {
        let recorder = AssetEventRecorder()
        let clock = FakeClock(start: 10, end: 10.5)
        let environment = FakeSpeechAssetEnvironment(statuses: ["installed"], operation: nil)

        let result = try await AssetInstallFlow.ensureReady(
            statusBefore: "supported",
            localeIdentifier: "zh_TW",
            environment: environment,
            emit: { recorder.record($0) },
            now: { clock.now() }
        )

        XCTAssertEqual(recorder.events, [.started, .finished(seconds: 0.5)])
        XCTAssertFalse(result.attempted)
        XCTAssertTrue(result.installed)
        XCTAssertEqual(result.progressLines, 0)
    }

    func testEnsureReadyRejectsANilRequestWhenTheAssetIsStillMissing() async throws {
        let recorder = AssetEventRecorder()
        let environment = FakeSpeechAssetEnvironment(statuses: ["supported"], operation: nil)

        do {
            _ = try await AssetInstallFlow.ensureReady(
                statusBefore: "supported",
                localeIdentifier: "zh_TW",
                environment: environment,
                emit: { recorder.record($0) },
                now: { 1_000 }
            )
            XCTFail("expected an asset error")
        } catch let error as AppleSpeechError {
            XCTAssertEqual(error.code, .assetError)
            XCTAssertEqual(error.exitCode, 4)
            XCTAssertTrue(error.message.contains("no asset installation request was offered"), error.message)
        }

        XCTAssertEqual(recorder.events.count, 2)
        guard case .failed(_, let code, _)? = recorder.events.last else {
            return XCTFail("expected a failed progress line, got \(recorder.events)")
        }
        XCTAssertEqual(code, "APPLE_ASSET_ERROR")
    }

    // MARK: - Source-level invariants

    func testSourcesNeverReleaseOrReserveLocales() throws {
        for file in try PackageSources.swiftFiles() {
            XCTAssertFalse(
                file.contents.contains("AssetInventory.release("),
                "\(file.name) releases a locale reservation; DEC-06 forbids it"
            )
            XCTAssertFalse(
                file.contents.contains("release(reservedLocale"),
                "\(file.name) releases a locale reservation; DEC-06 forbids it"
            )
            XCTAssertFalse(
                file.contents.contains("AssetInventory.reserve("),
                "\(file.name) creates a locale reservation; only the system install may do that"
            )
        }
    }

    func testOnlyTheAssetInstallModuleTouchesTheInstallationRequest() throws {
        let owners = try PackageSources.swiftFiles()
            .filter { $0.contents.contains("assetInstallationRequest") }
            .map(\.name)
        XCTAssertEqual(owners, ["AssetInstall.swift"])
    }

    func testProbePathPerformsNoAssetInstallation() throws {
        let runner = try PackageSources.contents(of: "Sources/AppleSpeechKit/Runner.swift")
        XCTAssertTrue(runner.contains("runProbe"))
        XCTAssertFalse(runner.contains("AssetInstallFlow"))
        XCTAssertFalse(runner.contains("assetInstallationRequest"))

        let probePayload = try PackageSources.contents(of: "Sources/AppleSpeechKit/ProbePayload.swift")
        XCTAssertFalse(probePayload.contains("AssetInstallFlow"))
        XCTAssertFalse(probePayload.contains("assetInstallationRequest"))
        XCTAssertFalse(probePayload.contains("downloadAndInstall"))
    }

    func testDiagnosticsNeverLogTranscriptText() throws {
        for file in try PackageSources.swiftFiles() {
            XCTAssertFalse(file.contents.contains("text=<"), "\(file.name) logs transcript text")
            XCTAssertFalse(file.contents.contains("text=\\("), "\(file.name) logs transcript text")
        }
    }

    func testDiagnosticsBoundingKeepsShortMessagesIntact() {
        XCTAssertEqual(Diagnostics.bounded("short message"), "short message")
        let long = String(repeating: "y", count: Diagnostics.maximumMessageLength + 50)
        let bounded = Diagnostics.bounded(long)
        XCTAssertEqual(bounded.count, Diagnostics.maximumMessageLength + 1)
        XCTAssertTrue(bounded.hasSuffix("…"))
        XCTAssertEqual(
            Diagnostics.bounded("a\nb", limit: 10),
            "a\nb",
            "messages inside the limit survive byte for byte"
        )
        XCTAssertEqual(Diagnostics.bounded(String(repeating: "z", count: 20), limit: 5), "zzzzz…")
    }

    func testDiagnosticsProgressWritesOnePrefixedLineToTheSink() {
        let recorder = LineRecorder()
        let previous = Diagnostics.sink
        Diagnostics.sink = { recorder.record($0) }
        defer { Diagnostics.sink = previous }

        Diagnostics.progress(AssetProgressLine.encode(.started))
        Diagnostics.progress(AssetProgressLine.encode(.progress(fractionCompleted: 0.42)))

        XCTAssertEqual(recorder.lines, [
            "apple-speech-cli:progress {\"phase\":\"asset_install\",\"status\":\"started\"}",
            "apple-speech-cli:progress {\"phase\":\"asset_install\",\"status\":\"progress\",\"fractionCompleted\":0.42}",
        ])
    }

    func testDiagnosticsProgressNeverEmitsLineBreaks() {
        let recorder = LineRecorder()
        let previous = Diagnostics.sink
        Diagnostics.sink = { recorder.record($0) }
        defer { Diagnostics.sink = previous }

        Diagnostics.progress("apple-speech-cli:progress first\nsecond")

        XCTAssertEqual(recorder.lines, ["apple-speech-cli:progress first second"])
    }

    func testDiagnosticsLogBoundsEveryLine() {
        let recorder = LineRecorder()
        let previous = Diagnostics.sink
        Diagnostics.sink = { recorder.record($0) }
        defer { Diagnostics.sink = previous }

        Diagnostics.log(String(repeating: "q", count: Diagnostics.maximumMessageLength + 100))

        XCTAssertEqual(recorder.lines.count, 1)
        XCTAssertEqual(recorder.lines[0].count, Diagnostics.maximumMessageLength + 1)
    }

    // MARK: - Live seams (read-only: no install, no reservation, no network)

    func testProgressFractionSourceReadsFoundationProgress() {
        let progress = Progress(totalUnitCount: 8)
        let source = ProgressFractionSource(progress: progress)
        XCTAssertEqual(source.fractionCompleted(), 0)

        progress.completedUnitCount = 4
        XCTAssertEqual(source.fractionCompleted(), 0.5, accuracy: 0.0001)
    }

    @available(macOS 26.0, *)
    func testAssetProgressMonitorSamplesARealProgressObject() async {
        let progress = Progress(totalUnitCount: 10)
        let recorder = AssetEventRecorder()
        let monitor = AssetProgressMonitor(
            source: ProgressFractionSource(progress: progress),
            intervalSeconds: 0,
            maximumLines: 3,
            sampleInterval: { _ in
                progress.completedUnitCount += 5
                await Task.yield()
            },
            emit: { recorder.record($0) }
        )

        await monitor.start()
        var attempts = 0
        while recorder.emittedProgressEvents < 2, attempts < 20_000 {
            attempts += 1
            await Task.yield()
        }
        await monitor.stop()

        let emittedLines = await monitor.progressLines()
        XCTAssertEqual(recorder.events, [
            .progress(fractionCompleted: 0.5),
            .progress(fractionCompleted: 1.0),
        ])
        XCTAssertEqual(emittedLines, 2, "completion ends sampling early")
    }

    @available(macOS 26.0, *)
    func testLiveEnvironmentReportsKnownStatusNamesWithoutInstalling() async {
        // Read-only on purpose: `makeInstallationRequest()` is never called
        // here, because on a host without the asset it would start a real
        // download.
        let transcriber = SpeechTranscriber(
            locale: Locale(identifier: "zh_TW"),
            preset: .timeIndexedTranscriptionWithAlternatives
        )
        let environment = LiveSpeechAssetEnvironment(transcriber: transcriber)

        let status = await environment.statusName()
        XCTAssertTrue(
            ["unsupported", "supported", "downloading", "installed", "unknown"].contains(status),
            status
        )

        let reservation = await environment.reservationState(localeIdentifier: "zh_TW")
        XCTAssertGreaterThanOrEqual(reservation.maximumReservedLocaleCount, 0)
        XCTAssertGreaterThanOrEqual(reservation.reservedLocaleCount, 0)
    }
}

// MARK: - Test doubles

/// Captures everything written to the `Diagnostics` sink.
final class LineRecorder: @unchecked Sendable {
    private let lock = NSLock()
    private var storage: [String] = []

    func record(_ line: String) {
        lock.lock()
        defer { lock.unlock() }
        storage.append(line)
    }

    var lines: [String] {
        lock.lock()
        defer { lock.unlock() }
        return storage
    }
}

/// Records the progress events the flow emits.
final class AssetEventRecorder: @unchecked Sendable {    private let lock = NSLock()
    private var storage: [AssetProgressEvent] = []
    private var progressEvents = 0

    func record(_ event: AssetProgressEvent) {
        lock.lock()
        defer { lock.unlock() }
        storage.append(event)
        if case .progress = event { progressEvents += 1 }
    }

    var events: [AssetProgressEvent] {
        lock.lock()
        defer { lock.unlock() }
        return storage
    }

    var emittedProgressEvents: Int {
        lock.lock()
        defer { lock.unlock() }
        return progressEvents
    }
}

/// Deterministic, injected clock so install durations are exact under test.
final class FakeClock: @unchecked Sendable {
    private let lock = NSLock()
    private let start: Double
    private let end: Double
    private var reads = 0

    init(start: Double, end: Double) {
        self.start = start
        self.end = end
    }

    func now() -> Double {
        lock.lock()
        defer { lock.unlock() }
        reads += 1
        return reads == 1 ? start : end
    }
}

/// Deterministic `Foundation.Progress` stand-in.
final class FakeProgressSource: AssetProgressSource, @unchecked Sendable {
    private let lock = NSLock()
    private let fractions: [Double]
    private var index = 0

    init(fractions: [Double]) {
        self.fractions = fractions
    }

    func fractionCompleted() -> Double {
        lock.lock()
        defer { lock.unlock() }
        let value = index < fractions.count ? fractions[index] : (fractions.last ?? 0)
        index += 1
        return value
    }
}

struct FakeAssetError: Error, LocalizedError {
    let message: String
    var errorDescription: String? { message }
}

/// Install operation that completes only once the expected number of progress
/// lines has been emitted, so the emitted sequence is deterministic. The wait
/// is bounded so a broken test can never hang the suite.
final class FakeAssetInstallOperation: AssetInstallOperation, @unchecked Sendable {
    enum Completion {
        case success
        case failure(String)
    }

    private let source: FakeProgressSource
    private let completion: Completion
    private let recorder: AssetEventRecorder
    private let minimumProgressEventsBeforeFinishing: Int

    init(
        source: FakeProgressSource,
        completion: Completion,
        recorder: AssetEventRecorder,
        minimumProgressEventsBeforeFinishing: Int
    ) {
        self.source = source
        self.completion = completion
        self.recorder = recorder
        self.minimumProgressEventsBeforeFinishing = minimumProgressEventsBeforeFinishing
    }

    func progressSource() -> any AssetProgressSource { source }

    func downloadAndInstall() async throws {
        var attempts = 0
        while recorder.emittedProgressEvents < minimumProgressEventsBeforeFinishing, attempts < 2_000 {
            attempts += 1
            try? await Task.sleep(nanoseconds: 500_000)
        }
        switch completion {
        case .success:
            return
        case .failure(let message):
            throw FakeAssetError(message: message)
        }
    }
}

/// Asset environment fake. Every call is counted so a test can prove that a
/// code path never reached the framework.
final class FakeSpeechAssetEnvironment: SpeechAssetEnvironment, @unchecked Sendable {
    private let lock = NSLock()
    private var statuses: [String]
    private let reservation: AssetReservationState
    private let operation: (any AssetInstallOperation)?
    private let requestError: Error?
    private var statusCalls = 0
    private var requestCalls = 0
    private var reservationCalls = 0

    init(
        statuses: [String],
        reservation: AssetReservationState = AssetReservationState(
            reservedLocaleCount: 1,
            maximumReservedLocaleCount: 5,
            localeAlreadyReserved: true
        ),
        operation: (any AssetInstallOperation)? = nil,
        requestError: Error? = nil
    ) {
        self.statuses = statuses
        self.reservation = reservation
        self.operation = operation
        self.requestError = requestError
    }

    func statusName() async -> String {
        nextStatus()
    }

    func reservationState(localeIdentifier: String) async -> AssetReservationState {
        recordReservationQuery()
    }

    func makeInstallationRequest() async throws -> (any AssetInstallOperation)? {
        try nextInstallationRequest()
    }

    // `NSLock` is `noasync`, so the async entry points delegate to synchronous
    // accessors instead of locking directly inside an asynchronous context.
    private func nextStatus() -> String {
        lock.lock()
        defer { lock.unlock() }
        statusCalls += 1
        guard statuses.count > 1 else { return statuses.first ?? "unknown" }
        return statuses.removeFirst()
    }

    private func recordReservationQuery() -> AssetReservationState {
        lock.lock()
        defer { lock.unlock() }
        reservationCalls += 1
        return reservation
    }

    private func nextInstallationRequest() throws -> (any AssetInstallOperation)? {
        lock.lock()
        requestCalls += 1
        let error = requestError
        let request = operation
        lock.unlock()
        if let error { throw error }
        return request
    }

    var calls: (status: Int, request: Int, reservation: Int) {
        lock.lock()
        defer { lock.unlock() }
        return (statusCalls, requestCalls, reservationCalls)
    }
}

/// Reads the package sources so structural invariants can be asserted.
enum PackageSources {
    static var root: URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
    }

    static func swiftFiles() throws -> [(name: String, contents: String)] {
        let sources = root.appendingPathComponent("Sources")
        let enumerator = try XCTUnwrap(FileManager.default.enumerator(at: sources, includingPropertiesForKeys: nil))
        var files: [(name: String, contents: String)] = []
        for case let url as URL in enumerator where url.pathExtension == "swift" {
            files.append((name: url.lastPathComponent, contents: try String(contentsOf: url, encoding: .utf8)))
        }
        files.sort { $0.name < $1.name }
        return files
    }

    static func contents(of relativePath: String) throws -> String {
        try String(contentsOf: root.appendingPathComponent(relativePath), encoding: .utf8)
    }
}
