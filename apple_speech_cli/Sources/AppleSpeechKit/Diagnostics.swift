import Foundation

/// Diagnostics writer. Everything that is not the single stdout JSON document
/// goes through here, i.e. to stderr. Transcript text, decoded audio and raw
/// input bytes are never emitted, and every string is bounded.
public enum Diagnostics {
    nonisolated(unsafe) public static var debugEnabled = false

    /// Destination for diagnostics. Receives one line without a trailing
    /// newline so the writer stays unit-testable.
    nonisolated(unsafe) public static var sink: @Sendable (String) -> Void = Diagnostics.writeToStandardError

    /// Upper bound for a diagnostic line; keeps stderr readable and ensures a
    /// framework error can never flood the pipe.
    public static let maximumMessageLength = 400

    public static func log(_ message: String) {
        write(bounded(message))
    }

    public static func debug(_ message: String) {
        guard debugEnabled else { return }
        log("[debug] " + message)
    }

    /// Emits one already-encoded machine-parseable progress line. Line breaks
    /// are always collapsed so a reader can parse stderr line by line.
    public static func progress(_ line: String) {
        write(singleLineBounded(line, limit: AssetProgressLine.maximumLineLength))
    }

    /// Length-limited rendering used by every diagnostic path. Messages inside
    /// the limit are returned untouched, so existing diagnostics stay byte for
    /// byte identical.
    public static func bounded(_ text: String, limit: Int = Diagnostics.maximumMessageLength) -> String {
        guard text.count > limit else { return text }
        return String(singleLine(text).prefix(limit)) + "…"
    }

    public static func singleLine(_ text: String) -> String {
        text
            .replacingOccurrences(of: "\r", with: " ")
            .replacingOccurrences(of: "\n", with: " ")
    }

    private static func singleLineBounded(_ text: String, limit: Int) -> String {
        let line = singleLine(text)
        guard line.count > limit else { return line }
        return String(line.prefix(limit)) + "…"
    }

    private static func write(_ text: String) {
        sink(text)
    }

    private static func writeToStandardError(_ text: String) {
        FileHandle.standardError.write(Data((text + "\n").utf8))
    }
}

public enum StandardOutput {
    /// Writes exactly one JSON document plus a trailing newline to stdout.
    public static func write(_ value: JSONValue) {
        FileHandle.standardOutput.write(value.serializedData())
        FileHandle.standardOutput.write(Data("\n".utf8))
    }
}
