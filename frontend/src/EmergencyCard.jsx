import { useEffect, useState } from 'react'
import { getEmergencyCard } from './api'

export default function EmergencyCard({ patientId }) {
  const [card, setCard] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getEmergencyCard(patientId).then(setCard).catch(() => setError('Could not load the card.'))
  }, [patientId])

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (!card) return <p className="text-sm text-gray-500">Loading…</p>

  const call = (number) => `tel:${(number || '').replace(/[^+\d]/g, '')}`

  return (
    <div className="mx-auto max-w-2xl">
      <div className="overflow-hidden rounded-lg border-2 border-red-300 bg-white">
        <div className="bg-red-600 px-5 py-3">
          <h2 className="text-base font-semibold text-white">Emergency medical card</h2>
          <p className="text-xs text-red-100">
            Visible without signing in, so a responder can read it. Minimum information only.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 border-b border-gray-200 px-5 py-4 md:grid-cols-4">
          {[
            ['Name', card.full_name],
            ['Date of birth', card.dob],
            ['Sex', card.sex],
            ['Blood group', card.blood_group],
          ].map(([label, value]) => (
            <div key={label}>
              <div className="text-xs text-gray-500">{label}</div>
              <div className="text-base font-medium text-gray-900">{value || '—'}</div>
            </div>
          ))}
        </div>

        <div className="border-b border-gray-200 px-5 py-4">
          <h3 className="mb-2 text-sm font-semibold text-red-800">Allergies</h3>
          {card.allergies.length === 0 ? (
            <p className="text-sm text-gray-500">None recorded</p>
          ) : (
            <ul className="flex flex-col gap-1">
              {card.allergies.map((a) => (
                <li key={a.id} className="text-sm">
                  <span className="font-medium text-gray-900">{a.substance}</span>
                  <span className="text-gray-600"> — {a.reaction} ({a.severity})</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="border-b border-gray-200 px-5 py-4">
          <h3 className="mb-2 text-sm font-semibold text-gray-900">Active conditions</h3>
          {card.conditions.length === 0 ? (
            <p className="text-sm text-gray-500">None recorded</p>
          ) : (
            <ul className="flex flex-col gap-1 text-sm text-gray-800">
              {card.conditions.map((c) => (
                <li key={c.id}>{c.name}{c.since && ` (since ${c.since})`}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="border-b border-gray-200 px-5 py-4">
          <h3 className="mb-2 text-sm font-semibold text-gray-900">Current medications</h3>
          {card.current_medications.length === 0 ? (
            <p className="text-sm text-gray-500">None recorded</p>
          ) : (
            <ul className="flex flex-col gap-1 text-sm text-gray-800">
              {card.current_medications.map((m, i) => (
                <li key={i}>
                  {m.name}
                  <span className="text-gray-600">
                    {' '}
                    {[m.dose, m.frequency].filter(Boolean).join(', ')}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex flex-col gap-2 px-5 py-4">
          {/* tel: links hand off to the phone's dialler; a person still presses call */}
          <a
            href={call(card.hospital_phone)}
            className="rounded-md bg-red-600 px-4 py-3 text-center text-sm font-semibold text-white"
          >
            Call hospital {card.hospital_phone}
          </a>
          <a
            href={call(card.emergency_contact_phone)}
            className="rounded-md border border-gray-300 px-4 py-3 text-center text-sm font-medium text-gray-800"
          >
            Call {card.emergency_contact_name || 'emergency contact'} {card.emergency_contact_phone}
          </a>
        </div>
      </div>
    </div>
  )
}
