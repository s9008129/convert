import Foundation

/// Builds the probe JSON document. Probe never runs inference; it only reports
/// what the host can do so the Python adapter can route truthfully.
public enum ProbePayload {
    public static func build(
        report: LocaleReport?,
        failure: AppleSpeechError?,
        metadata: [(key: String, value: JSONValue)]
    ) -> JSONValue {
        var pairs: [(key: String, value: JSONValue)] = [
            ("schema_version", .string(SchemaPayload.schemaVersion)),
            ("engine", .string(SchemaPayload.engine)),
            ("command", .string("probe")),
            ("locale_requested", report.map { JSONValue.string($0.requestedIdentifier) } ?? .null),
            ("locale_canonical_requested", report.map { JSONValue.string($0.canonicalRequested) } ?? .null),
            ("locale_resolved", report?.resolvedIdentifier.map { JSONValue.string($0) } ?? .null),
            ("locale_supported", .bool(report?.isSupported ?? false)),
            ("locale_in_supported_list", .bool(report?.isInSupportedList ?? false)),
            ("locale_installed", .bool(report?.isInstalled ?? false)),
            ("asset_status", .string(report?.assetStatus ?? "unsupported")),
            ("transcriber_is_available", .bool(report?.transcriberIsAvailable ?? false)),
            ("supported_locales_count", .integer(report?.supportedLocalesCount ?? 0)),
            ("installed_locales_count", .integer(report?.installedLocalesCount ?? 0)),
            ("supported_locales", .array((report?.supportedLocales ?? []).map { JSONValue.string($0) })),
            ("installed_locales", .array((report?.installedLocales ?? []).map { JSONValue.string($0) })),
            ("maximum_reserved_locales", .integer(report?.maximumReservedLocales ?? 0)),
            ("reserved_locales", .array((report?.reservedLocales ?? []).map { JSONValue.string($0) })),
        ]
        if let failure {
            pairs.append((
                "error",
                .object([
                    ("code", .string(failure.code.rawValue)),
                    ("message", .string(failure.message)),
                ])
            ))
        }
        pairs.append(("metadata", .object(metadata)))
        return .object(pairs)
    }
}
