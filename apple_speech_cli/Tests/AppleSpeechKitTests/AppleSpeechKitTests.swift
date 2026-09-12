import CoreMedia
import Foundation
import Speech
import XCTest

@testable import AppleSpeechKit

/// Deterministic tests only: no Speech asset, no network, no audio.
/// Runtime/asset behaviour is evidenced by the WAVE-1 spike commands instead.
final class AppleSpeechKitTests: XCTestCase {

    // MARK: - Schema 1.0

    private func sampleSuccessPayload(extraTopLevelKey: Bool = false) -> JSONValue {
        var metadata: [(key: String, value: JSONValue)] = [
            ("helper_version", .string("0.1.0")),
            ("segments_supported", .bool(true)),
            ("ratio", .number(0.25)),
            ("count", .integer(3)),
            ("optional", .null),
        ]
        if extraTopLevelKey {
            metadata.append(("nested", .array([.string("not-allowed")])))
        }
        return SchemaPayload.success(
            locale: "zh_TW",
            text: "今天天氣很好。",
            segments: [
                TranscriptSegment(start: 0.0, end: 1.2, text: "今天天氣很好"),
                TranscriptSegment(start: nil, end: nil, text: "。"),
            ],
            metadata: metadata
        )
    }

    func testSuccessPayloadIsSchemaCompliant() {
        let payload = sampleSuccessPayload()
        XCTAssertNil(SchemaPayload.successViolation(payload))

        guard case .object(let pairs) = payload else { return XCTFail("not an object") }
        XCTAssertEqual(
            pairs.map(\.key),
            ["schema_version", "engine", "locale", "text", "segments", "metadata"]
        )
    }

    func testSuccessPayloadScalarOnlyMetadataIsEnforced() {
        let payload = sampleSuccessPayload(extraTopLevelKey: true)
        let violation = SchemaPayload.successViolation(payload)
        XCTAssertEqual(violation, "member 'metadata.nested' is not a JSON scalar")
    }

    func testSuccessPayloadSerializesToSingleParseableDocument() throws {
        let data = sampleSuccessPayload().serializedData()
        let parsed = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        XCTAssertEqual(parsed?["schema_version"] as? String, "1.0")
        XCTAssertEqual(parsed?["engine"] as? String, "apple")
        XCTAssertEqual(parsed?["text"] as? String, "今天天氣很好。")
        let segments = try XCTUnwrap(parsed?["segments"] as? [[String: Any]])
        XCTAssertEqual(segments.count, 2)
        XCTAssertEqual(segments[0]["start"] as? Double, 0.0)
        XCTAssertEqual(segments[0]["end"] as? Double, 1.2)
        XCTAssertTrue(segments[1]["start"] is NSNull)
        XCTAssertTrue(segments[1]["end"] is NSNull)
        // CJK must survive unescaped so evidence stays readable.
        let raw = String(decoding: data, as: UTF8.self)
        XCTAssertTrue(raw.contains("今天天氣很好"))
        XCTAssertFalse(raw.contains("\\u4"))
    }

    func testFailurePayloadShape() throws {
        let payload = SchemaPayload.failure(code: .localeUnsupported, message: "no locale")
        guard case .object(let pairs) = payload else { return XCTFail("not an object") }
        XCTAssertEqual(pairs.map(\.key), ["schema_version", "engine", "error"])
        let jsonObject = try JSONSerialization.jsonObject(with: payload.serializedData())
        let parsed = try XCTUnwrap(jsonObject as? [String: Any])
        let error = try XCTUnwrap(parsed["error"] as? [String: Any])
        XCTAssertEqual(error["code"] as? String, "APPLE_LOCALE_UNSUPPORTED")
        XCTAssertEqual(error["message"] as? String, "no locale")
    }

    // MARK: - Exit code contract

    func testExitCodeMappingMatchesContract() {
        XCTAssertEqual(AppleSpeechErrorCode.unavailable.exitCode, 2)
        XCTAssertEqual(AppleSpeechErrorCode.localeUnsupported.exitCode, 3)
        XCTAssertEqual(AppleSpeechErrorCode.assetError.exitCode, 4)
        XCTAssertEqual(AppleSpeechErrorCode.inputError.exitCode, 5)
        XCTAssertEqual(AppleSpeechErrorCode.transcriptionError.exitCode, 6)
        XCTAssertEqual(AppleSpeechErrorCode.cancelled.exitCode, 7)
        XCTAssertEqual(AppleSpeechErrorCode.timeout.exitCode, 1)
        XCTAssertEqual(AppleSpeechErrorCode.outputInvalid.exitCode, 1)
        XCTAssertEqual(AppleSpeechError(code: .cancelled, message: "x").exitCode, 7)
    }

