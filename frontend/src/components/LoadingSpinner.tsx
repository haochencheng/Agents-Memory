interface LoadingSpinnerProps {
  text?: string
}

export default function LoadingSpinner({ text = '加载中...' }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-gray-400" data-testid="loading-spinner">
      <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      <span className="text-sm">{text}</span>
    </div>
  )
}
