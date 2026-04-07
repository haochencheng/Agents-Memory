import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: number | string
  icon?: React.ReactNode
  trend?: 'up' | 'down' | 'neutral'
  className?: string
}

export default function StatCard({ label, value, icon, className }: StatCardProps) {
  return (
    <div className={cn('stat-card', className)} data-testid="stat-card">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-500 font-medium">{label}</span>
        {icon && <span className="text-gray-400">{icon}</span>}
      </div>
      <div className="text-3xl font-bold text-gray-900">{value}</div>
    </div>
  )
}