    func testErrorCodeRawValuesAreStable() {
        XCTAssertEqual(
            AppleSpeechErrorCode.allCases.map(\.rawValue),
            [
                "APPLE_UNAVAILABLE",
                "APPLE_LOCALE_UNSUPPORTED",
                "APPLE_ASSET_ERROR",
                "APPLE_INPUT_ERROR",
                "APPLE_TRANSCRIPTION_ERROR",
                "APPLE_TIMEOUT",
                "APPLE_CANCELLED",
                "APPLE_OUTPUT_INVALID",
            ]
        )
    }

    // MARK: - Locale helpers

    func testLocaleEquivalence() {
        XCTAssertTrue(LocaleEquivalence.isEquivalent("zh_TW", "zh-TW"))
        XCTAssertTrue(LocaleEquivalence.isEquivalent("zh-Hant-TW", "zh-TW"))
        XCTAssertTrue(LocaleEquivalence.isEquivalent("ZH-tw", "zh-TW"))
        XCTAssertFalse(LocaleEquivalence.isEquivalent("zh-TW", "zh-CN"))
        XCTAssertFalse(LocaleEquivalence.isEquivalent("en-US", "zh-TW"))
    }

    func testCanonicalLocaleIdentifier() {
        XCTAssertEqual(LocaleEquivalence.canonicalIdentifier("zh_TW"), "zh-TW")
        XCTAssertEqual(LocaleEquivalence.canonicalIdentifier("zh-hant-tw"), "zh-Hant-TW")
        XCTAssertEqual(LocaleEquivalence.canonicalIdentifier("en_US.UTF-8"), "en-US")
    }

    // MARK: - Time mapping

    func testTimeMappingConvertsToMillisecondSeconds() {
        // 1.2345 s at timescale 10000 is exact, so the millisecond rounding is
        // the only transformation under test.
        let range = CMTimeRange(
            start: CMTime(seconds: 1.2345, preferredTimescale: 10000),
            duration: CMTime(seconds: 2.25, preferredTimescale: 10000)
        )
        let bounds = TimeMapping.bounds(range)
        XCTAssertEqual(bounds.start, 1.235)
        XCTAssertEqual(bounds.end, 3.485)

        let invalid = CMTimeRange(start: .invalid, duration: .invalid)
        let invalidBounds = TimeMapping.bounds(invalid)
        XCTAssertNil(invalidBounds.start)
        XCTAssertNil(invalidBounds.end)
    }

    // MARK: - JSON primitives

    func testJSONScalarFormatting() {
        XCTAssertEqual(JSONValue.integer(3).serialized(), "3")
        XCTAssertEqual(JSONValue.number(0).serialized(), "0.0")
        XCTAssertEqual(JSONValue.number(6.116).serialized(), "6.116")
        XCTAssertEqual(JSONValue.number(.nan).serialized(), "null")
        XCTAssertEqual(JSONValue.number(.infinity).serialized(), "null")
        XCTAssertEqual(JSONValue.bool(true).serialized(), "true")
        XCTAssertEqual(JSONValue.null.serialized(), "null")
    }

    func testJSONStringEscaping() {
        XCTAssertEqual(JSONValue.string("a\"b\\c\nd\te").serialized(), "\"a\\\"b\\\\c\\nd\\te\"")
        XCTAssertEqual(JSONValue.string("\u{01}").serialized(), "\"\\u0001\"")
    }

    func testArrayAndObjectSerializationIsOrdered() {
        let value = JSONValue.object([
            ("b", .integer(1)),
            ("a", .array([.string("x"), .null])),
        ])
        XCTAssertEqual(value.serialized(), "{\"b\":1,\"a\":[\"x\",null]}")
    }

    // MARK: - CLI parsing

    func testParseProbeDefaults() throws {
        let options = try CLIArgumentParser.parse(["probe", "--locale", "zh-TW", "--output-format", "json"])
        XCTAssertEqual(options.command, .probe)
        XCTAssertEqual(options.locale, "zh-TW")
        XCTAssertEqual(options.outputFormat, "json")
        XCTAssertNil(options.input)
        XCTAssertEqual(options.timeoutSeconds, 0)
        XCTAssertFalse(options.debug)
    }

