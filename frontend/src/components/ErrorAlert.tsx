interface ErrorAlertProps {
  message?: string
}

export default function ErrorAlert({ message = '请求失败，请稍后重试' }: ErrorAlertProps) {
  return (
    <div
      className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm"
      data-testid="error-alert"
    >
      ⚠ {message}
    </div>
  )
}
