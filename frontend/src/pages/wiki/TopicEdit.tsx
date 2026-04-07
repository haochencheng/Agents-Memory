import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useWikiTopic, useUpdateWikiTopic } from '@/api/useWiki'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

export default function TopicEdit() {
  const { topic = '' } = useParams<{ topic: string }>()
  const navigate = useNavigate()
  const { data, isLoading, error } = useWikiTopic(topic)
  const update = useUpdateWikiTopic(topic)
  const [content, setContent] = useState('')
  const [preview, setPreview] = useState(false)
  const [saveError, setSaveError] = useState('')

  useEffect(() => {
    if (data) {
      const c = data.raw ?? ''
      setContent(c)
    }
  }, [data])

  const handleSave = async () => {
    setSaveError('')
    try {
      await update.mutateAsync(content)
      navigate(`/wiki/${encodeURIComponent(topic)}`)
    } catch {
      setSaveError('保存失败')
    }
  }

  if (isLoading) return <LoadingSpinner text={`加载 ${topic}...`} />
  if (error) return <ErrorAlert message={`加载失败: ${topic}`} />

  return (
    <div className="space-y-4" data-testid="topic-edit-page">
      <div className="flex items-center gap-3">
        <Link to={`/wiki/${encodeURIComponent(topic)}`} className="text-sm text-blue-500 hover:underline">
          ← 返回
        </Link>
        <h1 className="page-title">{topic}</h1>
        <div className="ml-auto flex gap-2">
          <button
            className={`btn text-sm ${preview ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setPreview(v => !v)}
          >
            {preview ? '编辑' : '预览'}
          </button>
          <button
            className="btn btn-primary text-sm"
            onClick={handleSave}
            disabled={update.isPending}
          >
            {update.isPending ? '保存中...' : '保存'}
          </button>
        </div>
      </div>

      {saveError && <ErrorAlert message={saveError} />}

      {preview ? (
        <div className="bg-white rounded-xl border border-gray-100 p-6 min-h-64 prose prose-sm max-w-none">
          <pre className="whitespace-pre-wrap text-sm text-gray-800">{content}</pre>
        </div>
      ) : (
        <textarea
          className="w-full min-h-[480px] rounded-xl border border-gray-200 p-4 font-mono text-sm resize-y focus:outline-none focus:ring-2 focus:ring-blue-300"
          value={content}
          onChange={e => setContent(e.target.value)}
          placeholder="输入 Markdown 内容..."
          data-testid="editor-textarea"
        />
      )}

      <p className="text-xs text-gray-400">
        字数: {content.length} | 行数: {content.split('\n').length}
      </p>
    </div>
  )
}
