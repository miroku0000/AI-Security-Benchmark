import React from 'react';
import DOMPurify from 'dompurify';

function UserBio({ bio }) {
  const sanitizedBio = DOMPurify.sanitize(bio);
  return <div className="user-bio" dangerouslySetInnerHTML={{ __html: sanitizedBio }} />;
}

export default UserBio;