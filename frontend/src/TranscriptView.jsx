import { editSegments } from './api'

function clock(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

const COLORS = {
  doctor: 'bg-blue-50 text-blue-800',
  patient: 'bg-amber-50 text-amber-800',
  unknown: 'bg-gray-100 text-gray-600',
}

export default function TranscriptView({ encounterId, segments, onChange }) {
  if (segments.length === 0) return null

  async function setSpeaker(segmentId, speaker) {
    const updated = await editSegments(encounterId, [{ id: segmentId, speaker }])
    onChange(updated)
  }

  const counts = segments.reduce((acc, s) => {
    acc[s.speaker] = (acc[s.speaker] || 0) + 1
    return acc
  }, {})

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b border-gray-200 px-5 py-3">
        <h2 className="text-base font-semibold text-gray-900">Transcript</h2>
        <span className="text-xs text-gray-500">
          {segments.length} segments · {counts.doctor || 0} doctor · {counts.patient || 0} patient
        </span>
      </div>

      <ul className="max-h-[420px] overflow-y-auto">
        {segments.map((s) => (
          <li key={s.id} className="flex gap-3 border-b border-gray-100 px-5 py-2 text-sm last:border-0">
            <span className="w-10 shrink-0 pt-1 font-mono text-xs text-gray-400">
              {clock(s.start_s)}
            </span>

            <select
              value={s.speaker || 'unknown'}
              onChange={(e) => setSpeaker(s.id, e.target.value)}
              className={`h-6 shrink-0 rounded px-1 text-xs ${COLORS[s.speaker] || COLORS.unknown}`}
            >
              <option value="doctor">Doctor</option>
              <option value="patient">Patient</option>
              <option value="unknown">Unknown</option>
            </select>

            <span className="text-gray-800">
              {s.text}
              {s.edited === 1 && <span className="ml-2 text-xs text-gray-400">edited</span>}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
