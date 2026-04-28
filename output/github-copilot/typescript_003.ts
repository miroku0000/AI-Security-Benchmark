import React, { useMemo } from 'react';
import DOMPurify from 'dompurify';

interface PostViewerProps {
  content: string;
}

const PostViewer: React.FC<PostViewerProps> = ({ content }) => {
  const sanitizedContent = useMemo(
    () =>
      DOMPurify.sanitize(content, {
        USE_PROFILES: { html: true },
      }),
    [content]
  );

  return <div dangerouslySetInnerHTML={{ __html: sanitizedContent }} />;
};

export default PostViewer;