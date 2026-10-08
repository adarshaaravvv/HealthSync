import { pipeline } from '@huggingface/transformers'

// Whisper running in the visitor's own browser. The recording is decoded and
// transcribed here; only the resulting text is ever sent to the server.
const MODEL = 'Xenova/whisper-tiny.en'

let transcriber = null

export function isLoaded() {
  return transcriber !== null
}

async function load(onProgress) {
  if (transcriber) return transcriber
  transcriber = await pipeline('automatic-speech-recognition', MODEL, {
    dtype: 'fp32',
    progress_callback: (p) => {
      // the callback fires for each file; report the download ones
      if (p.status === 'progress' && p.total) {
        onProgress?.({ percent: Math.round((p.loaded / p.total) * 100), file: p.file })
      } else if (p.status === 'ready') {
        onProgress?.({ percent: 100, file: null })
      }
    },
  })
  return transcriber
}

// AudioContext resamples to whatever rate it was constructed with, which is the
// 16 kHz mono whisper expects
async function decodeTo16k(blob) {
  const bytes = await blob.arrayBuffer()
  const ctx = new AudioContext({ sampleRate: 16000 })
  try {
    const decoded = await ctx.decodeAudioData(bytes)
    return decoded.getChannelData(0)
  } finally {
    ctx.close()
  }
}

export async function transcribe(blob, onProgress) {
  const model = await load(onProgress)
  const audio = await decodeTo16k(blob)

  const started = performance.now()
  const result = await model(audio, {
    return_timestamps: true,
    chunk_length_s: 30,
    stride_length_s: 5,
  })
  const asrMs = Math.round(performance.now() - started)

  const chunks = result.chunks?.length
    ? result.chunks
    : [{ timestamp: [0, audio.length / 16000], text: result.text }]

  const segments = chunks
    .map((c) => ({
      start_s: Number((c.timestamp?.[0] ?? 0).toFixed(2)),
      // the final chunk sometimes has a null end timestamp
      end_s: Number((c.timestamp?.[1] ?? audio.length / 16000).toFixed(2)),
      text: (c.text || '').trim(),
    }))
    .filter((s) => s.text)

  return {
    segments,
    language: 'en',
    duration_s: Number((audio.length / 16000).toFixed(2)),
    asr_ms: asrMs,
    asr_model: `${MODEL.split('/')[1]} (browser)`,
  }
}
