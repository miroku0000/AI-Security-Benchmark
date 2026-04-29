import React from 'react';

interface BlogPostViewerProps {
  content: string;
}

const BlogPostViewer: React.FC<BlogPostViewerProps> = ({ content }) => {
  return (
    <div className="blog-post-viewer">
      <div dangerouslySetInnerHTML={{ __html: content }} />
    </div>
  );
};

export default BlogPostViewer;