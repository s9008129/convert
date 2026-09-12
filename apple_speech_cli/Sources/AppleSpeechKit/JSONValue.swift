import Foundation

/// Minimal JSON value model with deterministic key ordering and explicit
/// scalar typing. `metadata` objects are required to hold scalars only, so the
/// model makes non-scalar metadata impossible to express accidentally.
public enum JSONValue: Sendable, Equatable {
    case string(String)
    case number(Double)
    case integer(Int)
    case bool(Bool)
    case null
    case array([JSONValue])
    case object([(key: String, value: JSONValue)])

    public var isScalar: Bool {
        switch self {
        case .string, .number, .integer, .bool, .null: return true
        case .array, .object: return false
        }
    }

    /// Structural equality; object member order is part of the value because
    /// the serializer preserves it.
    public static func == (lhs: JSONValue, rhs: JSONValue) -> Bool {
        lhs.serialized() == rhs.serialized()
    }

    public func serialized() -> String {
        switch self {
        case .string(let value):
            return JSONValue.quote(value)
        case .number(let value):
            guard value.isFinite else { return "null" }
            return JSONValue.format(value)
        case .integer(let value):
            return String(value)
        case .bool(let value):
            return value ? "true" : "false"
        case .null:
            return "null"
        case .array(let values):
            return "[" + values.map { $0.serialized() }.joined(separator: ",") + "]"
        case .object(let pairs):
            let body = pairs.map { JSONValue.quote($0.key) + ":" + $0.value.serialized() }
            return "{" + body.joined(separator: ",") + "}"
        }
    }

    public func serializedData() -> Data {
        Data(serialized().utf8)
    }

    /// Validates that `memberName` exists on this object and that every one of
    /// its members is a JSON scalar (no nested objects or arrays).
    public func scalarObjectViolation(memberName: String) -> String? {
        guard case .object(let pairs) = self else { return "payload is not a JSON object" }
        guard let member = pairs.first(where: { $0.key == memberName }) else {
            return "missing member '\(memberName)'"
        }
        guard case .object(let inner) = member.value else {
            return "member '\(memberName)' is not a JSON object"
        }
        for pair in inner where !pair.value.isScalar {
            return "member '\(memberName).\(pair.key)' is not a JSON scalar"
        }
        return nil
    }

    static func format(_ value: Double) -> String {
        if value == value.rounded(), abs(value) < 1e15 {
            return String(format: "%.1f", locale: nil, value)
        }
        var text = String(format: "%.6f", locale: nil, value)
        while text.hasSuffix("0") { text.removeLast() }
        if text.hasSuffix(".") { text += "0" }
        return text
    }

    static func quote(_ value: String) -> String {
        var out = "\""
        for scalar in value.unicodeScalars {
            switch scalar {
            case "\"": out += "\\\""
            case "\\": out += "\\\\"
            case "\n": out += "\\n"
            case "\r": out += "\\r"
            case "\t": out += "\\t"
            default:
                if scalar.value < 0x20 {
                    out += String(format: "\\u%04x", scalar.value)
                } else {
                    out.unicodeScalars.append(scalar)
                }
            }
        }
        out += "\""
        return out
    }
}
