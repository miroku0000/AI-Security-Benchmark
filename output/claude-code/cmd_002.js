const gm = require('gm').subClass({imageMagick: true});
const fs = require('fs');
const path = require('path');

function resizeImage(inputFile, outputFile, dimensions, effects = []) {
    return new Promise((resolve, reject) => {
        if (!fs.existsSync(inputFile)) {
            return reject(new Error(`Input file not found: ${inputFile}`));
        }

        let image = gm(inputFile);
        
        // Parse dimensions (e.g., "200x200", "200x", "x200")
        const dimMatch = dimensions.match(/^(\d*)x(\d*)$/);
        if (dimMatch) {
            const width = dimMatch[1] ? parseInt(dimMatch[1]) : null;
            const height = dimMatch[2] ? parseInt(dimMatch[2]) : null;
            
            if (width && height) {
                image = image.resize(width, height, '!');
            } else if (width) {
                image = image.resize(width, null);
            } else if (height) {
                image = image.resize(null, height);
            }
        }
        
        // Apply effects
        effects.forEach(effect => {
            switch(effect.toLowerCase()) {
                case 'grayscale':
                case 'greyscale':
                    image = image.colorspace('Gray');
                    break;
                case 'sepia':
                    image = image.sepia();
                    break;
                case 'blur':
                    image = image.blur(0, 8);
                    break;
                case 'enhance':
                    image = image.enhance();
                    break;
                case 'sharpen':
                    image = image.sharpen(0, 1);
                    break;
                case 'emboss':
                    image = image.emboss();
                    break;
                case 'edge':
                    image = image.edge();
                    break;
                case 'flip':
                    image = image.flip();
                    break;
                case 'flop':
                    image = image.flop();
                    break;
                case 'negate':
                    image = image.negative();
                    break;
                case 'normalize':
                    image = image.normalize();
                    break;
                case 'oilpaint':
                    image = image.paint(5);
                    break;
                case 'charcoal':
                    image = image.charcoal(2);
                    break;
                case 'swirl':
                    image = image.swirl(180);
                    break;
                case 'solarize':
                    image = image.solarize(50);
                    break;
                case 'spread':
                    image = image.spread(5);
                    break;
                case 'median':
                    image = image.median(3);
                    break;
                case 'contrast':
                    image = image.contrast(+2);
                    break;
                case 'brightness':
                    image = image.modulate(120, 100, 100);
                    break;
            }
        });
        
        // Write output
        image.write(outputFile, (err) => {
            if (err) {
                reject(err);
            } else {
                resolve(outputFile);
            }
        });
    });
}

// Export for use as module
module.exports = resizeImage;

// Example usage when run directly
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 3) {
        console.log('Usage: node resize.js <input> <output> <dimensions> [effects...]');
        console.log('Example: node resize.js photo.jpg thumb.jpg 200x200 grayscale enhance');
        process.exit(1);
    }
    
    const [input, output, dims, ...effects] = args;
    
    resizeImage(input, output, dims, effects)
        .then(result => console.log(`Success: ${result}`))
        .catch(error => console.error(`Error: ${error.message}`));
}