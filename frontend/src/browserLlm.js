// A small language model running on the visitor's own GPU through WebGPU.
// Used only by the hosted demo, where there is no Ollama. The prompts come from
// the server so prompts.py stays the single place the wording is edited.
const MODEL = 'Qwen2.5-1.5B-Instruct-q4f16_1-MLC'

let engine = null

export async function support() {
  if (!('gpu' in navigator)) {
    return { ok: false, reason: 'This browser has no WebGPU. Chrome or Edge on a desktop can run it.' }
  }
  try {
    // ask for the discrete card: browsers default to the integrated GPU, which
    // makes generation several times slower on a laptop that has both
    const adapter = await navigator.gpu.requestAdapter({ powerPreference: 'high-performance' })
    if (!adapter) {
      return { ok: false, reason: 'No graphics adapter available for WebGPU on this device.' }
    }
    if (!adapter.features.has('shader-f16')) {
      return { ok: false, reason: 'This graphics adapter is missing shader-f16, which the model needs.' }
    }
    return { ok: true }
  } catch (e) {
    return { ok: false, reason: `WebGPU could not start: ${e.message}` }
  }
}

export function isLoaded() {
  return engine !== null
}

async function load(onProgress) {
  if (engine) return engine
  const webllm = await import('@mlc-ai/web-llm')
  engine = await webllm.CreateMLCEngine(MODEL, {
    initProgressCallback: (r) =>
      onProgress?.({ percent: Math.round((r.progress ?? 0) * 100), label: r.text || 'loading the model' }),
  })
  return engine
}

function stripFences(text) {
  const trimmed = text.trim()
  if (!trimmed.startsWith('```')) return trimmed
  return trimmed.slice(trimmed.indexOf('\n') + 1).replace(/```$/, '').trim()
}

export async function generateNote(prompts, transcriptText, onProgress) {
  const model = await load(onProgress)
  onProgress?.({ percent: 100, label: 'writing the note' })

  const messages = [
    { role: 'system', content: prompts.note_system },
    { role: 'user', content: prompts.note_user.replace('{transcript}', transcriptText) },
  ]

  const started = performance.now()
  let lastError = null

  // same shape as the server's retry loop: hand the validation error back once
  for (let attempt = 0; attempt < 2; attempt++) {
    const turns = lastError
      ? [...messages, { role: 'user', content: prompts.retry.replace('{error}', lastError) }]
      : messages

    const reply = await model.chat.completions.create({
      messages: turns,
      temperature: 0,
      max_tokens: 1600,
      response_format: { type: 'json_object' },
    })

    try {
      const draft = JSON.parse(stripFences(reply.choices[0].message.content))
      if (!draft.soap || !draft.entities) throw new Error('missing soap or entities')
      return {
        note: {
          soap: {
            subjective: draft.soap.subjective ?? '',
            objective: draft.soap.objective ?? '',
            assessment: draft.soap.assessment ?? '',
            plan: draft.soap.plan ?? '',
          },
          entities: {
            chief_complaint: draft.entities.chief_complaint ?? null,
            symptoms: draft.entities.symptoms ?? [],
            vitals: draft.entities.vitals ?? [],
            diagnoses: draft.entities.diagnoses ?? [],
            medications: draft.entities.medications ?? [],
            follow_up: draft.entities.follow_up ?? null,
          },
          med_instructions: [],
        },
        llm_ms: Math.round(performance.now() - started),
        model: `${MODEL} (browser)`,
      }
    } catch (e) {
      lastError = String(e.message).slice(0, 400)
    }
  }

  throw new Error(`the browser model did not return a usable note: ${lastError}`)
}

export async function chat(prompts, record, history, onProgress) {
  const model = await load(onProgress)
  onProgress?.({ percent: 100, label: 'thinking' })

  const started = performance.now()
  const reply = await model.chat.completions.create({
    messages: [{ role: 'system', content: prompts.chat_system.replace('{record}', record) }, ...history],
    temperature: 0.3,
    max_tokens: 500,
  })

  return {
    reply: reply.choices[0].message.content.trim(),
    llm_ms: Math.round(performance.now() - started),
  }
}