    func testParseTranscribe() throws {
        let options = try CLIArgumentParser.parse([
            "transcribe", "--input", "fixtures/x.m4a", "-l", "zh-TW", "--timeout", "12.5", "--debug",
        ])
        XCTAssertEqual(options.command, .transcribe)
        XCTAssertEqual(options.input, "fixtures/x.m4a")
        XCTAssertEqual(options.timeoutSeconds, 12.5)
        XCTAssertTrue(options.debug)
        XCTAssertEqual(options.segmentSource, "result")
        XCTAssertEqual(options.preset, "time-indexed")
    }

    func testParseRejectsInvalidArguments() {
        XCTAssertThrowsError(try CLIArgumentParser.parse([]))
        XCTAssertThrowsError(try CLIArgumentParser.parse(["bogus"]))
        XCTAssertThrowsError(try CLIArgumentParser.parse(["transcribe"]))
        XCTAssertThrowsError(try CLIArgumentParser.parse(["transcribe", "--input"]))
        XCTAssertThrowsError(try CLIArgumentParser.parse(["probe", "--bogus"]))
        XCTAssertThrowsError(try CLIArgumentParser.parse(["probe", "--output-format", "text"]))
        XCTAssertThrowsError(try CLIArgumentParser.parse(["probe", "--timeout", "-1"]))
        XCTAssertThrowsError(try CLIArgumentParser.parse(["probe", "--timeout", "abc"]))
        XCTAssertThrowsError(try CLIArgumentParser.parse(["probe", "--preset", "nope"]))
        XCTAssertThrowsError(try CLIArgumentParser.parse(["probe", "--segment-source", "nope"]))
    }

    func testParseErrorsAreInputErrors() {
        do {
            _ = try CLIArgumentParser.parse(["bogus"])
            XCTFail("expected throw")
        } catch let error as AppleSpeechError {
            XCTAssertEqual(error.code, .inputError)
            XCTAssertEqual(error.exitCode, 5)
        } catch {
            XCTFail("unexpected error type \(error)")
        }
    }

    @available(macOS 26.0, *)
    func testPresetAndSegmentSourceSelection() {
        XCTAssertEqual(
            SpeechRuntime.preset(named: "plain").reportingOptions,
            SpeechTranscriber.Preset.transcription.reportingOptions
        )
        XCTAssertEqual(
            SpeechRuntime.preset(named: "time-indexed").reportingOptions,
            SpeechTranscriber.Preset.timeIndexedTranscriptionWithAlternatives.reportingOptions
        )
        XCTAssertEqual(
            SpeechRuntime.preset(named: "unknown-value").reportingOptions,
            SpeechTranscriber.Preset.timeIndexedTranscriptionWithAlternatives.reportingOptions
        )
    }

    // MARK: - Output guard

    func testOutputGuardAllowsExactlyOneWrite() {
        let recorder = WriteRecorder()
        let guardInstance = OutputGuard { recorder.record($0) }
        XCTAssertTrue(guardInstance.writeOnce(.object([("a", .integer(1))])))
        XCTAssertFalse(guardInstance.writeOnce(.object([("a", .integer(2))])))
        XCTAssertTrue(guardInstance.hasWritten)
        XCTAssertEqual(recorder.writes, ["{\"a\":1}"])
    }

    func testHostMetadataIsScalarOnly() {
        let metadata = MetadataBuilder.host()
        XCTAssertFalse(metadata.isEmpty)
        for entry in metadata {
            XCTAssertTrue(entry.value.isScalar, "metadata key \(entry.key) is not a scalar")
        }
        XCTAssertTrue(metadata.contains { $0.key == "os_version" })
        XCTAssertTrue(metadata.contains { $0.key == "api_available" })
    }
}

/// Records everything an `OutputGuard` would have written to stdout.
final class WriteRecorder: @unchecked Sendable {
    private let lock = NSLock()
    private var storage: [String] = []

    func record(_ value: JSONValue) {
        lock.lock()
        defer { lock.unlock() }
        storage.append(value.serialized())
    }

    var writes: [String] {
        lock.lock()
        defer { lock.unlock() }
        return storage
    }
}
