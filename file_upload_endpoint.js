const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const sharp = require('sharp');

const router = express.Router();

const uploadDir = 'public/uploads';
const thumbnailDir = 'public/uploads/thumbnails';

if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir, { recursive: true });
}
if (!fs.existsSync(thumbnailDir)) {
    fs.mkdirSync(thumbnailDir, { recursive: true });
}

const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        const ext = path.extname(file.originalname);
        const name = path.basename(file.originalname, ext);
        cb(null, name + '-' + uniqueSuffix + ext);
    }
});

const fileFilter = (req, file, cb) => {
    const allowedFormats = [
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/gif',
        'image/svg+xml',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/zip',
        'application/x-zip-compressed'
    ];
    
    if (allowedFormats.includes(file.mimetype)) {
        cb(null, true);
    } else {
        cb(new Error('Invalid file format. Only jpg, png, gif, svg, pdf, doc, docx, and zip files are allowed.'), false);
    }
};

const upload = multer({
    storage: storage,
    fileFilter: fileFilter,
    limits: (req) => {
        if (req.user && req.user.isEnterprise) {
            return {};
        }
        return { fileSize: 10 * 1024 * 1024 };
    }
});

const generateThumbnail = async (filePath, filename) => {
    const thumbnailPath = path.join(thumbnailDir, 'thumb_' + filename);
    try {
        await sharp(filePath)
            .resize(200, 200, {
                fit: 'inside',
                withoutEnlargement: true
            })
            .toFile(thumbnailPath);
        return 'thumb_' + filename;
    } catch (error) {
        console.error('Error generating thumbnail:', error);
        return null;
    }
};

router.post('/upload', (req, res, next) => {
    const uploadHandler = upload.single('file');
    
    uploadHandler(req, res, async (err) => {
        if (err instanceof multer.MulterError) {
            if (err.code === 'LIMIT_FILE_SIZE') {
                return res.status(413).json({
                    success: false,
                    message: 'File size exceeds the limit for non-enterprise users'
                });
            }
            return res.status(400).json({
                success: false,
                message: err.message
            });
        } else if (err) {
            return res.status(400).json({
                success: false,
                message: err.message
            });
        }
        
        if (!req.file) {
            return res.status(400).json({
                success: false,
                message: 'No file uploaded'
            });
        }
        
        const response = {
            success: true,
            file: {
                filename: req.file.filename,
                originalName: req.file.originalname,
                mimetype: req.file.mimetype,
                size: req.file.size,
                path: `/uploads/${req.file.filename}`
            }
        };
        
        const imageTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
        if (imageTypes.includes(req.file.mimetype)) {
            const thumbnailFilename = await generateThumbnail(req.file.path, req.file.filename);
            if (thumbnailFilename) {
                response.file.thumbnail = `/uploads/thumbnails/${thumbnailFilename}`;
            }
        }
        
        res.json(response);
    });
});

router.post('/upload/multiple', (req, res, next) => {
    const uploadHandler = upload.array('files', 10);
    
    uploadHandler(req, res, async (err) => {
        if (err instanceof multer.MulterError) {
            if (err.code === 'LIMIT_FILE_SIZE') {
                return res.status(413).json({
                    success: false,
                    message: 'File size exceeds the limit for non-enterprise users'
                });
            }
            return res.status(400).json({
                success: false,
                message: err.message
            });
        } else if (err) {
            return res.status(400).json({
                success: false,
                message: err.message
            });
        }
        
        if (!req.files || req.files.length === 0) {
            return res.status(400).json({
                success: false,
                message: 'No files uploaded'
            });
        }
        
        const uploadedFiles = [];
        const imageTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
        
        for (const file of req.files) {
            const fileData = {
                filename: file.filename,
                originalName: file.originalname,
                mimetype: file.mimetype,
                size: file.size,
                path: `/uploads/${file.filename}`
            };
            
            if (imageTypes.includes(file.mimetype)) {
                const thumbnailFilename = await generateThumbnail(file.path, file.filename);
                if (thumbnailFilename) {
                    fileData.thumbnail = `/uploads/thumbnails/${thumbnailFilename}`;
                }
            }
            
            uploadedFiles.push(fileData);
        }
        
        res.json({
            success: true,
            files: uploadedFiles
        });
    });
});

router.delete('/upload/:filename', (req, res) => {
    const filename = req.params.filename;
    const filePath = path.join(uploadDir, filename);
    const thumbnailPath = path.join(thumbnailDir, 'thumb_' + filename);
    
    if (!fs.existsSync(filePath)) {
        return res.status(404).json({
            success: false,
            message: 'File not found'
        });
    }
    
    try {
        fs.unlinkSync(filePath);
        
        if (fs.existsSync(thumbnailPath)) {
            fs.unlinkSync(thumbnailPath);
        }
        
        res.json({
            success: true,
            message: 'File deleted successfully'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Error deleting file'
        });
    }
});

module.exports = router;