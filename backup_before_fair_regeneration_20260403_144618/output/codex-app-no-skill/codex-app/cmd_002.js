async function findCommand() {
  const candidates = [
    { cmd: 'magick', mode: 'imagemagick' },
    { cmd: 'gm', mode: 'graphicsmagick' },
    { cmd: 'convert', mode: 'imagemagick-legacy' }
  ];