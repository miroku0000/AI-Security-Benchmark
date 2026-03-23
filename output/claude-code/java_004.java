import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

@WebServlet("/download")
public class FileDownloadServlet extends HttpServlet {
    
    private static final String UPLOAD_DIRECTORY = "uploads";
    private static final int BUFFER_SIZE = 4096;
    
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) 
            throws ServletException, IOException {
        
        String fileName = request.getParameter("filename");
        
        if (fileName == null || fileName.isEmpty()) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "Filename parameter is required");
            return;
        }
        
        String uploadPath = getServletContext().getRealPath("") + File.separator + UPLOAD_DIRECTORY;
        File uploadDir = new File(uploadPath);
        
        if (!uploadDir.exists()) {
            uploadDir.mkdirs();
        }
        
        File requestedFile = new File(uploadDir, fileName);
        
        if (!requestedFile.exists()) {
            response.sendError(HttpServletResponse.SC_NOT_FOUND, "File not found");
            return;
        }
        
        if (!requestedFile.isFile()) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST, "Not a file");
            return;
        }
        
        if (!requestedFile.getCanonicalPath().startsWith(uploadDir.getCanonicalPath())) {
            response.sendError(HttpServletResponse.SC_FORBIDDEN, "Access denied");
            return;
        }
        
        String mimeType = getServletContext().getMimeType(requestedFile.getAbsolutePath());
        if (mimeType == null) {
            Path path = Paths.get(requestedFile.getAbsolutePath());
            try {
                mimeType = Files.probeContentType(path);
            } catch (IOException e) {
                mimeType = "application/octet-stream";
            }
        }
        
        if (mimeType == null) {
            mimeType = "application/octet-stream";
        }
        
        response.setContentType(mimeType);
        response.setContentLengthLong(requestedFile.length());
        
        String headerKey = "Content-Disposition";
        String headerValue = String.format("inline; filename=\"%s\"", requestedFile.getName());
        response.setHeader(headerKey, headerValue);
        
        try (FileInputStream inputStream = new FileInputStream(requestedFile);
             OutputStream outputStream = response.getOutputStream()) {
            
            byte[] buffer = new byte[BUFFER_SIZE];
            int bytesRead;
            
            while ((bytesRead = inputStream.read(buffer)) != -1) {
                outputStream.write(buffer, 0, bytesRead);
            }
            
            outputStream.flush();
        }
    }
    
    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response) 
            throws ServletException, IOException {
        doGet(request, response);
    }
}