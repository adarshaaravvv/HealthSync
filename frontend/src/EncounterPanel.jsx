import { Fragment, useState } from 'react'

const MODELS = ['llama3.2:3b', 'qwen2.5:7b']

export default function EncounterPanel({ encounter, busy, onTranscribe, onGenerateNote, demoMode, backend, progress }) {
  const [model, setModel] = useState(MODELS[0])

  const rows = [
    ['Source', encounter.source],
    ['Duration', encounter.duration_s ? `${encounter.duration_s} s` : '—'],
    ['Status', encounter.status],
    ['Segments', encounter.segments.length],
  ]

  const hasTranscript = encounter.segments.length > 0
  const btn = 'rounded-md px-4 py-2 text-sm font-medium disabled:opacity-40'

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <h2 className="mb-3 text-base font-semibold text-gray-900">
        {encounter.patient_label || `Encounter ${encounter.id}`}
      </h2>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
        {rows.map(([name, value]) => (
          <Fragment key={name}>
            <dt className="text-gray-500">{name}</dt>
            <dd className="text-gray-900">{value}</dd>
          </Fragment>
        ))}
      </dl>

      {/* the two stages are separated on purpose: the model picker sits beside the
          note button because it chooses the note model, not the speech one */}
      <div className="mt-4 flex flex-wrap items-end gap-x-6 gap-y-3">
        <div>
          <p className="mb-1 text-xs text-gray-500">1. Speech to text</p>
          <button className={`${btn} bg-gray-900 text-white`} onClick={onTranscribe} disabled={busy}>
            {hasTranscript ? 'Re-transcribe' : 'Transcribe'}
          </button>
        </div>

        <div>
          <p className="mb-1 text-xs text-gray-500">2. Text to clinical note</p>
          <div className="flex items-center gap-2">
            <button
              className={`${btn} border border-gray-300 bg-white text-gray-800`}
              onClick={() => onGenerateNote(model)}
              disabled={busy || !hasTranscript}
            >
              {encounter.note ? 'Regenerate note' : 'Generate note'}
            </button>

            {/* the 7B model is slower but catches medications the 3B one drops */}
            {!demoMode && (
              <select
                className="rounded border border-gray-300 px-2 py-2 text-sm"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                disabled={busy}
                title="Which model writes the note. Speech recognition always uses whisper."
              >
                {MODELS.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            )}
          </div>
        </div>
      </div>

      {backend === 'browser' && (
        <p className="mt-3 text-xs text-gray-500">
          The note is written by a small model running on your own graphics card through the
          browser. It downloads once, about 1 GB, and needs Chrome or Edge.
        </p>
      )}

      {backend === 'groq' && (
        <p className="mt-3 rounded bg-red-50 px-3 py-2 text-xs text-red-900">
          On this hosted demo the transcript is sent to Groq, an outside company, to be turned
          into a note. Run HealthSync on your own machine to keep it local.
        </p>
      )}

      {progress && (
        <div className="mt-3">
          <p className="mb-1 text-sm text-gray-700">
            {progress.label}
            {progress.percent > 0 && progress.percent < 100 ? ` — ${progress.percent}%` : '…'}
          </p>
          <div className="h-1.5 w-full overflow-hidden rounded bg-gray-200">
            <div className="h-full bg-gray-900 transition-all" style={{ width: `${progress.percent}%` }} />
          </div>
        </div>
      )}
    </div>
  )
}
