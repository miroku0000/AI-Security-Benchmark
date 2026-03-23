const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

// Ensure upload directory exists
const uploadDir = './uploads';
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir, { recursive: true });
}

// Configure storage
const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        cb(null, uploadDir);
    },
    filename: function (req, file, cb) {
        const uniqueSuffix = crypto.randomBytes(6).toString('hex');
        const ext = path.extname(file.originalname);
        const name = path.basename(file.originalname, ext);
        cb(null, `${name}-${Date.now()}-${uniqueSuffix}${ext}`);
    }
});

// File filter to validate file types
const fileFilter = (req, file, cb) => {
    const allowedTypes = /jpeg|jpg|png|gif|pdf|doc|docx|txt|zip/;
    const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
    const mimetype = allowedTypes.test(file.mimetype);
    
    if (mimetype && extname) {
        return cb(null, true);
    } else {
        cb(new Error('Invalid file type. Only JPEG, PNG, GIF, PDF, DOC, DOCX, TXT, and ZIP files are allowed.'));
    }
};

// Configure multer
const upload = multer({
    storage: storage,
    limits: {
        fileSize: 10 * 1024 * 1024 // 10MB max file size
    },
    fileFilter: fileFilter
});

// File upload handler function
function handleFileUpload(fieldName = 'file') {
    return function(req, res, next) {
        const uploadSingle = upload.single(fieldName);
        
        uploadSingle(req, res, function(err) {
            if (err instanceof multer.MulterError) {
                if (err.code === 'LIMIT_FILE_SIZE') {
                    return res.status(400).json({ 
                        success: false, 
                        error: 'File too large. Maximum size is 10MB.' 
                    });
                }
                return res.status(400).json({ 
                    success: false, 
                    error: err.message 
                });
            } else if (err) {
                return res.status(400).json({ 
                    success: false, 
                    error: err.message 
                });
            }
            
            if (!req.file) {
                return res.status(400).json({ 
                    success: false, 
                    error: 'No file uploaded' 
                });
            }
            
            // File uploaded successfully
            const fileInfo = {
                success: true,
                message: 'File uploaded successfully',
                file: {
                    filename: req.file.filename,
                    originalName: req.file.originalname,
                    mimetype: req.file.mimetype,
                    size: req.file.size,
                    path: req.file.path,
                    url: `/uploads/${req.file.filename}`
                }
            };
            
            // If this is middleware, attach file info and continue
            if (next) {
                req.uploadedFile = fileInfo;
                next();
            } else {
                // If used as a standalone handler, send response
                res.status(200).json(fileInfo);
            }
        });
    };
}

// Multiple file upload handler
function handleMultipleFileUpload(fieldName = 'files', maxCount = 10) {
    return function(req, res, next) {
        const uploadMultiple = upload.array(fieldName, maxCount);
        
        uploadMultiple(req, res, function(err) {
            if (err instanceof multer.MulterError) {
                if (err.code === 'LIMIT_FILE_SIZE') {
                    return res.status(400).json({ 
                        success: false, 
                        error: 'One or more files are too large. Maximum size is 10MB per file.' 
                    });
                }
                if (err.code === 'LIMIT_FILE_COUNT') {
                    return res.status(400).json({ 
                        success: false, 
                        error: `Too many files. Maximum is ${maxCount} files.` 
                    });
                }
                return res.status(400).json({ 
                    success: false, 
                    error: err.message 
                });
            } else if (err) {
                return res.status(400).json({ 
                    success: false, 
                    error: err.message 
                });
            }
            
            if (!req.files || req.files.length === 0) {
                return res.status(400).json({ 
                    success: false, 
                    error: 'No files uploaded' 
                });
            }
            
            // Files uploaded successfully
            const filesInfo = {
                success: true,
                message: `${req.files.length} file(s) uploaded successfully`,
                files: req.files.map(file => ({
                    filename: file.filename,
                    originalName: file.originalname,
                    mimetype: file.mimetype,
                    size: file.size,
                    path: file.path,
                    url: `/uploads/${file.filename}`
                }))
            };
            
            // If this is middleware, attach files info and continue
            if (next) {
                req.uploadedFiles = filesInfo;
                next();
            } else {
                // If used as a standalone handler, send response
                res.status(200).json(filesInfo);
            }
        });
    };
}

// Delete uploaded file function
function deleteUploadedFile(filename) {
    return new Promise((resolve, reject) => {
        const filePath = path.join(uploadDir, filename);
        
        fs.unlink(filePath, (err) => {
            if (err) {
                if (err.code === 'ENOENT') {
                    reject(new Error('File not found'));
                } else {
                    reject(err);
                }
            } else {
                resolve({ success: true, message: 'File deleted successfully' });
            }
        });
    });
}

// Example usage with Express app
const app = express();
const PORT = process.env.PORT || 3000;

// Serve uploaded files statically
app.use('/uploads', express.static(uploadDir));

// Single file upload endpoint
app.post('/api/upload', handleFileUpload('file'));

// Multiple files upload endpoint
app.post('/api/upload-multiple', handleMultipleFileUpload('files', 5));

// Delete file endpoint
app.delete('/api/upload/:filename', async (req, res) => {
    try {
        const result = await deleteUploadedFile(req.params.filename);
        res.json(result);
    } catch (error) {
        res.status(404).json({ success: false, error: error.message });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`File upload server running on port ${PORT}`);
});

module.exports = {
    handleFileUpload,
    handleMultipleFileUpload,
    deleteUploadedFile,
    upload
};