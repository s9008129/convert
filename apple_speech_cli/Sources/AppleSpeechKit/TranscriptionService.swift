import AVFAudio
import CoreMedia
import Foundation
import Speech

/// Holds the live analysis cancellation hook so that a signal handler can stop
/// analysis from outside the analysis task. It stays available on every
/// deployment target by holding a closure instead of the macOS 26 analyzer.
public actor AnalysisControl {
    private var cancelHandler: (@Sendable () async -> Void)?
    private var cancelled = false

    public init() {}

    public func attach(cancel: @escaping @Sendable () async -> Void) {
        cancelHandler = cancel
    }

    public func markCancelled() { cancelled = true }
    public func isCancelled() -> Bool { cancelled }

    public func cancelNow() async {
        cancelled = true
        if let cancelHandler {
            await cancelHandler()
        }
    }
}

public enum TranscriptionService {
    public static func transcribe(
        options: CLIOptions,
        input: URL,
        control: AnalysisControl
    ) async throws -> TranscriptionOutcome {
        guard HostInfo.isAppleSilicon else {
            throw AppleSpeechError(
                code: .unavailable,
                message: "Apple SpeechAnalyzer provider requires Apple Silicon; host architecture is \(HostInfo.architecture)"
            )
        }
        guard #available(macOS 26.0, *) else {
            throw AppleSpeechError(
                code: .unavailable,
                message: "SpeechAnalyzer requires macOS \(SpeechRuntime.minimumMacOSMajorVersion) or newer; host is \(HostInfo.operatingSystemVersion)"
            )
        }
        return try await run(options: options, input: input, control: control)
    }

    @available(macOS 26.0, *)
    private static func run(
        options: CLIOptions,
        input: URL,
        control: AnalysisControl
    ) async throws -> TranscriptionOutcome {
        let started = Date()
        let fileManager = FileManager.default
        var isDirectory: ObjCBool = false
        guard fileManager.fileExists(atPath: input.path, isDirectory: &isDirectory), !isDirectory.boolValue else {
            throw AppleSpeechError(code: .inputError, message: "input file does not exist: \(input.path)")
        }

        let report = try await SpeechRuntime.localeReport(for: options.locale)
        guard report.isSupported, let resolvedIdentifier = report.resolvedIdentifier else {
            throw AppleSpeechError(
                code: .localeUnsupported,
                message: "no SpeechTranscriber locale equivalent to '\(options.locale)' (supported: \(report.supportedLocalesCount))"
            )
        }
        let resolvedLocale = Locale(identifier: resolvedIdentifier)
        Diagnostics.log("resolved locale '\(options.locale)' -> '\(resolvedIdentifier)'")
        Diagnostics.log(
            "asset status before: \(report.assetStatus); installed locales: \(report.installedLocales)"
        )

        let transcriber = SpeechTranscriber(
            locale: resolvedLocale,
            preset: SpeechRuntime.preset(named: options.preset)
        )
        if options.debug {
            let preset = SpeechRuntime.preset(named: options.preset)
            Diagnostics.debug("preset transcriptionOptions=\(preset.transcriptionOptions) reportingOptions=\(preset.reportingOptions) attributeOptions=\(preset.attributeOptions)")
            let formats = await transcriber.availableCompatibleAudioFormats
            for format in formats {
                Diagnostics.debug("compatible audio format: \(format.sampleRate) Hz \(format.channelCount) ch")
            }
        }
        let analyzer = SpeechAnalyzer(modules: [transcriber])
        await control.attach { await analyzer.cancelAndFinishNow() }

        let environment = LiveSpeechAssetEnvironment(transcriber: transcriber)
        let readiness = try await AssetInstallFlow.ensureReady(
            statusBefore: report.assetStatus,
            localeIdentifier: resolvedIdentifier,
            environment: environment,
            emit: { Diagnostics.progress(AssetProgressLine.encode($0)) }
        )
        let assetStatusAfter = readiness.statusAfter
        let installReport = AssetInstallReport(
            attempted: readiness.attempted,
            installed: readiness.installed,
            seconds: readiness.seconds,
            errorMessage: readiness.errorMessage
        )
        Diagnostics.log("asset status after: \(assetStatusAfter)")

        let audioFile: AVAudioFile
        do {
            audioFile = try AVAudioFile(forReading: input)
        } catch {
            throw AppleSpeechError(
                code: .inputError,
                message: "AVAudioFile cannot read '\(input.lastPathComponent)': \(error.localizedDescription)"
            )
        }
        let audioDuration = audioFile.fileFormat.sampleRate > 0
            ? Double(audioFile.length) / audioFile.fileFormat.sampleRate
            : nil
        Diagnostics.log(
            "audio: \(audioFile.fileFormat.sampleRate) Hz, \(audioFile.fileFormat.channelCount) ch, \(audioFile.length) frames, duration=\(audioDuration.map { String($0) } ?? "unknown")s"
        )

        let collector = TranscriptionCollector()
        let splitRuns = !options.disableRunSplit
        let debugResults = options.debug
        let resultsTask = Task<Error?, Never> {
            do {
                for try await result in transcriber.results {
                    let textCharacters = String(result.text.characters).count
                    if debugResults {
                        let bounds = TimeMapping.bounds(result.range)
                        let runsWithRange = result.text.runs.filter {
                            $0[AttributeScopes.SpeechAttributes.TimeRangeAttribute.self] != nil
                        }.count
                        let confidenceRuns = result.text.runs.filter {
                            $0[AttributeScopes.SpeechAttributes.ConfidenceAttribute.self] != nil
                        }.count
                        var distinctRangeKeys = Set<String>()
                        for run in result.text.runs {
                            guard let runRange = run[AttributeScopes.SpeechAttributes.TimeRangeAttribute.self] else { continue }
                            distinctRangeKeys.insert("\(runRange.start.seconds)+\(runRange.duration.seconds)")
                        }
                        Diagnostics.debug(
                            "result isFinal=\(result.isFinal) range=\(bounds.start.map { String($0) } ?? "nil")..\(bounds.end.map { String($0) } ?? "nil") finalizationTime=\(result.resultsFinalizationTime.seconds) runs=\(result.text.runs.count) runsWithTimeRange=\(runsWithRange) runsWithConfidence=\(confidenceRuns) distinctRunRanges=\(distinctRangeKeys.count) alternatives=\(result.alternatives.count) text_chars=\(textCharacters)"
                        )
                    }
                    await collector.record(
                        text: result.text,
                        range: result.range,
                        isFinal: result.isFinal,
                        splitRuns: splitRuns
                    )
                }
                return nil
            } catch {
                return error
            }
        }

        let analysisStarted = Date()
        do {
            try await analyzer.start(inputAudioFile: audioFile, finishAfterFile: false)
            try await analyzer.finalizeAndFinishThroughEndOfInput()
        } catch {
            resultsTask.cancel()
            if await control.isCancelled() {
                throw AppleSpeechError(code: .cancelled, message: "analysis cancelled (cancelAndFinishNow)")
            }
            throw AppleSpeechError(
                code: .transcriptionError,
                message: "analysis failed: \(error.localizedDescription)"
            )
        }
        let resultsError = await resultsTask.value
        if let resultsError {
            throw AppleSpeechError(
                code: .transcriptionError,
                message: "result stream failed: \(resultsError.localizedDescription)"
            )
        }
        if await control.isCancelled() {
            throw AppleSpeechError(code: .cancelled, message: "analysis cancelled")
        }
        let analysisSeconds = Date().timeIntervalSince(analysisStarted)

        let snapshot = await collector.snapshot()
        let text = snapshot.text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else {
            throw AppleSpeechError(
                code: .transcriptionError,
                message: "provider produced empty text for '\(input.lastPathComponent)'"
            )
        }

        return TranscriptionOutcome(
            text: text,
            segments: snapshot.segments,
            totalResults: snapshot.total,
            finalResults: snapshot.final,
            volatileResults: snapshot.volatile,
            audioDurationSeconds: audioDuration,
            audioSampleRate: audioFile.fileFormat.sampleRate,
            audioChannels: Int(audioFile.fileFormat.channelCount),
            audioFrames: audioFile.length,
            preset: options.preset,
            segmentSource: options.segmentSource,
            localeResolved: resolvedIdentifier,
            assetStatusBefore: report.assetStatus,
            assetStatusAfter: assetStatusAfter,
            assetInstall: installReport,
            analysisSeconds: analysisSeconds,
            elapsedSeconds: Date().timeIntervalSince(started)
        )
    }
}
