import { useRef, useState } from 'react'
import { importBrowserTranscript, loadSample, uploadAudio } from './api'

export default function AudioInput({ onEncounter, busy, setBusy, demoMode }) {
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState(null)
  const [progress, setProgress] = useState(null)

  // MediaRecorder and its chunks live in refs, not state: changing them must not re-render
  const recorderRef = useRef(null)
  const chunksRef = useRef([])

  async function startRecording() {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []

      recorder.ondataavailable = (e) => chunksRef.current.push(e.data)
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType })

        if (demoMode) {
          await send(() => transcribeHere(blob))
        } else {
          const file = new File([blob], 'recording.webm', { type: recorder.mimeType })
          await send(() => uploadAudio(file, 'mic', null))
        }
      }

      recorder.start()
      recorderRef.current = recorder
      setRecording(true)
    } catch {
      setError('Could not access the microphone. Use upload or the bundled sample.')
    }
  }

  function stopRecording() {
    recorderRef.current?.stop()
    setRecording(false)
  }

  // the host has no speech model, so recordings and uploaded files are both
  // transcribed here and only the text is sent
  async function transcribeHere(blob) {
    setProgress({ percent: 0, label: 'preparing the speech model' })
    try {
      // imported here, not at the top: transformers.js is large and most
      // visitors never transcribe anything
      const { transcribe } = await import('./browserAsr')
      const transcript = await transcribe(blob, (p) =>
        setProgress({ percent: p.percent, label: 'downloading the speech model' }),
      )
      setProgress({ percent: 100, label: 'transcribing' })
      return await importBrowserTranscript(transcript)
    } finally {
      setProgress(null)
    }
  }

  async function send(fn) {
    setBusy(true)
    setError(null)
    try {
      const enc = await fn()
      onEncounter(enc)
    } catch (e) {
      setError(String(e.message))
    } finally {
      setBusy(false)
    }
  }

  const btn = 'rounded-md px-4 py-2 text-sm font-medium disabled:opacity-40'

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <h2 className="mb-4 text-base font-semibold text-gray-900">New consultation</h2>

      {demoMode && (
        <p className="mb-4 rounded bg-amber-50 px-3 py-2 text-xs text-amber-900">
          Recordings and uploaded files are transcribed by a speech model running inside your own
          browser, so the audio never leaves your device. The model downloads once, around 150 MB.
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        {!recording ? (
          <button className={`${btn} bg-gray-900 text-white`} onClick={startRecording} disabled={busy}>
            Start recording
          </button>
        ) : (
          <button className={`${btn} bg-red-600 text-white`} onClick={stopRecording}>
            Stop recording
          </button>
        )}

        <label className={`${btn} cursor-pointer border border-gray-300 bg-white text-gray-800`}>
          Upload .wav / .mp3
          <input
            type="file"
            accept=".wav,.mp3,audio/*"
            className="hidden"
            disabled={busy}
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) send(() => (demoMode ? transcribeHere(f) : uploadAudio(f, 'upload', null)))
              e.target.value = '' // lets the same file be picked twice in a row
            }}
          />
        </label>

        <button
          className={`${btn} border border-gray-300 bg-white text-gray-800`}
          onClick={() => send(loadSample)}
          disabled={busy}
        >
          Load sample consultation
        </button>
      </div>

      {recording && <p className="mt-3 text-sm text-red-600">Recording…</p>}

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

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  )
}
