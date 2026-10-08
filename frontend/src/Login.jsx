import { useState } from 'react'
import { login, register, setToken } from './api'

// shown only on the create-account form; these are what fill the emergency card
const PROFILE_FIELDS = [
  ['full_name', 'Full name', 'text'],
  ['dob', 'Date of birth', 'date'],
  ['blood_group', 'Blood group', 'text'],
  ['phone', 'Phone', 'tel'],
  ['emergency_contact_name', 'Emergency contact', 'text'],
  ['emergency_contact_phone', 'Their phone', 'tel'],
]

const BLANK = {
  username: '',
  password: '',
  full_name: '',
  dob: '',
  sex: '',
  blood_group: '',
  phone: '',
  emergency_contact_name: '',
  emergency_contact_phone: '',
}

export default function Login({ onSignedIn }) {
  const [mode, setMode] = useState('signin')
  const [form, setForm] = useState(BLANK)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const creating = mode === 'create'
  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }))

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      let result
      if (creating) {
        // the API rejects empty strings on optional fields, so send nulls instead
        const details = Object.fromEntries(
          Object.entries(form).map(([k, v]) => [k, v === '' ? null : v]),
        )
        result = await register(details)
      } else {
        result = await login(form.username, form.password)
      }
      setToken(result.token)
      onSignedIn(result.patient)
    } catch (err) {
      setError(readError(String(err.message), creating))
    } finally {
      setBusy(false)
    }
  }

  const input = 'w-full rounded border border-gray-300 px-3 py-2 text-sm'
  const canSubmit = form.username && form.password && (!creating || form.full_name)

  return (
    <div className="mx-auto mt-12 mb-12 max-w-md rounded-lg border border-gray-200 bg-white p-6">
      <h1 className="mb-1 text-lg font-semibold text-gray-900">HealthSync</h1>
      <p className="mb-5 text-sm text-gray-500">
        {creating ? 'Create an account to keep your medical record.' : 'Sign in to see your medical record.'}
      </p>

      <form onSubmit={submit} className="flex flex-col gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-gray-700">Username</span>
          <input className={input} value={form.username} onChange={(e) => set('username', e.target.value)} />
        </label>

        <label className="text-sm">
          <span className="mb-1 block text-gray-700">
            Password {creating && <span className="text-gray-400">(at least 8 characters)</span>}
          </span>
          <input
            className={input}
            type="password"
            value={form.password}
            onChange={(e) => set('password', e.target.value)}
          />
        </label>

        {creating && (
          <>
            {PROFILE_FIELDS.map(([key, label, type]) => (
              <label key={key} className="text-sm">
                <span className="mb-1 block text-gray-700">
                  {label} {key !== 'full_name' && <span className="text-gray-400">(optional)</span>}
                </span>
                <input
                  className={input}
                  type={type}
                  value={form[key]}
                  onChange={(e) => set(key, e.target.value)}
                />
              </label>
            ))}

            <label className="text-sm">
              <span className="mb-1 block text-gray-700">
                Sex <span className="text-gray-400">(optional)</span>
              </span>
              <select className={input} value={form.sex} onChange={(e) => set('sex', e.target.value)}>
                <option value="">Prefer not to say</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other</option>
              </select>
            </label>

            <p className="rounded bg-amber-50 px-3 py-2 text-xs text-amber-900">
              Blood group, allergies and emergency contact appear on your emergency card, which is
              readable without signing in. Leave anything blank that you would rather not share.
            </p>
          </>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          className="mt-1 rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
          disabled={busy || !canSubmit}
        >
          {busy ? 'Please wait…' : creating ? 'Create account' : 'Sign in'}
        </button>
      </form>

      <button
        className="mt-4 w-full text-sm text-blue-700 hover:underline"
        onClick={() => {
          setMode(creating ? 'signin' : 'create')
          setError(null)
        }}
      >
        {creating ? 'I already have an account' : 'Create a new account'}
      </button>

      {!creating && (
        <p className="mt-5 border-t border-gray-100 pt-4 text-xs text-gray-500">
          Demo accounts (fictional): <span className="font-mono">ananya</span>,{' '}
          <span className="font-mono">rohit</span>, <span className="font-mono">meera</span> — password{' '}
          <span className="font-mono">healthsync123</span>
        </p>
      )}
    </div>
  )
}

function readError(message, creating) {
  if (message.startsWith('409')) return 'That username is already taken.'
  if (message.startsWith('422')) {
    return 'Check the form: usernames are 3+ characters (letters, numbers, . _ -) and passwords 8+.'
  }
  if (message.startsWith('401')) return 'Wrong username or password.'
  return creating ? 'Could not create the account.' : 'Could not sign in.'
}
