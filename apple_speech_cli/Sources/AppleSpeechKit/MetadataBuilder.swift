import Foundation

/// Collects the scalar-only metadata block attached to both JSON documents.
public enum MetadataBuilder {
    public static func host() -> [(key: String, value: JSONValue)] {
        [
            ("helper_version", .string(HostInfo.helperVersion)),
            ("api", .string("SpeechAnalyzer/SpeechTranscriber")),
            ("api_minimum_required", .string("macOS \(SpeechRuntime.minimumMacOSMajorVersion).0")),
            ("framework", .string("Speech")),
            ("api_available", .bool(SpeechRuntime.isAPIAvailable)),
            ("platform", .string("macOS")),
            ("os_version", .string(HostInfo.operatingSystemVersion)),
            ("os_build", .string(HostInfo.operatingSystemBuild)),
            ("arch", .string(HostInfo.architecture)),
            ("is_apple_silicon", .bool(HostInfo.isAppleSilicon)),
            ("hardware_model", .string(HostInfo.sysctlString("hw.model") ?? "")),
            ("hardware_chip", .string(HostInfo.sysctlString("machdep.cpu.brand_string") ?? "")),
            ("cpu_count", .integer(ProcessInfo.processInfo.processorCount)),
            ("memory_bytes", .integer(Int(ProcessInfo.processInfo.physicalMemory))),
        ]
    }

    public static func transcribe(
        options: CLIOptions,
        outcome: TranscriptionOutcome,
        input: URL,
        inputBytes: Int
    ) -> [(key: String, value: JSONValue)] {
        var pairs = host()
        pairs.append(("locale_requested", .string(options.locale)))
        pairs.append(("locale_canonical_requested", .string(LocaleEquivalence.canonicalIdentifier(options.locale))))
        pairs.append(("locale_resolved", outcome.localeResolved.map { JSONValue.string($0) } ?? .null))
        pairs.append(("asset_status_before", .string(outcome.assetStatusBefore)))
        pairs.append(("asset_status_after", .string(outcome.assetStatusAfter)))
        pairs.append(("asset_install_attempted", .bool(outcome.assetInstall.attempted)))
        pairs.append(("asset_install_seconds", outcome.assetInstall.seconds.map { JSONValue.number(round($0, 3)) } ?? .null))
        pairs.append(("asset_install_error", outcome.assetInstall.errorMessage.map { JSONValue.string($0) } ?? .null))
        pairs.append(("preset", .string(outcome.preset)))
        pairs.append(("segment_source", .string(outcome.segmentSource)))
        pairs.append(("input_basename", .string(input.lastPathComponent)))
        pairs.append(("input_extension", .string(input.pathExtension.lowercased())))
        pairs.append(("input_bytes", .integer(inputBytes)))
        pairs.append(("timeout_seconds", .number(options.timeoutSeconds)))
        pairs.append(("audio_sample_rate", .number(outcome.audioSampleRate)))
        pairs.append(("audio_channels", .integer(outcome.audioChannels)))
        pairs.append(("audio_frames", .integer(Int(outcome.audioFrames))))
        pairs.append(("audio_duration_seconds", outcome.audioDurationSeconds.map { JSONValue.number(round($0, 3)) } ?? .null))
        pairs.append(("results_total", .integer(outcome.totalResults)))
        pairs.append(("results_final", .integer(outcome.finalResults)))
        pairs.append(("results_volatile", .integer(outcome.volatileResults)))
        pairs.append(("segment_count", .integer(outcome.segments.count)))
        pairs.append(("text_characters", .integer(outcome.text.count)))
        pairs.append(("analysis_seconds", .number(round(outcome.analysisSeconds, 3))))
        pairs.append(("elapsed_seconds", .number(round(outcome.elapsedSeconds, 3))))
        let rtf = outcome.audioDurationSeconds.flatMap { $0 > 0 ? outcome.analysisSeconds / $0 : nil }
        pairs.append(("real_time_factor", rtf.map { JSONValue.number(round($0, 3)) } ?? .null))
        pairs.append(("first_segment_start_seconds", outcome.segments.first.flatMap { $0.start }.map { JSONValue.number($0) } ?? .null))
        pairs.append(("last_segment_end_seconds", outcome.segments.last.flatMap { $0.end }.map { JSONValue.number($0) } ?? .null))
        return pairs
    }

    public static func round(_ value: Double, _ places: Int) -> Double {
        let factor = pow(10.0, Double(places))
        return (value * factor).rounded() / factor
    }
}
