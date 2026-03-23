import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Map;

import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@WebServlet(name = "FileUploadServlet", urlPatterns = { "/files" })
public class FileUploadServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;
    private static final String UPLOADS_DIR = "uploads";
    private static final int BUFFER_SIZE = 8192;

    private static final Map<String, String> MIME_TYPES = new HashMap<>();

    static {
        MIME_TYPES.put("jpg", "image/jpeg");
        MIME_TYPES.put("jpeg", "image/jpeg");
        MIME_TYPES.put("png", "image/png");
        MIME_TYPES.put("gif", "image/gif");
        MIME_TYPES.put("webp", "image/webp");
        MIME_TYPES.put("svg", "image/svg+xml");
        MIME_TYPES.put("bmp", "image/bmp");
        MIME_TYPES.put("ico", "image/x-icon");
        MIME_TYPES.put("pdf", "application/pdf");
        MIME_TYPES.put("doc", "application/msword");
        MIME_TYPES.put("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
        MIME_TYPES.put("xls", "application/vnd.ms-excel");
        MIME_TYPES.put("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        MIME_TYPES.put("ppt", "application/vnd.ms-powerpoint");
        MIME_TYPES.put("pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation");
        MIME_TYPES.put("txt", "text/plain; charset=UTF-8");
        MIME_TYPES.put("html", "text/html; charset=UTF-8");
        MIME_TYPES.put("htm", "text/html; charset=UTF-8");
        MIME_TYPES.put("css", "text/css; charset=UTF-8");
        MIME_TYPES.put("js", "application/javascript; charset=UTF-8");
        MIME_TYPES.put("json", "application/json; charset=UTF-8");
        MIME_TYPES.put("xml", "application/xml; charset=UTF-8");
        MIME_TYPES.put("zip", "application/zip");
        MIME_TYPES.put("csv", "text/csv; charset=UTF-8");
        MIME_TYPES.put("rtf", "application/rtf");
    }

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        String filename = request.getParameter("filename");
        if (filename == null || filename.trim().isEmpty()) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "Missing filename parameter");
            return;
        }
        filename = filename.trim();
        if (filename.contains("..") || filename.contains(File.separator) || filename.contains("/")
                || filename.contains("\\")) {
            response.sendError(HttpServletResponse.SC_FORBIDDEN, "Invalid filename");
            return;
        }

        Path uploadsBase = resolveUploadsBase(request);
        Path filePath = uploadsBase.resolve(filename).normalize();
        if (!filePath.startsWith(uploadsBase)) {
            response.sendError(HttpServletResponse.SC_FORBIDDEN, "Invalid path");
            return;
        }

        File file = filePath.toFile();
        if (!file.isFile() || !file.canRead()) {
            response.sendError(HttpServletResponse.SC_NOT_FOUND, "File not found");
            return;
        }

        String contentType = guessContentType(filePath);
        response.setContentType(contentType);
        response.setContentLengthLong(file.length());
        String name = file.getName();
        response.setHeader("Content-Disposition", "inline; filename=\"" + escapeFilenameHeader(name) + "\"");

        try (InputStream in = new FileInputStream(file);
                OutputStream out = response.getOutputStream()) {
            byte[] buffer = new byte[BUFFER_SIZE];
            int read;
            while ((read = in.read(buffer)) != -1) {
                out.write(buffer, 0, read);
            }
        }
    }

    private Path resolveUploadsBase(HttpServletRequest request) {
        String realPath = request.getServletContext().getRealPath("/" + UPLOADS_DIR);
        if (realPath != null) {
            return Paths.get(realPath).normalize();
        }
        return Paths.get(System.getProperty("user.dir"), UPLOADS_DIR).normalize();
    }

    private static String guessContentType(Path filePath) throws IOException {
        String probed = Files.probeContentType(filePath);
        if (probed != null && !probed.isEmpty()) {
            return probed;
        }
        String name = filePath.getFileName().toString();
        int dot = name.lastIndexOf('.');
        if (dot >= 0 && dot < name.length() - 1) {
            String ext = name.substring(dot + 1).toLowerCase();
            String mapped = MIME_TYPES.get(ext);
            if (mapped != null) {
                return mapped;
            }
        }
        return "application/octet-stream";
    }

    private static String escapeFilenameHeader(String name) {
        return name.replace("\"", "\\\"");
    }
}
