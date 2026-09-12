import Foundation

public enum CLICommand: Sendable, Equatable, CustomStringConvertible {
    case probe
    case transcribe

    public var description: String {
        switch self {
        case .probe: return "probe"
        case .transcribe: return "transcribe"
        }
    }
}

public struct CLIOptions: Sendable, Equatable {
    public var command: CLICommand
    public var locale: String
    public var outputFormat: String
    public var input: String?
    public var timeoutSeconds: Double
    public var debug: Bool
    public var preset: String
    public var segmentSource: String

    public init(
        command: CLICommand,
        locale: String = "zh-TW",
        outputFormat: String = "json",
        input: String? = nil,
        timeoutSeconds: Double = 0,
        debug: Bool = false,
        preset: String = "time-indexed",
        segmentSource: String = "result"
    ) {
        self.command = command
        self.locale = locale
        self.outputFormat = outputFormat
        self.input = input
        self.timeoutSeconds = timeoutSeconds
        self.debug = debug
        self.preset = preset
        self.segmentSource = segmentSource
    }

    public var disableRunSplit: Bool { segmentSource != "runs" }
}

public enum CLIArgumentParser {
    public static let usage = """
    USAGE:
      apple-speech-cli probe      [--locale <id>] [--output-format json] [--debug]
      apple-speech-cli transcribe --input <path> [--locale <id>] [--output-format json]
                                  [--timeout <seconds>] [--debug]

    OPTIONS:
      --input <path>          Local audio file to transcribe.
      --locale <id>           BCP-47 locale identifier (default: zh-TW).
      --output-format <fmt>   Only 'json' is supported.
      --timeout <seconds>     Abort analysis after N seconds (0 disables, default: 0).
      --debug                 Write per-result diagnostics to stderr.
    """

    public static func parse(_ arguments: [String]) throws -> CLIOptions {
        var args = arguments
        guard !args.isEmpty else {
            throw AppleSpeechError(code: .inputError, message: "missing subcommand\n\(usage)")
        }
        let commandName = args.removeFirst()
        let command: CLICommand
        switch commandName {
        case "probe": command = .probe
        case "transcribe": command = .transcribe
        default:
            throw AppleSpeechError(
                code: .inputError,
                message: "unknown subcommand '\(commandName)'\n\(usage)"
            )
        }

        var options = CLIOptions(command: command)
        var index = 0
        while index < args.count {
            let flag = args[index]
            index += 1
            func value() throws -> String {
                guard index < args.count else {
                    throw AppleSpeechError(
                        code: .inputError,
                        message: "flag '\(flag)' requires a value"
                    )
                }
                let next = args[index]
                index += 1
                return next
            }
            switch flag {
            case "--input", "-i":
                options.input = try value()
            case "--locale", "-l":
                options.locale = try value()
            case "--output-format", "-f":
                options.outputFormat = try value()
            case "--timeout":
                let raw = try value()
                guard let seconds = Double(raw), seconds >= 0, seconds.isFinite else {
                    throw AppleSpeechError(
                        code: .inputError,
                        message: "--timeout expects a non-negative number, got '\(raw)'"
                    )
                }
                options.timeoutSeconds = seconds
            case "--debug":
                options.debug = true
            case "--preset":
                let raw = try value()
                let allowed = ["time-indexed", "plain", "plain-alternatives", "progressive", "time-indexed-progressive"]
                guard allowed.contains(raw) else {
                    throw AppleSpeechError(
                        code: .inputError,
                        message: "--preset expects one of \(allowed.joined(separator: "|")), got '\(raw)'"
                    )
                }
                options.preset = raw
            case "--segment-source":
                let raw = try value()
                let allowed = ["runs", "result"]
                guard allowed.contains(raw) else {
                    throw AppleSpeechError(
                        code: .inputError,
                        message: "--segment-source expects one of \(allowed.joined(separator: "|")), got '\(raw)'"
                    )
                }
                options.segmentSource = raw
            default:
                throw AppleSpeechError(
                    code: .inputError,
                    message: "unknown flag '\(flag)'\n\(usage)"
                )
            }
        }

        guard options.outputFormat == "json" else {
            throw AppleSpeechError(
                code: .inputError,
                message: "--output-format only supports 'json', got '\(options.outputFormat)'"
            )
        }
        if command == .transcribe {
            guard let input = options.input, !input.isEmpty else {
                throw AppleSpeechError(
                    code: .inputError,
                    message: "transcribe requires --input <path>"
                )
            }
        }
        return options
    }
}
