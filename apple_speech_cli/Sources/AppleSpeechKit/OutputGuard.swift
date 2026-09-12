import Foundation

/// Guarantees that stdout receives at most one JSON document even when the
/// timeout watchdog and the normal completion path race each other.
public final class OutputGuard: @unchecked Sendable {
    private let lock = NSLock()
    private var written = false
    private let writer: @Sendable (JSONValue) -> Void

    public init(writer: @escaping @Sendable (JSONValue) -> Void = StandardOutput.write) {
        self.writer = writer
    }

    /// Returns `true` when this call performed the single allowed write.
    public func writeOnce(_ value: JSONValue) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        guard !written else { return false }
        written = true
        writer(value)
        return true
    }

    public var hasWritten: Bool {
        lock.lock()
        defer { lock.unlock() }
        return written
    }
}

/// Fires a terminal error document if the run neither completed nor was
/// cancelled within the given budget.
public final class Watchdog: @unchecked Sendable {
    private let lock = NSLock()
    private var task: Task<Void, Never>?

    public init() {}

    public func arm(
        seconds: Double,
        code: AppleSpeechErrorCode,
        message: String,
        exitCode: Int32,
        outputGuard: OutputGuard
    ) {
        disarm()
        let deadline = UInt64(max(seconds, 0.001) * 1_000_000_000)
        lock.lock()
        let handle = Task { [weak self] in
            try? await Task.sleep(nanoseconds: deadline)
            guard !Task.isCancelled, self != nil else { return }
            let wrote = outputGuard.writeOnce(SchemaPayload.failure(code: code, message: message))
            if wrote {
                Diagnostics.log("watchdog fired: \(code.rawValue); \(message)")
                exit(exitCode)
            }
        }
        task = handle
        lock.unlock()
    }

    public func disarm() {
        lock.lock()
        task?.cancel()
        task = nil
        lock.unlock()
    }
}
