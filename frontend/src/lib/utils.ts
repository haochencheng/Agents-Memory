import { clsx, type ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function formatDate(iso: string | undefined | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('zh-CN', {
      year: 'numeric', month: '2-digit', day: '2-digit',
    })
  } catch {
    return iso
  }
}

export function healthBadgeClass(status: string): string {
  switch (status?.toLowerCase()) {
    case 'ok':
    case 'pass':
    case 'active':
    case 'healthy': return 'badge badge-green'
    case 'warn':
    case 'warning': return 'badge badge-yellow'
    case 'fail':
    case 'error':
    case 'failed': return 'badge badge-red'
    default: return 'badge badge-gray'
  }
}
