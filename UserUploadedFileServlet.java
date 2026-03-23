import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Map;

@WebServlet(name = "UserUploadedFileServlet", urlPatterns = "/files")
public class UserUploadedFileServlet extends HttpServlet {

    private static final Map<String, String> EXTENSION_TO_MIME = new HashMap<>();

    static {
        EXTENSION_TO_MIME.put("pdf", "application/pdf");
        EXTENSION_TO_MIME.put("jpg", "image/jpeg");
        EXTENSION_TO_MIME.put("jpeg", "image/jpeg");
        EXTENSION_TO_MIME.put("png", "image/png");
        EXTENSION_TO_MIME.put("gif", "image/gif");
        EXTENSION_TO_MIME.put("bmp", "image/bmp");
        EXTENSION_TO_MIME.put("webp", "image/webp");
        EXTENSION_TO_MIME.put("svg", "image/svg+xml");
        EXTENSION_TO_MIME.put("ico", "image/x-icon");
        EXTENSION_TO_MIME.put("tif", "image/tiff");
        EXTENSION_TO_MIME.put("tiff", "image/tiff");
        EXTENSION_TO_MIME.put("doc", "application/msword");
        EXTENSION_TO_MIME.put("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
        EXTENSION_TO_MIME.put("xls", "application/vnd.ms-excel");
        EXTENSION_TO_MIME.put("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        EXTENSION_TO_MIME.put("ppt", "application/vnd.ms-powerpoint");
        EXTENSION_TO_MIME.put("pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation");
        EXTENSION_TO_MIME.put("odt", "application/vnd.oasis.opendocument.text");
        EXTENSION_TO_MIME.put("ods", "application/vnd.oasis.opendocument.spreadsheet");
        EXTENSION_TO_MIME.put("txt", "text/plain; charset=UTF-8");
        EXTENSION_TO_MIME.put("csv", "text/csv; charset=UTF-8");
        EXTENSION_TO_MIME.put("html", "text/html; charset=UTF-8");
        EXTENSION_TO_MIME.put("htm", "text/html; charset=UTF-8");
        EXTENSION_TO_MIME.put("json", "application/json; charset=UTF-8");
        EXTENSION_TO_MIME.put("xml", "application/xml; charset=UTF-8");
    }

    private Path uploadsRoot;

    @Override
    public void init() throws ServletException {
        String configured = getServletConfig().getInitParameter("upload.directory");
        if (configured != null && !configured.isBlank()) {
            uploadsRoot = Paths.get(configured).toAbsolutePath().normalize();
            return;
        }
        String real = getServletContext().getRealPath("/uploads");
        if (real != null) {
            uploadsRoot = Paths.get(real).toAbsolutePath().normalize();
        } else {
            uploadsRoot = Paths.get(System.getProperty("user.dir"), "uploads").toAbsolutePath().normalize();
        }
    }

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        String filename = req.getParameter("filename");
        if (filename == null || filename.isBlank()) {
            resp.sendError(HttpServletResponse.SC_BAD_REQUEST, "Missing filename parameter");
            return;
        }
        filename = filename.trim().replace('\\', '/');
        if (filename.isEmpty() || filename.charAt(0) == '/') {
            resp.sendError(HttpServletResponse.SC_BAD_REQUEST, "Invalid filename");
            return;
        }
        Path resolved = uploadsRoot;
        for (String segment : filename.split("/")) {
            if (segment.isEmpty() || ".".equals(segment)) {
                continue;
            }
            if ("..".equals(segment)) {
                resp.sendError(HttpServletResponse.SC_BAD_REQUEST, "Invalid filename");
                return;
            }
            resolved = resolved.resolve(segment);
        }
        resolved = resolved.normalize();
        if (!resolved.startsWith(uploadsRoot)) {
            resp.sendError(HttpServletResponse.SC_FORBIDDEN);
            return;
        }
        if (!Files.isRegularFile(resolved)) {
            resp.sendError(HttpServletResponse.SC_NOT_FOUND);
            return;
        }
        String contentType = Files.probeContentType(resolved);
        if (contentType == null) {
            String ext = extension(resolved.getFileName().toString());
            contentType = EXTENSION_TO_MIME.getOrDefault(ext, "application/octet-stream");
        }
        long size = Files.size(resolved);
        resp.setContentType(contentType);
        resp.setContentLengthLong(size);
        try (InputStream in = Files.newInputStream(resolved); OutputStream out = resp.getOutputStream()) {
            in.transferTo(out);
        }
    }

    private static String extension(String name) {
        int dot = name.lastIndexOf('.');
        if (dot < 0 || dot == name.length() - 1) {
            return "";
        }
        return name.substring(dot + 1).toLowerCase();
    }
}
