use std::process::Command;
use std::path::{Path, PathBuf};
use std::io;

fn convert_file(input_file: &str, target_format: &str) -> Result<String, Box<dyn std::error::Error>> {
    let input_path = Path::new(input_file);
    
    if !input_path.exists() {
        return Err(Box::new(io::Error::new(
            io::ErrorKind::NotFound,
            format!("Input file {} does not exist", input_file)
        )));
    }
    
    let file_stem = input_path.file_stem()
        .ok_or("Invalid filename")?
        .to_str()
        .ok_or("Invalid UTF-8 in filename")?;
    
    let parent_dir = input_path.parent().unwrap_or(Path::new("."));
    let output_file = parent_dir.join(format!("{}.{}", file_stem, target_format));
    let output_path = output_file.to_str()
        .ok_or("Invalid output path")?;
    
    let current_ext = input_path.extension()
        .and_then(|e| e.to_str())
        .unwrap_or("");
    
    let command_result = match (current_ext, target_format) {
        ("pdf", "txt") => {
            Command::new("pdftotext")
                .arg(input_file)
                .arg(output_path)
                .output()
        },
        ("pdf", "html") => {
            Command::new("pdftohtml")
                .arg("-s")
                .arg("-noframes")
                .arg(input_file)
                .arg(output_path)
                .output()
        },
        ("docx", "pdf") | ("doc", "pdf") => {
            Command::new("libreoffice")
                .arg("--headless")
                .arg("--convert-to")
                .arg("pdf")
                .arg("--outdir")
                .arg(parent_dir)
                .arg(input_file)
                .output()
        },
        ("docx", "txt") | ("doc", "txt") => {
            Command::new("libreoffice")
                .arg("--headless")
                .arg("--convert-to")
                .arg("txt")
                .arg("--outdir")
                .arg(parent_dir)
                .arg(input_file)
                .output()
        },
        (_, "pdf") if matches!(current_ext, "jpg" | "jpeg" | "png" | "bmp" | "gif") => {
            Command::new("convert")
                .arg(input_file)
                .arg(output_path)
                .output()
        },
        (_, target) if matches!(current_ext, "jpg" | "jpeg" | "png" | "bmp" | "gif") 
            && matches!(target, "jpg" | "jpeg" | "png" | "bmp" | "gif") => {
            Command::new("convert")
                .arg(input_file)
                .arg(output_path)
                .output()
        },
        ("mp4", "mp3") | ("avi", "mp3") | ("mkv", "mp3") | ("webm", "mp3") => {
            Command::new("ffmpeg")
                .arg("-i")
                .arg(input_file)
                .arg("-vn")
                .arg("-acodec")
                .arg("libmp3lame")
                .arg("-y")
                .arg(output_path)
                .output()
        },
        ("mp4", "avi") | ("mkv", "avi") | ("webm", "avi") => {
            Command::new("ffmpeg")
                .arg("-i")
                .arg(input_file)
                .arg("-c:v")
                .arg("libxvid")
                .arg("-y")
                .arg(output_path)
                .output()
        },
        ("mp3", "wav") | ("flac", "wav") | ("ogg", "wav") => {
            Command::new("ffmpeg")
                .arg("-i")
                .arg(input_file)
                .arg("-y")
                .arg(output_path)
                .output()
        },
        ("wav", "mp3") | ("flac", "mp3") | ("ogg", "mp3") => {
            Command::new("ffmpeg")
                .arg("-i")
                .arg(input_file)
                .arg("-acodec")
                .arg("libmp3lame")
                .arg("-y")
                .arg(output_path)
                .output()
        },
        ("csv", "json") => {
            Command::new("python3")
                .arg("-c")
                .arg(format!(
                    "import csv, json; \
                    with open('{}', 'r') as f: data = list(csv.DictReader(f)); \
                    with open('{}', 'w') as f: json.dump(data, f, indent=2)",
                    input_file, output_path
                ))
                .output()
        },
        ("json", "csv") => {
            Command::new("python3")
                .arg("-c")
                .arg(format!(
                    "import csv, json; \
                    with open('{}', 'r') as f: data = json.load(f); \
                    with open('{}', 'w') as f: \
                        w = csv.DictWriter(f, fieldnames=data[0].keys() if data else []); \
                        w.writeheader(); w.writerows(data)",
                    input_file, output_path
                ))
                .output()
        },
        ("md", "html") | ("markdown", "html") => {
            Command::new("pandoc")
                .arg(input_file)
                .arg("-o")
                .arg(output_path)
                .output()
        },
        ("md", "pdf") | ("markdown", "pdf") => {
            Command::new("pandoc")
                .arg(input_file)
                .arg("-o")
                .arg(output_path)
                .arg("--pdf-engine=xelatex")
                .output()
        },
        ("html", "pdf") => {
            Command::new("wkhtmltopdf")
                .arg(input_file)
                .arg(output_path)
                .output()
        },
        ("txt", "pdf") => {
            Command::new("pandoc")
                .arg(input_file)
                .arg("-o")
                .arg(output_path)
                .output()
        },
        _ => {
            return Err(Box::new(io::Error::new(
                io::ErrorKind::Unsupported,
                format!("Conversion from {} to {} is not supported", current_ext, target_format)
            )));
        }
    };
    
    let output = command_result?;
    
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(Box::new(io::Error::new(
            io::ErrorKind::Other,
            format!("Conversion failed: {}", stderr)
        )));
    }
    
    Ok(output_path.to_string())
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    
    if args.len() != 3 {
        eprintln!("Usage: {} <input_file> <target_format>", args[0]);
        std::process::exit(1);
    }
    
    match convert_file(&args[1], &args[2]) {
        Ok(output_path) => {
            println!("{}", output_path);
        },
        Err(e) => {
            eprintln!("Error: {}", e);
            std::process::exit(1);
        }
    }
}