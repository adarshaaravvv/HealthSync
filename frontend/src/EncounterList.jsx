export default function EncounterList({ encounters, selectedId, onSelect, onDelete }) {
  if (encounters.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-5 text-sm text-gray-500">
        No encounters yet.
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <h2 className="border-b border-gray-200 px-5 py-3 text-base font-semibold text-gray-900">
        Past encounters
      </h2>
      <ul>
        {encounters.map((e) => (
          <li
            key={e.id}
            onClick={() => onSelect(e.id)}
            className={`flex cursor-pointer items-center gap-3 border-b border-gray-100 px-5 py-3 text-sm last:border-0 hover:bg-gray-50 ${
              e.id === selectedId ? 'bg-gray-50' : ''
            }`}
          >
            <div className="flex-1">
              <div className="font-medium text-gray-900">
                {e.patient_label || `Encounter ${e.id}`}
              </div>
              <div className="text-xs text-gray-500">
                {e.created_at} · {e.source} · {e.duration_s ? `${e.duration_s}s` : '—'}
              </div>
            </div>
            <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">{e.status}</span>
            <button
              className="text-xs text-gray-400 hover:text-red-600"
              onClick={(ev) => {
                ev.stopPropagation() // otherwise the row's onSelect fires too
                onDelete(e.id)
              }}
            >
              delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
