const express = require('express');
const multer = require('multer');
const xml2js = require('xml2js');
const fs = require('fs').promises;
const path = require('path');

const app = express();
const upload = multer({ dest: 'uploads/' });

app.use(express.json());

app.post('/api/xml/upload', upload.single('xmlFile'), async (req, res) => {
    if (!req.file) {
        return res.status(400).json({ error: 'No XML file provided' });
    }

    try {
        const xmlContent = await fs.readFile(req.file.path, 'utf8');
        
        const parser = new xml2js.Parser({
            explicitArray: false,
            mergeAttrs: true,
            resolveEntities: true,
            processDoctype: true,
            parseComments: true,
            xmlns: true,
            strict: false,
            normalizeTags: false,
            preserveChildrenOrder: true,
            attrValueProcessors: [xml2js.processors.parseNumbers, xml2js.processors.parseBooleans],
            valueProcessors: [xml2js.processors.parseNumbers, xml2js.processors.parseBooleans]
        });

        parser.parseString(xmlContent, async (err, result) => {
            if (err) {
                await fs.unlink(req.file.path).catch(() => {});
                return res.status(400).json({ error: 'Invalid XML format', details: err.message });
            }

            await fs.unlink(req.file.path).catch(() => {});

            const configSettings = extractConfigSettings(result);
            
            res.json({
                success: true,
                filename: req.file.originalname,
                size: req.file.size,
                configuration: configSettings,
                rawParsedXml: result
            });
        });
    } catch (error) {
        if (req.file && req.file.path) {
            await fs.unlink(req.file.path).catch(() => {});
        }
        res.status(500).json({ error: 'Processing failed', details: error.message });
    }
});

app.post('/api/xml/parse', express.text({ type: 'application/xml', limit: '10mb' }), (req, res) => {
    if (!req.body) {
        return res.status(400).json({ error: 'No XML content provided' });
    }

    const parser = new xml2js.Parser({
        explicitArray: false,
        mergeAttrs: true,
        resolveEntities: true,
        processDoctype: true,
        parseComments: true,
        xmlns: true,
        strict: false,
        normalizeTags: false,
        preserveChildrenOrder: true,
        attrValueProcessors: [xml2js.processors.parseNumbers, xml2js.processors.parseBooleans],
        valueProcessors: [xml2js.processors.parseNumbers, xml2js.processors.parseBooleans]
    });

    parser.parseString(req.body, (err, result) => {
        if (err) {
            return res.status(400).json({ error: 'Invalid XML format', details: err.message });
        }

        const configSettings = extractConfigSettings(result);
        
        res.json({
            success: true,
            configuration: configSettings,
            rawParsedXml: result
        });
    });
});

function extractConfigSettings(xmlObject) {
    const config = {};
    
    function traverse(obj, currentPath = '') {
        if (typeof obj !== 'object' || obj === null) {
            return obj;
        }

        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                const newPath = currentPath ? `${currentPath}.${key}` : key;
                
                if (key.startsWith('xmlns') || key.startsWith('xsi')) {
                    continue;
                }
                
                if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
                    traverse(obj[key], newPath);
                } else if (Array.isArray(obj[key])) {
                    config[newPath] = obj[key].map(item => 
                        typeof item === 'object' ? traverse(item) : item
                    );
                } else {
                    config[newPath] = obj[key];
                }
            }
        }
        return obj;
    }
    
    traverse(xmlObject);
    
    const rootKey = Object.keys(xmlObject)[0];
    if (rootKey && typeof xmlObject[rootKey] === 'object') {
        const flatConfig = {};
        
        function flattenObject(obj, prefix = '') {
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    const newKey = prefix ? `${prefix}_${key}` : key;
                    
                    if (key.startsWith('xmlns') || key.startsWith('xsi') || key === '_' || key === '$') {
                        continue;
                    }
                    
                    if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
                        flattenObject(obj[key], newKey);
                    } else {
                        flatConfig[newKey] = obj[key];
                    }
                }
            }
        }
        
        flattenObject(xmlObject[rootKey]);
        return flatConfig;
    }
    
    return config;
}

app.get('/api/xml/schema/:filename', async (req, res) => {
    const schemaPath = path.join(__dirname, 'schemas', req.params.filename);
    
    try {
        const schemaContent = await fs.readFile(schemaPath, 'utf8');
        res.type('application/xml').send(schemaContent);
    } catch (error) {
        res.status(404).json({ error: 'Schema not found' });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`XML Parser Service running on port ${PORT}`);
});