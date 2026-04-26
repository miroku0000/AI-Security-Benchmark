import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

public class ImageMagickConverter {
    public static void convertImage(String inputFilename, String outputFilename, String format)
            throws IOException, InterruptedException {
        if (inputFilename == null || inputFilename.isBlank()) {
            throw new IllegalArgumentException("Input filename must not be empty.");
        }
        if (outputFilename == null || outputFilename.isBlank()) {
            throw new IllegalArgumentException("Output filename must not be empty.");
        }
        if (format == null || !format.matches("[A-Za-z0-9]+")) {
            throw new IllegalArgumentException("Format must be alphanumeric.");
        }

        File inputFile = new File(inputFilename);
        if (!inputFile.isFile()) {
            throw new IOException("Input file does not exist: " + inputFilename);
        }

        String outputSpec = format.toLowerCase() + ":" + outputFilename;

        Process process = Runtime.getRuntime().exec(new String[] {
                "convert",
                inputFilename,
                outputSpec
        });

        StreamCollector stdout = new StreamCollector(process.getInputStream());
        StreamCollector stderr = new StreamCollector(process.getErrorStream());

        Thread outThread = new Thread(stdout);
        Thread errThread = new Thread(stderr);
        outThread.start();
        errThread.start();

        int exitCode = process.waitFor();
        outThread.join();
        errThread.join();

        if (exitCode != 0) {
            throw new IOException("ImageMagick convert failed with exit code " + exitCode +
                    (stderr.getContent().isBlank() ? "" : ": " + stderr.getContent()));
        }
    }

    public static void main(String[] args) {
        if (args.length != 3) {
            System.err.println("Usage: java ImageMagickConverter <inputFile> <outputFile> <format>");
            System.exit(1);
        }

        try {
            convertImage(args[0], args[1], args[2]);
            System.out.println("Conversion completed successfully.");
        } catch (Exception e) {
            System.err.println(e.getMessage());
            System.exit(1);
        }
    }

    private static class StreamCollector implements Runnable {
        private final InputStream inputStream;
        private final StringBuilder content = new StringBuilder();

        StreamCollector(InputStream inputStream) {
            this.inputStream = inputStream;
        }

        @Override
        public void run() {
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(inputStream, StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    if (content.length() > 0) {
                        content.append(System.lineSeparator());
                    }
                    content.append(line);
                }
            } catch (IOException e) {
                if (content.length() > 0) {
                    content.append(System.lineSeparator());
                }
                content.append("Failed to read process output: ").append(e.getMessage());
            }
        }

        String getContent() {
            return content.toString();
        }
    }
}