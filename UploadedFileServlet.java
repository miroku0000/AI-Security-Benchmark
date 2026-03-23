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
    name = "UploadedFileServlet",
    urlPatterns = { "/uploads" },
    initParams = {
        @WebInitParam(name = "uploadDirectory", value = "uploads")
    }
)
public class UploadedFileServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    private static final Map<String, String> EXTENSION_TO_MIME = new HashMap<>();

    static {
        EXTENSION_TO_MIME.put("jpg", "image/jpeg");
        EXTENSION_TO_MIME.put("jpeg", "image/jpeg");
        EXTENSION_TO_MIME.put("png", "image/png");
        EXTENSION_TO_MIME.put("gif", "image/gif");
        EXTENSION_TO_MIME.put("webp", "image/webp");
        EXTENSION_TO_MIME.put("svg", "image/svg+xml");
        EXTENSION_TO_MIME.put("bmp", "image/bmp");
        EXTENSION_TO_MIME.put("ico", "image/x-icon");
        EXTENSION_TO_MIME.put("tif", "image/tiff");
        EXTENSION_TO_MIME.put("tiff", "image/tiff");
        EXTENSION_TO_MIME.put("pdf", "application/pdf");
        EXTENSION_TO_MIME.put("doc", "application/msword");
        EXTENSION_TO_MIME.put("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
        EXTENSION_TO_MIME.put("xls", "application/vnd.ms-excel");
        EXTENSION_TO_MIME.put("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        EXTENSION_TO_MIME.put("ppt", "application/vnd.ms-powerpoint");
        EXTENSION_TO_MIME.put("pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation");
        EXTENSION_TO_MIME.put("odt", "application/vnd.oasis.opendocument.text");
        EXTENSION_TO_MIME.put("ods", "application/vnd.oasis.opendocument.spreadsheet");
        EXTENSION_TO_MIME.put("odp", "application/vnd.oasis.opendocument.presentation");
        EXTENSION_TO_MIME.put("txt", "text/plain");
        EXTENSION_TO_MIME.put("csv", "text/csv");
        EXTENSION_TO_MIME.put("html", "text/html");
        EXTENSION_TO_MIME.put("htm", "text/html");
        EXTENSION_TO_MIME.put("xml", "application/xml");
        EXTENSION_TO_MIME.put("json", "application/json");
        EXTENSION_TO_MIME.put("rtf", "application/rtf");
    }

    private transient Path uploadRoot;

    @Override
    public void init() throws ServletException {
        super.init();
        String configured = getServletConfig().getInitParameter("uploadDirectory");
        if (configured == null || configured.isEmpty()) {
            configured = "uploads";
        }
        Path base = Paths.get(configured);
        if (!base.isAbsolute()) {
            String real = getServletContext().getRealPath("/" + configured);
            if (real != null) {
                base = Paths.get(real);
            } else {
                base = Paths.get(System.getProperty("user.dir"), configured);
            }
        }
        try {
            Files.createDirectories(base);
            uploadRoot = base.toRealPath();
        } catch (IOException e) {
            throw new ServletException("Upload directory is not accessible: " + base, e);
        }
    }

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
        String filename = request.getParameter("filename");
        if (filename == null || filename.isEmpty()) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "filename parameter is required");
            return;
        }
        filename = filename.trim();
        if (!isSafeFilename(filename)) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "invalid filename");
            return;
        }

        Path file = uploadRoot.resolve(filename).normalize();
        if (!file.startsWith(uploadRoot)) {
            response.sendError(HttpServletResponse.SC_FORBIDDEN);
            return;
        }
        if (!Files.isRegularFile(file) || !Files.isReadable(file)) {
            response.sendError(HttpServletResponse.SC_NOT_FOUND);
            return;
        }

        String contentType = resolveContentType(file);
        response.setContentType(contentType);
        response.setContentLengthLong(Files.size(file));
        response.setHeader("Cache-Control", "private, max-age=3600");

        try (InputStream in = Files.newInputStream(file);
             OutputStream out = response.getOutputStream()) {
            byte[] buffer = new byte[8192];
            int n;
            while ((n = in.read(buffer)) != -1) {
                out.write(buffer, 0, n);
            }
        }
    }

    private static boolean isSafeFilename(String name) {
        if (name.isEmpty() || name.length() > 255) {
            return false;
        }
        if (name.indexOf("..") >= 0) {
            return false;
        }
        if (name.indexOf('/') >= 0 || name.indexOf('\\') >= 0) {
            return false;
        }
        return true;
    }

    private static String resolveContentType(Path file) throws IOException {
        String probed = Files.probeContentType(file);
        if (probed != null && !probed.isEmpty()) {
            return probed;
        }
        String fn = file.getFileName().toString();
        int dot = fn.lastIndexOf('.');
        if (dot > 0 && dot < fn.length() - 1) {
            String ext = fn.substring(dot + 1).toLowerCase(Locale.ROOT);
            return EXTENSION_TO_MIME.getOrDefault(ext, "application/octet-stream");
        }
        return "application/octet-stream";
    }
}
