// What the badge claims has to match where the work happens, so the mode comes
// from the server's chat_backend rather than from demo mode alone.
const MODES = {
  ollama: {
    dot: 'bg-emerald-500',
    box: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    label: 'On device',
    detail: 'nothing leaves this machine',
  },
  browser: {
    dot: 'bg-amber-500',
    box: 'border-amber-200 bg-amber-50 text-amber-900',
    label: 'In your browser',
    detail: 'speech and notes run on your own device',
  },
  groq: {
    dot: 'bg-red-500',
    box: 'border-red-200 bg-red-50 text-red-900',
    label: 'Sent to Groq',
    detail: 'notes and answers are processed off this device',
  },
}

function ms(value) {
  if (value == null) return null
  return value >= 1000 ? `${(value / 1000).toFixed(1)} s` : `${value} ms`
}

function Mark() {
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gray-900">
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="white" strokeWidth="2"
           strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M3 12h3l2-5 3 10 2.5-7 1.5 4h6" />
      </svg>
    </span>
  )
}

export default function Header({ health, timings, patient, tabs, view, onView, onSignOut }) {
  const mode = MODES[health?.chat_backend] ?? MODES.ollama
  const asr = ms(timings?.asr_ms)
  const llm = ms(timings?.llm_ms)

  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-3 sm:gap-6">
        <div className="flex shrink-0 items-center gap-2.5">
          <Mark />
          <span className="hidden text-[15px] font-semibold tracking-tight text-gray-900 sm:inline">
            HealthSync
          </span>
        </div>

        {/* scrolls rather than pushing the page sideways on a narrow window */}
        <nav className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
          {tabs.map(([key, label]) => (
            <button
              key={key}
              onClick={() => onView(key)}
              className={`shrink-0 rounded-md px-3 py-1.5 text-sm transition-colors ${
                view === key
                  ? 'bg-gray-100 font-medium text-gray-900'
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              {label}
            </button>
          ))}
        </nav>

        {patient && (
          <div className="flex shrink-0 items-center gap-3">
            <span className="hidden text-sm text-gray-700 sm:inline">{patient.full_name}</span>
            <button
              className="rounded-md border border-gray-300 px-2.5 py-1 text-xs text-gray-600 hover:bg-gray-50"
              onClick={onSignOut}
            >
              Sign out
            </button>
          </div>
        )}
      </div>

      {/* the privacy claim and the latency numbers are the pitch, so they get
          their own strip instead of competing with the navigation */}
      <div className="border-t border-gray-100 bg-gray-50/60">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-1.5 px-6 py-1.5">
          <span
            className={`flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${mode.box}`}
            title={mode.detail}
          >
            <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${mode.dot}`} />
            {mode.label}
          </span>

          <span className="text-xs text-gray-500">{mode.detail}</span>

          {(asr || llm) && (
            <span className="ml-auto flex items-center gap-3 font-mono text-xs text-gray-600">
              {asr && <span>speech {asr}</span>}
              {llm && <span>note {llm}</span>}
            </span>
          )}

          <span className={`text-xs text-gray-400 ${asr || llm ? '' : 'ml-auto'}`}>
            {health?.asr_model && `whisper ${health.asr_model}`}
            {health?.llm_model && ` · ${health.llm_model}`}
          </span>
        </div>
      </div>
    </header>
  )
}
