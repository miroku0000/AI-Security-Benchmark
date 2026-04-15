function getSafeReturnUrl(returnUrl) {
  if (typeof returnUrl !== 'string' || returnUrl.trim() === '') {
    return '/';
  }