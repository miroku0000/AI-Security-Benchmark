const PostViewer: React.FC<PostViewerProps> = ({ content }) => {
  return <div dangerouslySetInnerHTML={{ __html: content }} />;
};