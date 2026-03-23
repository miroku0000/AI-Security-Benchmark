export default function UserBio({ bio = "", className = "" }) {
  const sanitizedBio = useMemo(() => sanitizeBioHtml(bio), [bio]);