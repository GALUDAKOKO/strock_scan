export function formatUpdatedAt(isoString) {
  if (!isoString) return '-'
  const parsed = new Date(isoString)
  if (Number.isNaN(parsed.getTime())) return '-'
  return parsed.toLocaleString()
}
