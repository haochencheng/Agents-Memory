export function extractWikiPreview(raw: string, maxLength = 150) {
  const withoutFrontmatter = raw.replace(/^---[\s\S]*?---\s*/m, '')
  const flattened = withoutFrontmatter
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[\[([^\]]+)\]\]/g, '$1')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1')
    .replace(/[*_>#-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  if (!flattened) return ''
  if (flattened.length <= maxLength) return flattened
  return `${flattened.slice(0, maxLength - 1).trim()}…`
}
