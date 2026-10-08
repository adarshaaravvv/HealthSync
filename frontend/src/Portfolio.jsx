import { useEffect, useState } from 'react'
import { saveAllergies, saveConditions, saveProfile } from './api'
import ListEditor from './ListEditor'

function Card({ title, action, children }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b border-gray-200 px-5 py-3">
        <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
        {action}
      </div>
      <div className="px-5 py-3 text-sm">{children}</div>
    </div>
  )
}

const PROFILE_FIELDS = [
  ['full_name', 'Name'],
  ['dob', 'Date of birth'],
  ['sex', 'Sex'],
  ['blood_group', 'Blood group'],
  ['phone', 'Phone'],
  ['emergency_contact_name', 'Emergency contact'],
  ['emergency_contact_phone', 'Contact phone'],
  ['hospital_phone', 'Hospital'],
]

const empty = <p className="text-sm text-gray-400">none recorded</p>

export default function Portfolio({ portfolio, onOpenEncounter, onSaved }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  // rebuild the draft whenever the saved record changes or editing restarts
  useEffect(() => {
    setDraft({
      profile: Object.fromEntries(PROFILE_FIELDS.map(([k]) => [k, portfolio.patient[k] ?? ''])),
      conditions: portfolio.conditions.map((c) => ({ ...c })),
      allergies: portfolio.allergies.map((a) => ({ ...a })),
    })
  }, [portfolio])

  async function save() {
    setBusy(true)
    setError(null)
    try {
      const profile = Object.fromEntries(
        Object.entries(draft.profile).map(([k, v]) => [k, v === '' ? null : v]),
      )
      await saveProfile(profile)
      await saveConditions(
        draft.conditions.map((c) => ({
          name: c.name,
          since: blankToNull(c.since),
          status: c.status || 'active',
          notes: blankToNull(c.notes),
        })),
      )
      await saveAllergies(
        draft.allergies.map((a) => ({
          substance: a.substance,
          reaction: blankToNull(a.reaction),
          severity: a.severity || null,
        })),
      )
      await onSaved()
      setEditing(false)
    } catch (e) {
      setError(readError(String(e.message)))
    } finally {
      setBusy(false)
    }
  }

  if (!draft) return null

  const p = portfolio.patient
  const input = 'w-full rounded border border-gray-300 px-2 py-1 text-sm'
  const btn = 'rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-40'

  const editButton = editing ? (
    <div className="flex gap-2">
      <button className={`${btn} bg-gray-900 text-white`} onClick={save} disabled={busy}>
        {busy ? 'Saving…' : 'Save record'}
      </button>
      <button
        className={`${btn} border border-gray-300 bg-white text-gray-700`}
        onClick={() => {
          setEditing(false)
          setError(null)
        }}
        disabled={busy}
      >
        Cancel
      </button>
    </div>
  ) : (
    <button
      className={`${btn} border border-gray-300 bg-white text-gray-800`}
      onClick={() => setEditing(true)}
    >
      Edit record
    </button>
  )

  return (
    <div className="flex flex-col gap-5">
      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </p>
      )}

      <Card title="Patient" action={editButton}>
        <div className="grid grid-cols-2 gap-x-6 gap-y-3 md:grid-cols-4">
          {PROFILE_FIELDS.map(([key, label]) => (
            <div key={key}>
              <div className="mb-1 text-xs text-gray-500">{label}</div>
              {editing ? (
                <input
                  className={input}
                  value={draft.profile[key]}
                  onChange={(e) =>
                    setDraft({ ...draft, profile: { ...draft.profile, [key]: e.target.value } })
                  }
                />
              ) : (
                <div className="text-gray-900">{p[key] || '—'}</div>
              )}
            </div>
          ))}
        </div>
      </Card>

      <div className="grid gap-5 md:grid-cols-2">
        <Card title="Medical conditions">
          {editing ? (
            <ListEditor
              title=""
              items={draft.conditions}
              blank={{ name: '', since: null, status: 'active', notes: null }}
              fields={[
                { key: 'name', label: 'Condition' },
                { key: 'since', label: 'Since' },
                { key: 'status', label: 'Status', options: ['active', 'resolved'] },
                { key: 'notes', label: 'Notes' },
              ]}
              onChange={(conditions) => setDraft({ ...draft, conditions })}
            />
          ) : portfolio.conditions.length === 0 ? (
            empty
          ) : (
            <ul className="flex flex-col gap-2">
              {portfolio.conditions.map((c) => (
                <li key={c.id} className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-gray-900">{c.name}</div>
                    {c.notes && <div className="text-xs text-gray-500">{c.notes}</div>}
                  </div>
                  <span
                    className={`shrink-0 rounded px-2 py-0.5 text-xs ${
                      c.status === 'active'
                        ? 'bg-amber-50 text-amber-800'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {c.status} {c.since && `· ${c.since}`}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Allergies">
          {editing ? (
            <ListEditor
              title=""
              items={draft.allergies}
              blank={{ substance: '', reaction: null, severity: 'moderate' }}
              fields={[
                { key: 'substance', label: 'Substance' },
                { key: 'reaction', label: 'Reaction' },
                { key: 'severity', label: 'Severity', options: ['mild', 'moderate', 'severe'] },
              ]}
              onChange={(allergies) => setDraft({ ...draft, allergies })}
            />
          ) : portfolio.allergies.length === 0 ? (
            empty
          ) : (
            <ul className="flex flex-col gap-2">
              {portfolio.allergies.map((a) => (
                <li key={a.id} className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-gray-900">{a.substance}</div>
                    <div className="text-xs text-gray-500">{a.reaction}</div>
                  </div>
                  <span
                    className={`shrink-0 rounded px-2 py-0.5 text-xs ${
                      a.severity === 'severe' ? 'bg-red-50 text-red-800' : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {a.severity}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Current medications">
          {portfolio.current_medications.length === 0 ? empty : (
            <ul className="flex flex-col gap-2">
              {portfolio.current_medications.map((m, i) => (
                <li key={i}>
                  <div className="text-gray-900">{m.name}</div>
                  <div className="text-xs text-gray-500">
                    {[m.dose, m.frequency, m.duration, m.instruction].filter(Boolean).join(' · ') || '—'}
                  </div>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-xs text-gray-400">
            Taken from your most recent consultation note, not edited here.
          </p>
        </Card>

        <Card title="Doctors seen">
          {portfolio.doctors_seen.length === 0 ? empty : (
            <ul className="flex flex-col gap-2">
              {portfolio.doctors_seen.map((d) => (
                <li key={d.id}>
                  <div className="text-gray-900">{d.name}</div>
                  <div className="text-xs text-gray-500">
                    {[d.specialty, d.hospital, d.phone].filter(Boolean).join(' · ')}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="Appointments">
        {portfolio.appointments.length === 0 ? empty : (
          <ul className="flex flex-col gap-2">
            {portfolio.appointments.map((a) => (
              <li key={a.id} className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-gray-900">{a.scheduled_for}</div>
                  <div className="text-xs text-gray-500">
                    {[a.reason, a.doctor?.name].filter(Boolean).join(' · ')}
                  </div>
                </div>
                <span className="shrink-0 rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
                  {a.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Consultations">
        {portfolio.encounters.length === 0 ? empty : (
          <ul className="flex flex-col gap-2">
            {portfolio.encounters.map((e) => (
              <li key={e.id} className="flex items-center justify-between gap-3">
                <button
                  className="text-left text-blue-700 hover:underline"
                  onClick={() => onOpenEncounter(e.id)}
                >
                  {e.created_at}
                </button>
                <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">{e.status}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}

const blankToNull = (value) => (value === '' || value === undefined ? null : value)

function readError(message) {
  if (message.startsWith('422')) return 'Check the form: conditions need a name, allergies a substance.'
  if (message.startsWith('401')) return 'Your session expired. Sign in again.'
  return 'Could not save the record.'
}
