public class ImageConverter {
    
    public static boolean convertImage(String inputFilename, String outputFilename, String format) {
        try {
            String command = String.format("convert %s %s", inputFilename, outputFilename);
            
            Process process = Runtime.getRuntime().exec(command);
            
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            BufferedReader errorReader = new BufferedReader(new InputStreamReader(process.getErrorStream()));
            
            String line;
            StringBuilder output = new StringBuilder();
            StringBuilder errorOutput = new StringBuilder();
            
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
            }
            
            while ((line = errorReader.readLine()) != null) {
                errorOutput.append(line).append("\n");
            }
            
            int exitCode = process.waitFor();
            
            reader.close();
            errorReader.close();
            
            if (exitCode != 0) {
                System.err.println("Error converting image: " + errorOutput.toString());
                return false;
            }
            
            return true;
            
        } catch (IOException e) {
            System.err.println("IO Exception: " + e.getMessage());
            return false;
        } catch (InterruptedException e) {
            System.err.println("Process interrupted: " + e.getMessage());
            return false;
        }
    }
    
    public static void main(String[] args) {
        if (args.length != 3) {
            System.out.println("Usage: java ImageConverter <input_file> <output_file> <format>");
            System.out.println("Example: java ImageConverter image.jpg image.png png");
            System.exit(1);
        }
        
        String inputFile = args[0];
        String outputFile = args[1];
        String format = args[2];
        
        if (!new File(inputFile).exists()) {
            System.err.println("Input file does not exist: " + inputFile);
            System.exit(1);
        }
        
        if (!outputFile.toLowerCase().endsWith("." + format.toLowerCase())) {
            outputFile = outputFile + "." + format.toLowerCase();
        }
        
        boolean success = convertImage(inputFile, outputFile, format);
        
        if (success) {
            System.out.println("Successfully converted " + inputFile + " to " + outputFile);
        } else {
            System.err.println("Failed to convert image");
            System.exit(1);
        }
    }
}