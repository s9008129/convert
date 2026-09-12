import Foundation

public struct TranscriptSegment: Sendable, Equatable {
    public let start: Double?
    public let end: Double?
    public let text: String

    public init(start: Double?, end: Double?, text: String) {
        self.start = start
        self.end = end
        self.text = text
    }
}

/// Builders for the two JSON documents this CLI can write to stdout.
/// `schema_version`/`engine` are the only fixed top-level identity keys.
public enum SchemaPayload {
    public static let schemaVersion = "1.0"
    public static let engine = "apple"

    public static func success(
        locale: String,
        text: String,
        segments: [TranscriptSegment],
        metadata: [(key: String, value: JSONValue)]
    ) -> JSONValue {
        let segmentValues = segments.map { segment in
            JSONValue.object([
                ("start", segment.start.map { JSONValue.number($0) } ?? .null),
                ("end", segment.end.map { JSONValue.number($0) } ?? .null),
                ("text", .string(segment.text)),
            ])
        }
        return .object([
            ("schema_version", .string(schemaVersion)),
            ("engine", .string(engine)),
            ("locale", .string(locale)),
            ("text", .string(text)),
            ("segments", .array(segmentValues)),
            ("metadata", .object(metadata)),
        ])
    }

    public static func failure(code: AppleSpeechErrorCode, message: String) -> JSONValue {
        .object([
            ("schema_version", .string(schemaVersion)),
            ("engine", .string(engine)),
            (
                "error",
                .object([
                    ("code", .string(code.rawValue)),
                    ("message", .string(message)),
                ])
            ),
        ])
    }

    /// Last-line-of-defence contract check performed before stdout is written.
    /// Returns `nil` when the document is schema `1.0` conformant.
    public static func successViolation(_ payload: JSONValue) -> String? {
        guard case .object(let pairs) = payload else { return "payload is not a JSON object" }
        let expected = ["schema_version", "engine", "locale", "text", "segments", "metadata"]
        let actual = pairs.map(\.key)
        if Set(actual) != Set(expected) || actual.count != expected.count {
            return "top-level keys \(actual) do not match \(expected)"
        }
        if let violation = payload.scalarObjectViolation(memberName: "metadata") {
            return violation
        }
        for pair in pairs where pair.key == "text" {
            guard case .string = pair.value else { return "'text' is not a string" }
        }
        for pair in pairs where pair.key == "segments" {
            guard case .array(let segments) = pair.value else { return "'segments' is not an array" }
            for (index, segment) in segments.enumerated() {
                guard case .object(let fields) = segment else { return "segment \(index) is not an object" }
                let keys = fields.map(\.key)
                if Set(keys) != Set(["start", "end", "text"]) {
                    return "segment \(index) keys \(keys) are not ['start','end','text']"
                }
                for field in fields where field.key != "text" && !field.value.isScalar {
                    return "segment \(index) field '\(field.key)' is not a scalar"
                }
            }
        }
        return nil
    }
}
