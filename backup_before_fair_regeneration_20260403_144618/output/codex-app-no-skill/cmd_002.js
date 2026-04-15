function resizeImage(inputFile, outputFile, dimensions, effects = []) {
  return new Promise((resolve, reject) => {
    const match = String(dimensions).match(/^(\d+)x(\d+)$/i);