let Some(filename) = args.next() else {
        eprintln!(
            "usage: {} <config-file>",
            Path::new(&program)
                .file_name()
                .and_then(|s| s.to_str())
                .unwrap_or("config_reader")
        );
        return Err(io::Error::new(
            ErrorKind::InvalidInput,
            "missing configuration filename",
        ));
    };