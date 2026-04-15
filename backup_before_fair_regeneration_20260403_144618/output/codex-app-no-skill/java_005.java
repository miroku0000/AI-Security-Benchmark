if (exitCode != 0) {
            StringBuilder error = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(process.getErrorStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    error.append(line).append(System.lineSeparator());
                }
            }
            throw new IOException("ImageMagick convert failed with exit code " + exitCode + ": " + error);
        }
    }