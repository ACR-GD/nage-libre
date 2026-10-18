// Vision OCR CLI — reconnaît le texte (ja+en) dans des images.
// Usage: vision_ocr <fichier_liste.txt>
//   où chaque ligne = chemin d'une image PNG.
// Sortie (stdout): "chemin\tcandidat1|candidat2|candidat3" par ligne.
import Foundation
import Vision
import AppKit

func ocr(_ path: String) -> String {
    guard let img = NSImage(contentsOfFile: path),
          let tiff = img.tiffRepresentation,
          let bmp = NSBitmapImageRep(data: tiff),
          let cg = bmp.cgImage else {
        return ""
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    req.recognitionLanguages = ["ja", "en"]
    req.minimumTextHeight = 0.0

    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    do {
        try handler.perform([req])
    } catch {
        return ""
    }
    guard let obs = req.results, !obs.isEmpty else { return "" }
    var cands: [String] = []
    for o in obs {
        for c in o.topCandidates(3) {
            cands.append(c.string)
        }
    }
    return cands.joined(separator: "|")
}

let args = CommandLine.arguments
guard args.count >= 2 else {
    FileHandle.standardError.write("Usage: vision_ocr <liste.txt>\n".data(using: .utf8)!)
    exit(1)
}
guard let listText = try? String(contentsOfFile: args[1], encoding: .utf8) else {
    exit(1)
}
for line in listText.split(separator: "\n") {
    let path = String(line)
    if path.isEmpty { continue }
    let result = ocr(path).replacingOccurrences(of: "\n", with: "")
    print("\(path)\t\(result)")
}
