import { useState } from 'react'
import { getChatContext, getPrompts, sendChat } from './api'

const SUGGESTIONS = [
  'What did the doctor say is wrong with me?',
  'When do I take my medicines?',
  'Am I allergic to anything?',
  'What happens at my next appointment?',
]

export default function Chat({ demoMode, backend }) {
  const inBrowser = backend === 'browser'
  const [history, setHistory] = useState([])
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)

  async function ask(text) {
    if (!text.trim() || busy) return
    setBusy(true)
    setError(null)
    setMessage('')

    const next = [...history, { role: 'user', content: text }]
    setHistory(next)

    try {
      const reply = inBrowser ? await askInBrowser(next) : await sendChat(text, history)
      setHistory([...next, { role: 'assistant', content: reply.reply }])
    } catch (e) {
      setError(String(e.message))
    } finally {
      setBusy(false)
      setProgress(null)
    }
  }

  // on the hosted demo there is no Ollama, so the model runs on the visitor's GPU
  async function askInBrowser(turns) {
    const llm = await import('./browserLlm')
    const supported = await llm.support()
    if (!supported.ok) {
      return {
        reply:
          `${supported.reason}\n\nThe assistant needs a language model, and this hosted demo ` +
          'has none of its own. Your record, the consultation note and the emergency card are ' +
          'all still real.\n\nTo use it, run HealthSync on your own machine:\n' +
          'https://github.com/your-username/healthsync',
      }
    }

    setProgress({ percent: 0, label: 'starting the model' })
    const [prompts, context] = [await getPrompts(), await getChatContext()]
    return llm.chat(prompts, context.record, turns, setProgress)
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <div className="rounded-lg border border-gray-200 bg-white">
        <div className="border-b border-gray-200 px-5 py-3">
          <h2 className="text-base font-semibold text-gray-900">Ask about your record</h2>
          <p className="text-xs text-gray-500">
            Answers come only from your own record. This is not a doctor and cannot prescribe.
          </p>
        </div>

        <div className="flex min-h-[280px] flex-col gap-3 px-5 py-4">
          {inBrowser && (
            <p className="rounded bg-amber-50 px-3 py-2 text-xs text-amber-900">
              The model runs on your own graphics card through the browser, so nothing you type
              leaves this device. It downloads once, about 1 GB, and needs Chrome or Edge. On your
              own machine HealthSync uses a larger model instead:{' '}
              <a
                className="font-medium underline"
                href="https://github.com/your-username/healthsync"
                target="_blank"
                rel="noreferrer"
              >
                github.com/your-username/healthsync
              </a>
            </p>
          )}

          {backend === 'groq' && (
            <p className="rounded bg-red-50 px-3 py-2 text-xs text-red-900">
              On this hosted demo your question and your medical record are sent to Groq, an
              outside company, to be answered. Nothing is stored there, but the data does leave
              this server. Run HealthSync on your own machine to keep everything local.
            </p>
          )}

          {history.length === 0 && (
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  className="rounded-full border border-gray-300 px-3 py-1 text-xs text-gray-700 hover:bg-gray-50"
                  onClick={() => ask(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {history.map((turn, i) => (
            <div
              key={i}
              className={`max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                turn.role === 'user'
                  ? 'self-end bg-gray-900 text-white'
                  : 'self-start bg-gray-100 text-gray-900'
              }`}
            >
              {turn.content}
            </div>
          ))}

          {progress && (
            <div className="self-start">
              <p className="mb-1 text-sm text-gray-500">
                {progress.label}
                {progress.percent > 0 && progress.percent < 100 ? ` — ${progress.percent}%` : '…'}
              </p>
              <div className="h-1.5 w-48 overflow-hidden rounded bg-gray-200">
                <div className="h-full bg-gray-900 transition-all" style={{ width: `${progress.percent}%` }} />
              </div>
            </div>
          )}

          {busy && !progress && <p className="self-start text-sm text-gray-400">thinking…</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        <form
          className="flex gap-2 border-t border-gray-200 px-5 py-3"
          onSubmit={(e) => {
            e.preventDefault()
            ask(message)
          }}
        >
          <input
            className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
            placeholder="Ask a question about your record"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <button
            className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
            disabled={busy || !message.trim()}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  )
}
