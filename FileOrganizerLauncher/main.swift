import Foundation

let task = Process()
task.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
task.arguments = [
    "/Users/jelmer/Dev/file-organizer/organize.py"
] + Array(CommandLine.arguments.dropFirst())

do {
    try task.run()
    task.waitUntilExit()
    exit(task.terminationStatus)
} catch {
    fputs("Error: \(error.localizedDescription)\n", stderr)
    exit(1)
}
