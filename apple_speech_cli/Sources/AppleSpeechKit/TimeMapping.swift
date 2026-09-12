import CoreMedia
import Foundation

/// Deterministic `CMTime` / `CMTimeRange` to seconds conversion.
public enum TimeMapping {
    /// Rounds to milliseconds so that JSON output is stable across runs.
    public static func seconds(_ time: CMTime) -> Double? {
        guard time.isValid, !time.isIndefinite else { return nil }
        let value = time.seconds
        guard value.isFinite else { return nil }
        return (value * 1000).rounded() / 1000
    }

    /// `(nil, nil)` when the range carries no usable timing information.
    public static func bounds(_ range: CMTimeRange) -> (start: Double?, end: Double?) {
        guard range.isValid else { return (nil, nil) }
        let start = seconds(range.start)
        let duration = seconds(range.duration)
        if let start, let duration {
            return (start, ((start + duration) * 1000).rounded() / 1000)
        }
        return (start, seconds(range.end))
    }
}
