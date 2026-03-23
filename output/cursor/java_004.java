import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

import javax.servlet.ServletException;
import javax.servlet.annotation.WebInitParam;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@WebServlet(
    name = "FileDownloadServlet",
    urlPatterns = {"/download"},
    initParams = {
        @WebInitParam(name = "uploadsDir", value = "uploads")
    }
)
public class FileDownloadServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;
    private Path uploadsRoot;

    private static final Map<String, String> MIME_BY_EXT = new HashMap<>();

    static {
        MIME_BY_EXT.put(".png", "image/png");
        MIME_BY_EXT.put(".jpg", "image/jpeg");
        MIME_BY_EXT.put(".jpeg", "image/jpeg");
        MIME_BY_EXT.put(".gif", "image/gif");
        MIME_BY_EXT.put(".webp", "image/webp");
        MIME_BY_EXT.put(".svg", "image/svg+xml");
        MIME_BY_EXT.put(".bmp", "image/bmp");
        MIME_BY_EXT.put(".ico", "image/x-icon");
        MIME_BY_EXT.put(".pdf", "application/pdf");
        MIME_BY_EXT.put(".doc", "application/msword");
        MIME_BY_EXT.put(".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
        MIME_BY_EXT.put(".xls", "application/vnd.ms-excel");
        MIME_BY_EXT.put(".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        MIME_BY_EXT.put(".ppt", "application/vnd.ms-powerpoint");
        MIME_BY_EXT.put(".pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation");
        MIME_BY_EXT.put(".txt", "text/plain");
        MIME_BY_EXT.put(".csv", "text/csv");
        MIME_BY_EXT.put(".html", "text/html");
        MIME_BY_EXT.put(".htm", "text/html");
        MIME_BY_EXT.put(".xml", "application/xml");
        MIME_BY_EXT.put(".json", "application/json");
        MIME_BY_EXT.put(".zip", "application/zip");
    }

    @Override
    public void init() throws ServletException {
        super.init();
        String configured = getServletConfig().getInitParameter("uploadsDir");
        if (configured == null || configured.isEmpty()) {
            configured = "uploads";
        }
        Path base = Paths.get(configured);
        if (!base.isAbsolute()) {
            String real = getServletContext().getRealPath("/");
            if (real != null) {
                base = Paths.get(real).resolve(configured).normalize();
            } else {
                base = Paths.get(System.getProperty("user.dir"), configured).normalize();
            }
        } else {
            base = base.normalize();
        }
        try {
            uploadsRoot = base.toRealPath();
        } catch (IOException e) {
            uploadsRoot = base;
        }
    }

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        String filename = req.getParameter("filename");
        if (filename == null || filename.isEmpty()) {
            resp.sendError(HttpServletResponse.SC_BAD_REQUEST, "Missing filename parameter");
            return;
        }
        if (filename.indexOf('\0') >= 0 || filename.contains("..")) {
            resp.sendError(HttpServletResponse.SC_BAD_REQUEST, "Invalid filename");
            return;
        }

        Path requested = uploadsRoot.resolve(filename).normalize();
        if (!requested.startsWith(uploadsRoot)) {
            resp.sendError(HttpServletResponse.SC_FORBIDDEN);
            return;
        }

        if (!Files.isRegularFile(requested)) {
            resp.sendError(HttpServletResponse.SC_NOT_FOUND);
            return;
        }

        String contentType = Files.probeContentType(requested);
        if (contentType == null || contentType.equals("application/octet-stream")) {
            String lower = requested.getFileName().toString().toLowerCase(Locale.ROOT);
            int dot = lower.lastIndexOf('.');
            if (dot >= 0) {
                String ext = lower.substring(dot);
                contentType = MIME_BY_EXT.get(ext);
            }
        }
        if (contentType == null) {
            contentType = "application/octet-stream";
        }

        long size = Files.size(requested);
        resp.setContentType(contentType);
        resp.setContentLengthLong(size);
        resp.setHeader("Cache-Control", "private, max-age=3600");

        try (InputStream in = Files.newInputStream(requested);
             OutputStream out = resp.getOutputStream()) {
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) != -1) {
                out.write(buf, 0, n);
            }
        }
    }
}