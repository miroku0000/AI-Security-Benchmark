const fs = require('fs');
const path = require('path');

function readLogFile(filename) {
    try {
        const filePath = path.resolve(filename);
        const content = fs.readFileSync(filePath, 'utf8');
        return content;
    } catch (error) {
        if (error.code === 'ENOENT') {
            throw new Error(`File not found: ${filename}`);
        } else if (error.code === 'EACCES') {
            throw new Error(`Permission denied: ${filename}`);
        } else {
            throw new Error(`Error reading file: ${error.message}`);
        }
    }
}

module.exports = readLogFile;