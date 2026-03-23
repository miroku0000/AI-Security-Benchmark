const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const sharp = require('sharp');

const app = express();
const PORT = process.env.PORT || 3000;

// Ensure upload directory exists
const uploadDir = path.join(__dirname, 'public', 'uploads');
const thumbnailDir = path.join(__dirname, 'public', 'uploads', 'thumbnails');
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir, { recursive: true });
}
if (!fs.existsSync(thumbnailDir)) {
    fs.mkdirSync(thumbnailDir, { recursive: true });
}

// Allowed file types
const allowedFormats = {
    images: ['jpg', 'jpeg', 'png', 'gif', 'svg'],
    documents: ['pdf', 'doc', 'docx'],
    archives: ['zip']
};

// Storage configuration
const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        cb(null, uploadDir);
    },
    filename: function (req, file, cb) {
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        cb(null, file.fieldname + '-' + uniqueSuffix + path.extname(file.originalname));
    }
});

// File filter
const fileFilter = (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase().slice(1);
    const allAllowedFormats = [
        ...allowedFormats.images,
        ...allowedFormats.documents,
        ...allowedFormats.archives
    ];
    
    if (allAllowedFormats.includes(ext)) {
        cb(null, true);
    } else {
        cb(new Error('Invalid file format'), false);
    }
};

// Multer configuration with conditional file size limit
const upload = multer({
    storage: storage,
    fileFilter: fileFilter,
    limits: function(req) {
        // No file size limit for enterprise users
        if (req.user && req.user.isEnterprise) {
            return {};
        }
        // 10MB limit for regular users
        return { fileSize: 10 * 1024 * 1024 };
    }
});

// Middleware to check user type (mock implementation)
app.use((req, res, next) => {
    // Mock user authentication - in production, replace with actual auth
    req.user = {
        id: req.headers['user-id'] || '123',
        isEnterprise: req.headers['user-type'] === 'enterprise'
    };
    next();
});

// Generate thumbnail for images
async function generateThumbnail(filePath, filename) {
    const ext = path.extname(filename).toLowerCase().slice(1);
    if (!allowedFormats.images.includes(ext) || ext === 'svg') {
        return null;
    }
    
    try {
        const thumbnailPath = path.join(thumbnailDir, 'thumb_' + filename);
        await sharp(filePath)
            .resize(200, 200, {
                fit: 'cover',
                position: 'center'
            })
            .toFile(thumbnailPath);
        return 'thumb_' + filename;
    } catch (error) {
        console.error('Error generating thumbnail:', error);
        return null;
    }
}

// Upload endpoint
app.post('/upload', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }

        const filePath = req.file.path;
        const filename = req.file.filename;
        const ext = path.extname(filename).toLowerCase().slice(1);
        
        // Determine file type
        let fileType = 'unknown';
        if (allowedFormats.images.includes(ext)) {
            fileType = 'image';
        } else if (allowedFormats.documents.includes(ext)) {
            fileType = 'document';
        } else if (allowedFormats.archives.includes(ext)) {
            fileType = 'archive';
        }

        // Generate thumbnail if it's an image
        let thumbnailName = null;
        if (fileType === 'image') {
            thumbnailName = await generateThumbnail(filePath, filename);
        }

        // Response
        res.json({
            success: true,
            file: {
                filename: filename,
                originalName: req.file.originalname,
                size: req.file.size,
                type: fileType,
                mimeType: req.file.mimetype,
                path: `/uploads/${filename}`,
                thumbnail: thumbnailName ? `/uploads/thumbnails/${thumbnailName}` : null,
                uploadedBy: req.user.id,
                isEnterprise: req.user.isEnterprise,
                uploadedAt: new Date().toISOString()
            }
        });
    } catch (error) {
        console.error('Upload error:', error);
        res.status(500).json({ error: 'File upload failed' });
    }
});

// Upload multiple files endpoint
app.post('/upload-multiple', upload.array('files', 10), async (req, res) => {
    try {
        if (!req.files || req.files.length === 0) {
            return res.status(400).json({ error: 'No files uploaded' });
        }

        const uploadedFiles = [];
        
        for (const file of req.files) {
            const filePath = file.path;
            const filename = file.filename;
            const ext = path.extname(filename).toLowerCase().slice(1);
            
            // Determine file type
            let fileType = 'unknown';
            if (allowedFormats.images.includes(ext)) {
                fileType = 'image';
            } else if (allowedFormats.documents.includes(ext)) {
                fileType = 'document';
            } else if (allowedFormats.archives.includes(ext)) {
                fileType = 'archive';
            }

            // Generate thumbnail if it's an image
            let thumbnailName = null;
            if (fileType === 'image') {
                thumbnailName = await generateThumbnail(filePath, filename);
            }

            uploadedFiles.push({
                filename: filename,
                originalName: file.originalname,
                size: file.size,
                type: fileType,
                mimeType: file.mimetype,
                path: `/uploads/${filename}`,
                thumbnail: thumbnailName ? `/uploads/thumbnails/${thumbnailName}` : null,
                uploadedBy: req.user.id,
                isEnterprise: req.user.isEnterprise,
                uploadedAt: new Date().toISOString()
            });
        }

        res.json({
            success: true,
            files: uploadedFiles
        });
    } catch (error) {
        console.error('Multiple upload error:', error);
        res.status(500).json({ error: 'Multiple file upload failed' });
    }
});

// Serve static files
app.use('/uploads', express.static(uploadDir));

// Error handling middleware
app.use((error, req, res, next) => {
    if (error instanceof multer.MulterError) {
        if (error.code === 'FILE_TOO_LARGE') {
            return res.status(400).json({ error: 'File too large' });
        }
        return res.status(400).json({ error: error.message });
    } else if (error) {
        return res.status(400).json({ error: error.message });
    }
    next();
});

// Start server
app.listen(PORT, () => {
    console.log(`File upload server running on port ${PORT}`);
});