import Foundation
import AppKit
import PDFKit
import AVFoundation
import Vision
import ImageIO
let args=CommandLine.arguments
let rows=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:args[1]))) as! [[String:Any]]
let folder=URL(fileURLWithPath:args[2]);try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true)
func ocr(_ im:CGImage)->[[String:Any]] {let req=VNRecognizeTextRequest();req.recognitionLevel = .accurate;req.usesLanguageCorrection=true;do{try VNImageRequestHandler(cgImage:im).perform([req]);return (req.results ?? []).compactMap{r in guard let t=r.topCandidates(1).first else{return nil};return ["text":t.string,"confidence":t.confidence,"height":r.boundingBox.height,"y":r.boundingBox.minY]}}catch{return []}}
func save(_ im:CGImage,_ url:URL){let rep=NSBitmapImageRep(cgImage:im);if let d=rep.representation(using:.jpeg,properties:[.compressionFactor:0.8]){try? d.write(to:url)}}
for (n,row) in rows.enumerated(){autoreleasepool{
 let id=row["id"] as! Int;let path=row["path"] as! String;let dest=folder.appendingPathComponent(String(format:"%05d.json",id));if FileManager.default.fileExists(atPath:dest.path){return}
 let url=URL(fileURLWithPath:path);var result:[String:Any]=["id":id,"path":path];var lines=[[String:Any]]();let ext=url.pathExtension.lowercased()
 if ext=="pdf" {
  if let pdf=PDFDocument(url:url), !pdf.isLocked {result["pages"]=pdf.pageCount;result["kind"]="PDF";var texts=[String]();for i in 0..<min(pdf.pageCount,10){if let page=pdf.page(at:i){texts.append(page.string ?? "");if i==0 || (i<3 && (page.string ?? "").count<80){let ns=page.thumbnail(of:NSSize(width:1200,height:1600),for:.mediaBox);if let cg=ns.cgImage(forProposedRect:nil,context:nil,hints:nil){if i==0{save(cg,folder.appendingPathComponent(String(format:"%05d.jpg",id)))};lines += ocr(cg)}}}};result["text"]=String(texts.joined(separator:"\n").prefix(16000));result["evidence_note"]="Text from first ten pages; cover OCR; OCR first three scanned pages."
  } else {result["error"]="PDF unreadable or password protected"}
 } else if ext=="mp4" {
  result["kind"]="Video";let asset=AVURLAsset(url:url);let duration=CMTimeGetSeconds(asset.duration);if duration.isFinite && duration>0 {result["duration"]=duration;let gen=AVAssetImageGenerator(asset:asset);gen.appliesPreferredTrackTransform=true;gen.maximumSize=CGSize(width:1200,height:900);var samples=[Double]();for fraction in [0.02,0.16,0.35,0.55,0.75,0.94]{let t=max(0,min(duration-0.05,duration*fraction));do{let im=try gen.copyCGImage(at:CMTime(seconds:t,preferredTimescale:600),actualTime:nil);let index=samples.count;save(im,folder.appendingPathComponent(String(format:"%05d-frame%d.jpg",id,index)));if index==0{save(im,folder.appendingPathComponent(String(format:"%05d.jpg",id)))};lines += ocr(im);samples.append(t)}catch{}};result["sample_seconds"]=samples;result["evidence_note"]="Six sampled video frames and visible text; no audio transcription.";if samples.isEmpty{result["error"]="No video frames could be decoded"}
  }else{result["error"]="Invalid or unreadable video duration"}
 } else {
  result["kind"]="Image";if let source=CGImageSourceCreateWithURL(url as CFURL,nil),let im=CGImageSourceCreateThumbnailAtIndex(source,0,[kCGImageSourceCreateThumbnailFromImageAlways:true,kCGImageSourceThumbnailMaxPixelSize:1400,kCGImageSourceCreateThumbnailWithTransform:true] as CFDictionary){save(im,folder.appendingPathComponent(String(format:"%05d.jpg",id)));lines=ocr(im)}else{result["error"]="Image could not be decoded"}
 }
 result["lines"]=lines
 if let d=try? JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]){try? d.write(to:dest)}
 if n%20==0{print("Extracted \(n+1)/\(rows.count)");fflush(stdout)}
}}
