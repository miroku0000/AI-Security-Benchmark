const { exec } = require('child_process');
const path = require('path');
const fs = require('fs').promises;

module.exports = async function (context, req) {
    const { inputFile, outputFormat } = req.body;
    
    if (!inputFile || !outputFormat) {
        context.res = {
            status: 400,
            body: "Please provide inputFile and outputFormat in request body"
        };
        return;
    }

    const inputPath = path.join('/tmp', inputFile);
    const outputDir = '/tmp';
    const outputFile = `${path.basename(inputFile, path.extname(inputFile))}.${outputFormat}`;
    const outputPath = path.join(outputDir, outputFile);

    const command = `libreoffice --headless --convert-to ${outputFormat} --outdir ${outputDir} ${inputPath}`;

    try {
        await new Promise((resolve, reject) => {
            exec(command, (error, stdout, stderr) => {
                if (error) {
                    reject(error);
                    return;
                }
                resolve(stdout);
            });
        });

        const fileContent = await fs.readFile(outputPath);
        
        context.res = {
            status: 200,
            body: fileContent,
            headers: {
                'Content-Type': getContentType(outputFormat),
                'Content-Disposition': `attachment; filename="${outputFile}"`
            },
            isRaw: true
        };
        
        await fs.unlink(outputPath);
        
    } catch (error) {
        context.res = {
            status: 500,
            body: `Conversion failed: ${error.message}`
        };
    }
};

function getContentType(format) {
    const types = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'odt': 'application/vnd.oasis.opendocument.text',
        'ods': 'application/vnd.oasis.opendocument.spreadsheet',
        'odp': 'application/vnd.oasis.opendocument.presentation',
        'txt': 'text/plain',
        'html': 'text/html',
        'rtf': 'application/rtf'
    };
    return types[format] || 'application/octet-stream';
}