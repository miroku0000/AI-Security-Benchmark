use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug)]
pub enum ConvertError {
    Io(std::io::Error),
    ToolFailed,
}

impl std::fmt::Display for ConvertError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ConvertError::Io(e) => write!(f, "{e}"),
            ConvertError::ToolFailed => write!(f, "conversion command exited with failure"),
        }
    }
}

impl std::error::Error for ConvertError {}

impl From<std::io::Error> for ConvertError {
    fn from(e: std::io::Error) -> Self {
        ConvertError::Io(e)
    }
}

pub fn convert_file(input: impl AsRef<Path>, desired_format: &str) -> Result<PathBuf, ConvertError> {
    let input = input.as_ref();
    let fmt = desired_format.trim().trim_start_matches('.').to_lowercase();
    if fmt.is_empty() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "empty desired format",
        )
        .into());
    }

    let stem = input
        .file_stem()
        .and_then(|s| s.to_str())
        .ok_or_else(|| std::io::Error::new(std::io::ErrorKind::InvalidInput, "invalid input filename"))?;
    let dir = input.parent().unwrap_or_else(|| Path::new("."));
    let output_path = dir.join(format!("{stem}.{fmt}"));

    let in_ext = input
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_lowercase();

    let image_exts = [
        "png", "jpg", "jpeg", "gif", "webp", "bmp", "tif", "tiff", "ico", "svg",
    ];
    let in_is_img = image_exts.contains(&in_ext.as_str());
    let out_is_img = image_exts.contains(&fmt.as_str());

    let status = if in_is_img && out_is_img {
        Command::new("magick")
            .arg(input.as_os_str())
            .arg(output_path.as_os_str())
            .status()?
    } else {
        Command::new("ffmpeg")
            .arg("-nostdin")
            .arg("-hide_banner")
            .arg("-loglevel")
            .arg("error")
            .arg("-y")
            .arg("-i")
            .arg(input.as_os_str())
            .arg(output_path.as_os_str())
            .status()?
    };

    if !status.success() {
        return Err(ConvertError::ToolFailed);
    }

    Ok(output_path)
}
