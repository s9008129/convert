import Foundation

/// Locale identifier helpers.
///
/// The authoritative answer for "is this locale usable" always comes from
/// `SpeechTranscriber.supportedLocale(equivalentTo:)` / `supportedLocales`.
/// These helpers only normalise identifiers for comparison, reporting and
/// tests so that `zh-TW`, `zh_TW` and `zh-Hant-TW` are not reported as
/// different languages by our own code.
public enum LocaleEquivalence {
    public struct Components: Sendable, Equatable {
        public let language: String
        public let script: String?
        public let region: String?
    }

    /// Splits a locale identifier into language / script / region.
    /// Accepts both `-` and `_` separators and is case-insensitive.
    public static func components(_ identifier: String) -> Components {
        let parts = identifier
            .split(separator: ".", maxSplits: 1, omittingEmptySubsequences: false)[0]
            .replacingOccurrences(of: "_", with: "-")
            .split(separator: "-")
            .map { String($0) }
        var language = ""
        var script: String?
        var region: String?
        for part in parts {
            if part.isEmpty { continue }
            if language.isEmpty {
                language = part.lowercased()
                continue
            }
            if part.count == 4, part.allSatisfy({ $0.isLetter }) {
                script = part.prefix(1).uppercased() + part.dropFirst().lowercased()
                continue
            }
            if (part.count == 2 || part.count == 3), part.allSatisfy({ $0.isLetter }) {
                region = part.uppercased()
                continue
            }
            // Numeric regions such as "419" and anything unrecognised fall through.
            if region == nil, part.allSatisfy({ $0.isNumber }) {
                region = part
            }
        }
        return Components(language: language, script: script, region: region)
    }

    /// Normalised comparison form, e.g. `zh-TW`, `zh-TW`, `zh-Hant-TW`.
    public static func canonicalIdentifier(_ identifier: String) -> String {
        let parts = components(identifier)
        var out = parts.language
        if let script = parts.script { out += "-" + script }
        if let region = parts.region { out += "-" + region }
        return out
    }

    /// Two identifiers are equivalent when language matches and neither the
    /// script nor the region contradicts the other.
    public static func isEquivalent(_ lhs: String, _ rhs: String) -> Bool {
        let a = components(lhs)
        let b = components(rhs)
        guard !a.language.isEmpty, a.language == b.language else { return false }
        if let sa = a.script, let sb = b.script, sa != sb { return false }
        if let ra = a.region, let rb = b.region, ra != rb { return false }
        return true
    }
}
