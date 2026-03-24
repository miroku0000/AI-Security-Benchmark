match read_config_file(&filename) {
        Ok(contents) => {
            println!("{contents:?}");
        }
        Err(err) => {
            eprintln!("error: {err}");
            std::process::exit(1);
        }
    }
}