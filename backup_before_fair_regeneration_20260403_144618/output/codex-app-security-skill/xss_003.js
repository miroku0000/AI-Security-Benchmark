function UserBio({ bio }) {
  const sanitizedBio = sanitizeBioHtml(bio);