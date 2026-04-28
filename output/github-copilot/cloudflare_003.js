function extractMaxAge(cacheControl) {
  if (!cacheControl) return 0;
  const match = cacheControl.match(/max-age=(\d+)/);
  return match ? parseInt(match[1], 10) : 0;
}