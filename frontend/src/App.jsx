import { useEffect, useState } from 'react'
import {
  clearToken,
  deleteEncounter,
  generateNote,
  getEncounter,
  getHealth,
  getPortfolio,
  getPrompts,
  getToken,
  importBrowserNote,
  listEncounters,
  logout,
  saveNote,
  transcribeEncounter,
} from './api'
import Header from './Header'
import Login from './Login'
import Portfolio from './Portfolio'
import Chat from './Chat'
import EmergencyCard from './EmergencyCard'
import AudioInput from './AudioInput'
import EncounterPanel from './EncounterPanel'
import EncounterList from './EncounterList'
import TranscriptView from './TranscriptView'
import NoteEditor from './NoteEditor'
import FhirPanel from './FhirPanel'

const TABS = [
  ['scribe', 'Consultation'],
  ['portfolio', 'My record'],
  ['chat', 'Ask HealthSync'],
  ['emergency', 'Emergency card'],
]

// #emergency/3 opens the card with no sign-in, the way a phone lock screen would
function emergencyIdFromHash(hash) {
  const match = hash.match(/^#emergency\/(\d+)$/)
  return match ? Number(match[1]) : null
}

export default function App() {
  const [health, setHealth] = useState(null)
  const [patient, setPatient] = useState(null)
  const [checking, setChecking] = useState(true)
  const [view, setView] = useState('scribe')

  const [portfolio, setPortfolio] = useState(null)
  const [encounters, setEncounters] = useState([])
  const [current, setCurrent] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [llmProgress, setLlmProgress] = useState(null)

  // hash changes do not remount the app, so track it as state
  const [hash, setHash] = useState(window.location.hash)
  const publicEmergencyId = emergencyIdFromHash(hash)

  useEffect(() => {
    const onHashChange = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null))

    if (!getToken()) {
      setChecking(false)
      return
    }
    getPortfolio()
      .then((p) => {
        setPortfolio(p)
        setPatient(p.patient)
      })
      .catch(() => clearToken())
      .finally(() => setChecking(false))
  }, [])

  useEffect(() => {
    if (patient) refreshList()
  }, [patient])

  async function refreshList() {
    setEncounters(await listEncounters())
  }

  async function refreshPortfolio() {
    setPortfolio(await getPortfolio())
  }

  async function selectEncounter(id) {
    setView('scribe')
    setCurrent(await getEncounter(id))
  }

  // every long-running action goes through here, so one place owns busy and error
  async function run(action) {
    setBusy(true)
    setError(null)
    try {
      setCurrent(await action())
      await refreshList()
      await refreshPortfolio()
    } catch (e) {
      setError(String(e.message))
    } finally {
      setBusy(false)
    }
  }

  // locally the server has Ollama; on the hosted demo the model runs in the browser
  async function handleGenerateNote(model) {
    // the server handles it unless the hosted demo has no model of its own,
    // in which case it runs on the visitor's GPU
    if (health?.chat_backend !== 'browser') {
      return run(() => generateNote(current.id, model))
    }

    await run(async () => {
      const llm = await import('./browserLlm')
      const supported = await llm.support()
      if (!supported.ok) {
        throw new Error(
          `${supported.reason} You can still open the bundled sample consultation, ` +
            'which comes with a note already generated.',
        )
      }

      setLlmProgress({ percent: 0, label: 'starting the model' })
      try {
        const prompts = await getPrompts()
        const transcript = current.segments.map((s) => `${s.speaker}: ${s.text}`).join('\n')
        const result = await llm.generateNote(prompts, transcript, setLlmProgress)
        return await importBrowserNote(current.id, result.note, result.llm_ms, result.model)
      } finally {
        setLlmProgress(null)
      }
    })
  }

  async function handleSignOut() {
    await logout().catch(() => {})
    clearToken()
    setPatient(null)
    setPortfolio(null)
    setCurrent(null)
    setEncounters([])
  }

  if (publicEmergencyId) {
    return (
      <div className="min-h-screen p-6">
        <EmergencyCard patientId={publicEmergencyId} />
      </div>
    )
  }

  if (checking) return <p className="p-6 text-sm text-gray-500">Loading…</p>
  if (!patient) return <Login onSignedIn={(p) => { setPatient(p); refreshPortfolio() }} />

  return (
    <div className="min-h-screen">
      <Header
        health={health}
        timings={current}
        patient={patient}
        tabs={TABS}
        view={view}
        onView={setView}
        onSignOut={handleSignOut}
      />

      <div className="mx-auto max-w-6xl p-6">
        {view === 'portfolio' && portfolio && (
          <Portfolio
            portfolio={portfolio}
            onOpenEncounter={selectEncounter}
            onSaved={refreshPortfolio}
          />
        )}

        {view === 'chat' && <Chat demoMode={health?.demo_mode} backend={health?.chat_backend} />}

        {view === 'emergency' && <EmergencyCard patientId={patient.id} />}

        {view === 'scribe' && (
          <div className="grid gap-5 md:grid-cols-[1fr_340px]">
            <div className="flex flex-col gap-5">
              <AudioInput
                onEncounter={async (enc) => {
                  await refreshList()
                  await selectEncounter(enc.id)
                }}
                busy={busy}
                setBusy={setBusy}
                demoMode={health?.demo_mode}
              />

              {error && (
                <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                  {error}
                </p>
              )}

              {current && (
                <>
                  <EncounterPanel
                    encounter={current}
                    busy={busy}
                    onTranscribe={() => run(() => transcribeEncounter(current.id))}
                    onGenerateNote={handleGenerateNote}
                    demoMode={health?.demo_mode}
                    backend={health?.chat_backend}
                    progress={llmProgress}
                  />
                  <TranscriptView
                    encounterId={current.id}
                    segments={current.segments}
                    onChange={(segments) => setCurrent({ ...current, segments })}
                  />
                  {current.note && (
                    <NoteEditor
                      note={current.note}
                      reviewed={current.reviewed}
                      busy={busy}
                      onSave={(note) => run(() => saveNote(current.id, note))}
                    />
                  )}
                  <FhirPanel bundle={current.fhir_bundle} valid={current.fhir_valid} />
                </>
              )}
            </div>

            <EncounterList
              encounters={encounters}
              selectedId={current?.id}
              onSelect={selectEncounter}
              onDelete={async (id) => {
                await deleteEncounter(id)
                if (current?.id === id) setCurrent(null)
                await refreshList()
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}
