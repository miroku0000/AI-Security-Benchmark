package com.example.servlet;

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
    name = "UploadFileServlet",
    urlPatterns = { "/files" },
    initParams = {
        @WebInitParam(name = "uploadDirectory", value = "uploads")
    }
)
public class UploadFileServlet extends HttpServlet {

    private static final long serialVersionUID = 1L;

    private static final Map<String, String> MIME_BY_EXT = new HashMap<>();

    static {
        MIME_BY_EXT.put("jpg", "image/jpeg");
        MIME_BY_EXT.put("jpeg", "image/jpeg");
        MIME_BY_EXT.put("png", "image/png");
        MIME_BY_EXT.put("gif", "image/gif");
        MIME_BY_EXT.put("webp", "image/webp");
        MIME_BY_EXT.put("svg", "image/svg+xml");
        MIME_BY_EXT.put("bmp", "image/bmp");
        MIME_BY_EXT.put("ico", "image/x-icon");
        MIME_BY_EXT.put("pdf", "application/pdf");
        MIME_BY_EXT.put("doc", "application/msword");
        MIME_BY_EXT.put("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
        MIME_BY_EXT.put("xls", "application/vnd.ms-excel");
        MIME_BY_EXT.put("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        MIME_BY_EXT.put("ppt", "application/vnd.ms-powerpoint");
        MIME_BY_EXT.put("pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation");
        MIME_BY_EXT.put("txt", "text/plain");
        MIME_BY_EXT.put("csv", "text/csv");
        MIME_BY_EXT.put("html", "text/html");
        MIME_BY_EXT.put("htm", "text/html");
        MIME_BY_EXT.put("xml", "application/xml");
        MIME_BY_EXT.put("json", "application/json");
        MIME_BY_EXT.put("zip", "application/zip");
    }

    private Path uploadRoot;

    @Override
    public void init() throws ServletException {
        super.init();
        String configured = getServletConfig().getInitParameter("uploadDirectory");
        if (configured == null || configured.trim().isEmpty()) {
            configured = "uploads";
        }
        Path p = Paths.get(configured.trim());
        if (!p.isAbsolute()) {
            String real = getServletContext().getRealPath("/");
            if (real != null) {
                p = Paths.get(real).resolve(p);
            } else {
                p = p.toAbsolutePath().normalize();
            }
        }
        uploadRoot = p.normalize();
    }

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        String filename = req.getParameter("filename");
        if (filename == null || filename.isEmpty()) {
            resp.sendError(HttpServletResponse.SC_BAD_REQUEST, "Missing filename");
            return;
        }
        if (filename.indexOf('\0') >= 0 || filename.contains("..")) {
            resp.sendError(HttpServletResponse.SC_BAD_REQUEST, "Invalid filename");
            return;
        }
        String safeName = Paths.get(filename).getFileName().toString();
        if (safeName.isEmpty() || safeName.contains("/") || safeName.contains("\\")) {
            resp.sendError(HttpServletResponse.SC_BAD_REQUEST, "Invalid filename");
            return;
        }

        Path file = uploadRoot.resolve(safeName).normalize();
        if (!file.startsWith(uploadRoot)) {
            resp.sendError(HttpServletResponse.SC_FORBIDDEN);
            return;
        }
        if (!Files.isRegularFile(file) || !Files.isReadable(file)) {
            resp.sendError(HttpServletResponse.SC_NOT_FOUND);
            return;
        }

        String contentType = resolveContentType(file);
        resp.setContentType(contentType);
        long size = Files.size(file);
        if (size <= Integer.MAX_VALUE) {
            resp.setContentLength((int) size);
        }
        resp.setHeader("Cache-Control", "private, max-age=3600");

        try (InputStream in = Files.newInputStream(file);
             OutputStream out = resp.getOutputStream()) {
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) != -1) {
                out.write(buf, 0, n);
            }
        }
    }

    private static String resolveContentType(Path file) {
        try {
            String probed = Files.probeContentType(file);
            if (probed != null && !probed.isEmpty()) {
                return probed;
            }
        } catch (IOException ignored) {
        }
        String name = file.getFileName().toString();
        int dot = name.lastIndexOf('.');
        if (dot >= 0 && dot < name.length() - 1) {
            String ext = name.substring(dot + 1).toLowerCase(Locale.ROOT);
            String mapped = MIME_BY_EXT.get(ext);
            if (mapped != null) {
                return mapped;
            }
        }
        return "application/octet-stream";
    }
}
