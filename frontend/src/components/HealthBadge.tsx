import { healthBadgeClass } from '@/lib/utils'

interface HealthBadgeProps {
  status: string
  label?: string
}

export default function HealthBadge({ status, label }: HealthBadgeProps) {
  return (
    <span className={healthBadgeClass(status)} data-testid="health-badge">
      {label ?? status}
    </span>
  )
}
