// Generic editor for the repeating parts of the note (symptoms, vitals, and so on).
// `fields` describes the columns: { key, label, options? }. options turns it into a select.
export default function ListEditor({ title, items, fields, blank, onChange }) {
  function updateItem(index, key, value) {
    onChange(items.map((item, i) => (i === index ? { ...item, [key]: value } : item)))
  }

  function removeItem(index) {
    onChange(items.filter((_, i) => i !== index))
  }

  const input = 'w-full rounded border border-gray-300 px-2 py-1 text-sm'

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-900">{title}</h4>
        <button
          className="text-xs text-blue-700 hover:underline"
          onClick={() => onChange([...items, { ...blank }])}
        >
          + add
        </button>
      </div>

      {items.length === 0 && <p className="mb-2 text-xs text-gray-400">none recorded</p>}

      <div className="flex flex-col gap-2">
        {items.map((item, index) => (
          <div key={index} className="flex items-start gap-2 rounded border border-gray-200 p-2">
            <div className="grid flex-1 gap-2" style={{ gridTemplateColumns: `repeat(${fields.length}, minmax(0, 1fr))` }}>
              {fields.map((field) => (
                <label key={field.key} className="text-xs text-gray-500">
                  {field.label}
                  {field.options ? (
                    <select
                      className={input}
                      value={item[field.key] ?? ''}
                      onChange={(e) => updateItem(index, field.key, e.target.value)}
                    >
                      {field.options.map((o) => (
                        <option key={o} value={o}>{o}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      className={input}
                      value={item[field.key] ?? ''}
                      onChange={(e) => updateItem(index, field.key, e.target.value || null)}
                    />
                  )}
                </label>
              ))}
            </div>
            <button
              className="mt-4 text-xs text-gray-400 hover:text-red-600"
              onClick={() => removeItem(index)}
            >
              remove
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
