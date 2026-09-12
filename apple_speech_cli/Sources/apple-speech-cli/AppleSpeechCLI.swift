import AppleSpeechKit
import Darwin
import Dispatch
import Foundation

/// Process entry point.
///
/// The executable intentionally has no bundle, no Info.plist, no entitlements
/// and no code signature: WAVE-1 has to prove whether a bare SwiftPM binary can
/// own the Speech assets.
@main
struct AppleSpeechCLI {
    static func main() async {
        let control = AnalysisControl()
        let outputGuard = OutputGuard()
        let watchdog = Watchdog()
        installSignalHandlers(control: control, outputGuard: outputGuard, watchdog: watchdog)

        let arguments = Array(CommandLine.arguments.dropFirst())
        let code = await Runner.run(
            arguments: arguments,
            control: control,
            outputGuard: outputGuard,
            watchdog: watchdog
        )
        exit(code)
    }

    /// SIGTERM/SIGINT are turned into a cooperative cancel: the analysis is
    /// cancelled, the single JSON document is written with APPLE_CANCELLED and
    /// the process exits 7. A grace watchdog guarantees termination even if the
    /// framework never returns.
    static func installSignalHandlers(control: AnalysisControl, outputGuard: OutputGuard, watchdog: Watchdog) {
        signal(SIGTERM, SIG_IGN)
        signal(SIGINT, SIG_IGN)
        for signalNumber in [SIGTERM, SIGINT] {
            let source = DispatchSource.makeSignalSource(signal: signalNumber, queue: .global())
            source.setEventHandler {
                Diagnostics.log("received signal \(signalNumber); cancelling analysis")
                watchdog.arm(
                    seconds: 5,
                    code: .cancelled,
                    message: "cancelled by signal \(signalNumber)",
                    exitCode: AppleSpeechErrorCode.cancelled.exitCode,
                    outputGuard: outputGuard
                )
                Task {
                    await control.cancelNow()
                }
            }
            source.resume()
            signalSources.append(source)
        }
    }

    nonisolated(unsafe) static var signalSources: [DispatchSourceSignal] = []
}
