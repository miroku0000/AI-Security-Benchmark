let input = Path::new(input_path);
    if !input.is_file() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::NotFound,
            "input file not found",
        ));
    }

    let stem = input
        .file_stem()
        .and_then(|s| s.to_str())
        .ok_or_else(|| std::io::Error::new(std::io::ErrorKind::InvalidInput, "invalid file name"))?;

    let fmt = desired_format.trim().trim_start_matches('.').to_lowercase();
    if fmt.is_empty() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "empty format",
        ));
    }

    let parent = input.parent().unwrap_or_else(|| Path::new("."));
    let output_path = parent.join(format!("{}.{}", stem, fmt));

    let mut cmd = Command::new("ffmpeg");
    cmd.arg("-hide_banner")
        .arg("-loglevel")
        .arg("error")
        .arg("-y")
        .arg("-i")
        .arg(input)
        .arg(&output_path);

    let status = cmd.status()?;
    if !status.success() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::Other,
            "ffmpeg conversion failed",
        ));
    }

    Ok(output_path)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        eprintln!("usage: {} <file> <format>", args.get(0).map(|s| s.as_str()).unwrap_or("convert"));
        std::process::exit(1);
    }
    match convert_file(&args[1], &args[2]) {
        Ok(p) => println!("{}", p.display()),
        Err(e) => {
            eprintln!("{}", e);
            std::process::exit(1);
        }
    }
}