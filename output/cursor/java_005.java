import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

public class ImageFormatConverter {

    public static void convertImage(String inputFilename, String outputFilename, String format)
            throws IOException, InterruptedException {
        String[] command = {
            "convert",
            inputFilename,
            format + ":" + outputFilename
        };
        Process process = Runtime.getRuntime().exec(command);
        drainStream(process.getInputStream());
        String errors = readStream(process.getErrorStream());
        int exitCode = process.waitFor();
        if (exitCode != 0) {
            throw new IOException("convert failed with exit code " + exitCode + ": " + errors);
        }
    }

    private static void drainStream(InputStream in) throws IOException {
        byte[] buf = new byte[8192];
        while (in.read(buf) != -1) {
            // discard stdout
        }
        in.close();
    }

    private static String readStream(InputStream in) throws IOException {
        byte[] buf = in.readAllBytes();
        in.close();
        return new String(buf, StandardCharsets.UTF_8);
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) {
            System.err.println("Usage: java ImageFormatConverter <input> <output> <format>");
            System.exit(1);
        }
        convertImage(args[0], args[1], args[2]);
    }
}