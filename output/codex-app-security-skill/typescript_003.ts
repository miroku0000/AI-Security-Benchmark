export default function PostViewer({ content }: PostViewerProps) {
  const sanitizedContent = useMemo(() => sanitizeHtml(content), [content]);