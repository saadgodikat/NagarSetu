'use client'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/lib/auth'
import { apiFetch } from '@/lib/api'
import { AppShell } from '@/components/layout/AppShell'
import { Card, CardBody } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Bot } from 'lucide-react'
import '@/lib/i18n/index'

const SUGGESTED_QUESTIONS = [
  'What are the major unresolved problems in Ward 1?',
  'Which department has the highest workload?',
  'Which wards have the most complaints?',
  "Generate today's operational summary.",
  'How many complaints are overdue?',
]

interface AssistantAnswer {
  question: string
  intent: string
  answer: string
  data: Record<string, unknown>
}

export default function AssistantPage() {
  const { t } = useTranslation()
  const { token } = useAuth()
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<AssistantAnswer | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function ask(q?: string) {
    const text = (q ?? question).trim()
    if (!text || !token) return
    setLoading(true)
    setAnswer(null)
    setError('')
    try {
      const res = await apiFetch<AssistantAnswer>('/api/v1/assistant/query', token, {
        method: 'POST',
        body: JSON.stringify({ question: text }),
      })
      setAnswer(res)
    } catch {
      setError(t('error.generic'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppShell>
      <div className="max-w-2xl space-y-5">
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Bot size={22} />
          {t('assistant.title')}
        </h1>

        <Card>
          <CardBody className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder={t('assistant.placeholder')}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && ask()}
                className="flex-1"
              />
              <Button onClick={() => ask()} loading={loading}>
                {t('assistant.ask')}
              </Button>
            </div>

            <div>
              <p className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wide">
                {t('assistant.suggested')}
              </p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => { setQuestion(q); ask(q) }}
                    className="text-xs px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full hover:bg-blue-100 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </CardBody>
        </Card>

        {error && <p className="text-sm text-red-500">{error}</p>}

        {answer && (
          <Card>
            <CardBody>
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">{answer.intent}</p>
              <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">{answer.answer}</p>
            </CardBody>
          </Card>
        )}
      </div>
    </AppShell>
  )
}
