import React from "react";

export interface PostViewerProps {
  content: string;
}

export function PostViewer({ content }: PostViewerProps): React.JSX.Element {
  return (
    <article
      className="post-viewer"
      dangerouslySetInnerHTML={{ __html: content }}
    />
  );
}
