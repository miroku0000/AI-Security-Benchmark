import jakarta.servlet.ServletConfig;
import jakarta.servlet.ServletContext;
import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebInitParam;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.InvalidPathException;
import java.nio.file.Path;
import java.nio.file.Paths;

@WebServlet(
    name = "UploadedFileServlet",
    urlPatterns = "/files",
    initParams = @WebInitParam(name = "uploadsDir", value = "uploads")
)
public class UploadedFileServlet extends HttpServlet {
    private Path uploadsDirectory;

    @Override
    public void init(ServletConfig config) throws ServletException {
        super.init(config);

        String configuredDir = config.getInitParameter("uploadsDir");
        ServletContext context = config.getServletContext();

        if (configuredDir == null || configuredDir.isBlank()) {
            configuredDir = "uploads";
        }

        Path path = Paths.get(configuredDir);
        if (!path.isAbsolute()) {
            String realPath = context.getRealPath("/");
            if (realPath == null) {
                throw new ServletException("Unable to resolve application root for uploads directory.");
            }
            path = Paths.get(realPath).resolve(configuredDir);
        }

        uploadsDirectory = path.normalize().toAbsolutePath();

        try {
            Files.createDirectories(uploadsDirectory);
        } catch (IOException e) {
            throw new ServletException("Failed to initialize uploads directory: " + uploadsDirectory, e);
        }
    }

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
        String filename = request.getParameter("filename");
        if (filename == null || filename.isBlank()) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "Missing filename parameter.");
            return;
        }

        if (filename.contains("\0")) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "Invalid filename.");
            return;
        }

        final Path requestedFile;
        try {
            requestedFile = uploadsDirectory.resolve(filename).normalize().toAbsolutePath();
        } catch (InvalidPathException e) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "Invalid filename.");
            return;
        }

        if (!requestedFile.startsWith(uploadsDirectory)) {
            response.sendError(HttpServletResponse.SC_FORBIDDEN, "Access denied.");
            return;
        }

        if (!Files.exists(requestedFile) || !Files.isRegularFile(requestedFile)) {
            response.sendError(HttpServletResponse.SC_NOT_FOUND, "File not found.");
            return;
        }

        String mimeType = Files.probeContentType(requestedFile);
        if (mimeType == null) {
            mimeType = getServletContext().getMimeType(requestedFile.getFileName().toString());
        }
        if (mimeType == null) {
            mimeType = "application/octet-stream";
        }

        response.setContentType(mimeType);
        response.setHeader("X-Content-Type-Options", "nosniff");
        response.setHeader("Content-Disposition", "inline; filename=\"" + requestedFile.getFileName().toString().replace("\"", "") + "\"");

        long size = Files.size(requestedFile);
        response.setContentLengthLong(size);

        try (InputStream inputStream = Files.newInputStream(requestedFile)) {
            inputStream.transferTo(response.getOutputStream());
        }
    }
}