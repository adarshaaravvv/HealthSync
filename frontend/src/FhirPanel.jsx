import { useState } from 'react'

export default function FhirPanel({ bundle, valid }) {
  const [open, setOpen] = useState(false)

  if (!bundle) return null

  const counts = bundle.entry.reduce((acc, e) => {
    const type = e.resource.resourceType
    acc[type] = (acc[type] || 0) + 1
    return acc
  }, {})

  function download() {
    const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${bundle.id || 'bundle'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b border-gray-200 px-5 py-3">
        <h2 className="text-base font-semibold text-gray-900">FHIR R4 Bundle</h2>
        <div className="flex items-center gap-3">
          <span
            className={`rounded px-2 py-0.5 text-xs ${
              valid ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
            }`}
          >
            {valid ? 'validates' : 'invalid'}
          </span>
          <button className="text-xs text-blue-700 hover:underline" onClick={download}>
            download .json
          </button>
          <button className="text-xs text-blue-700 hover:underline" onClick={() => setOpen(!open)}>
            {open ? 'hide' : 'show'} raw
          </button>
        </div>
      </div>

      <div className="px-5 py-3">
        <div className="flex flex-wrap gap-2">
          {Object.entries(counts).map(([type, n]) => (
            <span key={type} className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-700">
              {type} x{n}
            </span>
          ))}
        </div>

        {open && (
          <pre className="mt-3 max-h-80 overflow-auto rounded bg-gray-900 p-3 text-xs text-gray-100">
            {JSON.stringify(bundle, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}
