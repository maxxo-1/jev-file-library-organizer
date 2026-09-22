import Foundation
let source = URL(fileURLWithPath: CommandLine.arguments[1])
var result: NSURL?
do {
 try FileManager.default.trashItem(at: source, resultingItemURL: &result)
 print(result?.path ?? "")
} catch { fputs("\(error)\n", stderr); exit(1) }
