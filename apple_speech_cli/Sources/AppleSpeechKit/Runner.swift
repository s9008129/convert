import Foundation

/// Command dispatch shared by the executable and the deterministic tests.
public enum Runner {
    public static func run(
        arguments: [String],
        control: AnalysisControl,
        outputGuard: OutputGuard,
        watchdog: Watchdog
    ) async -> Int32 {
        do {
            let options = try CLIArgumentParser.parse(arguments)
            Diagnostics.debugEnabled = options.debug
            Diagnostics.log("apple-speech-cli \(HostInfo.helperVersion) \(options.command)")
            switch options.command {
            case .probe:
                return try await runProbe(options: options, outputGuard: outputGuard)
            case .transcribe:
                return try await runTranscribe(
                    options: options,
                    control: control,
                    outputGuard: outputGuard,
                    watchdog: watchdog
                )
            }
        } catch let error as AppleSpeechError {
            Diagnostics.log("error: \(error)")
            if !outputGuard.writeOnce(SchemaPayload.failure(code: error.code, message: error.message)) {
                Diagnostics.log("stdout already written; suppressed duplicate error document")
            }
            return error.exitCode
        } catch {
            let wrapped = AppleSpeechError(code: .transcriptionError, message: "\(error)")
            Diagnostics.log("error: \(wrapped)")
            if !outputGuard.writeOnce(SchemaPayload.failure(code: wrapped.code, message: wrapped.message)) {
                Diagnostics.log("stdout already written; suppressed duplicate error document")
            }
            return wrapped.exitCode
        }
    }

    static func runProbe(options: CLIOptions, outputGuard: OutputGuard) async throws -> Int32 {
        let metadata = MetadataBuilder.host()
        do {
            let report = try await SpeechRuntime.localeReport(for: options.locale)
            let failure = report.isSupported
                ? nil
                : AppleSpeechError(
                    code: .localeUnsupported,
                    message: "no SpeechTranscriber locale equivalent to '\(options.locale)'"
                )
            _ = outputGuard.writeOnce(
                ProbePayload.build(report: report, failure: failure, metadata: metadata)
            )
            if let failure {
                Diagnostics.log("probe failed: \(failure)")
                return failure.exitCode
            }
            Diagnostics.log("probe ok: asset_status=\(report.assetStatus) resolved=\(report.resolvedIdentifier ?? "nil")")
            return 0
        } catch let error as AppleSpeechError {
            _ = outputGuard.writeOnce(ProbePayload.build(report: nil, failure: error, metadata: metadata))
            Diagnostics.log("probe unavailable: \(error)")
            return error.exitCode
        }
    }

    static func runTranscribe(
        options: CLIOptions,
        control: AnalysisControl,
        outputGuard: OutputGuard,
        watchdog: Watchdog
    ) async throws -> Int32 {
        let inputURL = URL(fileURLWithPath: options.input ?? "")
        let attributes = try? FileManager.default.attributesOfItem(atPath: inputURL.path)
        let inputBytes = (attributes?[.size] as? NSNumber)?.intValue
        if options.timeoutSeconds > 0 {
            watchdog.arm(
                seconds: options.timeoutSeconds,
                code: .timeout,
                message: "analysis exceeded \(options.timeoutSeconds)s budget",
                exitCode: AppleSpeechErrorCode.timeout.exitCode,
                outputGuard: outputGuard
            )
        }
        let outcome: TranscriptionOutcome
        do {
            outcome = try await TranscriptionService.transcribe(
                options: options,
                input: inputURL,
                control: control
            )
        } catch {
            watchdog.disarm()
            throw error
        }
        watchdog.disarm()

        let metadata = MetadataBuilder.transcribe(
            options: options,
            outcome: outcome,
            input: inputURL,
            inputBytes: inputBytes ?? 0
        )
        let payload = SchemaPayload.success(
            locale: outcome.localeResolved ?? options.locale,
            text: outcome.text,
            segments: outcome.segments,
            metadata: metadata
        )
        if let violation = SchemaPayload.successViolation(payload) {
            throw AppleSpeechError(code: .outputInvalid, message: violation)
        }
        guard outputGuard.writeOnce(payload) else {
            Diagnostics.log("stdout already written; suppressed duplicate success document")
            return AppleSpeechErrorCode.outputInvalid.exitCode
        }
        Diagnostics.log(
            "transcribe ok: \(outcome.text.count) chars, \(outcome.segments.count) segments, \(outcome.finalResults) final results"
        )
        return 0
    }
}
