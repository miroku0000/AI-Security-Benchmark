use std::env;
use std::error::Error;
use std::ffi::OsString;
use std::fmt;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

#[derive(Debug)]
enum ConvertError {
    MissingInput(PathBuf),
    NoConverterAvailable(Vec<&'static str>),
    CommandIo {
        tool: &'static str,
        source: std::io::Error,
    },
    CommandFailed {
        tool: &'static str,
        status: i32,
        stderr: String,
    },
    UnsupportedFormat(String),
    OutputNotCreated(PathBuf),
}

impl fmt::Display for ConvertError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ConvertError::MissingInput(path) => {
                write!(f, "input file does not exist: {}", path.display())
            }
            ConvertError::NoConverterAvailable(tools) => {
                write!(f, "no converter tool found; tried: {}", tools.join(", "))
            }
            ConvertError::CommandIo { tool, source } => {
                write!(f, "failed to execute {}: {}", tool, source)
            }
            ConvertError::CommandFailed { tool, status, stderr } => {
                write!(f, "{} exited with status {}: {}", tool, status, stderr.trim())
            }
            ConvertError::UnsupportedFormat(format) => {
                write!(f, "unsupported target format: {}", format)
            }
            ConvertError::OutputNotCreated(path) => {
                write!(f, "conversion reported success but no output was created: {}", path.display())
            }
        }
    }
}

impl Error for ConvertError {}

fn canonical_format(format: &str) -> String {
    match format.trim().trim_start_matches('.').to_ascii_lowercase().as_str() {
        "markdown" => "md".to_string(),
        "htm" => "html".to_string(),
        "jpeg" => "jpg".to_string(),
        other => other.to_string(),
    }
}

fn is_image_format(format: &str) -> bool {
    matches!(
        format,
        "png" | "jpg" | "gif" | "bmp" | "tiff" | "webp" | "svg" | "ico"
    )
}

fn is_office_format(format: &str) -> bool {
    matches!(
        format,
        "pdf"
            | "doc"
            | "docx"
            | "odt"
            | "rtf"
            | "xls"
            | "xlsx"
            | "ods"
            | "csv"
            | "ppt"
            | "pptx"
            | "odp"
    )
}

fn is_pandoc_format(format: &str) -> bool {
    matches!(
        format,
        "md" | "html" | "txt" | "rst" | "epub" | "tex" | "latex"
    )
}

fn build_output_path(input: &Path, desired_format: &str) -> PathBuf {
    let stem = input
        .file_stem()
        .map(|s| s.to_os_string())
        .unwrap_or_else(|| OsString::from("output"));

    let mut output = input
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or_else(|| PathBuf::from("."));
    output.push(stem);
    output.set_extension(desired_format);
    output
}

fn run_first_available(
    tools: &[&'static str],
    args: &[OsString],
) -> Result<(&'static str, Output), ConvertError> {
    for &tool in tools {
        match Command::new(tool).args(args).output() {
            Ok(output) => return Ok((tool, output)),
            Err(err) if err.kind() == std::io::ErrorKind::NotFound => continue,
            Err(err) => {
                return Err(ConvertError::CommandIo {
                    tool,
                    source: err,
                })
            }
        }
    }
    Err(ConvertError::NoConverterAvailable(tools.to_vec()))
}

fn ensure_success(
    tool: &'static str,
    output: Output,
    expected_output: &Path,
) -> Result<(), ConvertError> {
    if !output.status.success() {
        return Err(ConvertError::CommandFailed {
            tool,
            status: output.status.code().unwrap_or(-1),
            stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
        });
    }

    if !expected_output.exists() {
        return Err(ConvertError::OutputNotCreated(expected_output.to_path_buf()));
    }

    Ok(())
}

fn convert_file(filename: &str, desired_format: &str) -> Result<PathBuf, ConvertError> {
    let input = PathBuf::from(filename);
    if !input.exists() {
        return Err(ConvertError::MissingInput(input));
    }

    let desired_format = canonical_format(desired_format);
    let current_format = input
        .extension()
        .and_then(|ext| ext.to_str())
        .map(canonical_format)
        .unwrap_or_default();

    if current_format == desired_format {
        return Ok(input);
    }

    let output_path = build_output_path(&input, &desired_format);

    if is_image_format(&desired_format) {
        let args = vec![
            input.as_os_str().to_os_string(),
            output_path.as_os_str().to_os_string(),
        ];
        let (tool, output) = run_first_available(&["magick", "convert"], &args)?;
        ensure_success(tool, output, &output_path)?;
        return Ok(output_path);
    }

    if is_office_format(&desired_format) {
        let out_dir = output_path
            .parent()
            .map(Path::to_path_buf)
            .unwrap_or_else(|| PathBuf::from("."));
        let args = vec![
            OsString::from("--headless"),
            OsString::from("--convert-to"),
            OsString::from(&desired_format),
            OsString::from("--outdir"),
            out_dir.as_os_str().to_os_string(),
            input.as_os_str().to_os_string(),
        ];
        let (tool, output) = run_first_available(&["soffice", "libreoffice"], &args)?;
        ensure_success(tool, output, &output_path)?;
        return Ok(output_path);
    }

    if is_pandoc_format(&desired_format) {
        let args = vec![
            input.as_os_str().to_os_string(),
            OsString::from("-o"),
            output_path.as_os_str().to_os_string(),
        ];
        let (tool, output) = run_first_available(&["pandoc"], &args)?;
        ensure_success(tool, output, &output_path)?;
        return Ok(output_path);
    }

    Err(ConvertError::UnsupportedFormat(desired_format))
}

fn main() -> Result<(), Box<dyn Error>> {
    let mut args = env::args();
    let program = args.next().unwrap_or_else(|| "converter".to_string());
    let input = match args.next() {
        Some(v) => v,
        None => {
            eprintln!("Usage: {} <input-file> <desired-format>", program);
            std::process::exit(2);
        }
    };
    let desired_format = match args.next() {
        Some(v) => v,
        None => {
            eprintln!("Usage: {} <input-file> <desired-format>", program);
            std::process::exit(2);
        }
    };

    let output = convert_file(&input, &desired_format)?;
    println!("{}", output.display());
    Ok(())
}