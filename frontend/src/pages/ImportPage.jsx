import { useRef, useState } from 'react'
import { uploadHandHistories } from '../lib/api.js'

export default function ImportPage() {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleFiles = async (fileList) => {
    const files = Array.from(fileList).filter((f) => f.name.endsWith('.txt'))
    if (files.length === 0) {
      setError('Only .txt hand history files are supported.')
      return
    }
    setError(null)
    setUploading(true)
    setResult(null)
    try {
      const res = await uploadHandHistories(files)
      setResult(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-8 flex flex-col gap-6">
      <header>
        <h1 className="text-xl font-semibold text-slate-100">Import hand histories</h1>
        <p className="text-sm text-slate-500">
          Upload PokerStars or GGPoker (PokerCraft) hand history .txt files. The site is
          detected automatically per file.
        </p>
      </header>

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          handleFiles(e.dataTransfer.files)
        }}
        onClick={() => inputRef.current?.click()}
        className={`rounded-xl border-2 border-dashed px-6 py-12 text-center cursor-pointer transition-colors ${
          dragging ? 'border-cyan-500 bg-cyan-950/20' : 'border-slate-700 bg-slate-900/40'
        }`}
      >
        <p className="text-slate-300 font-medium">Drop .txt files here, or click to choose</p>
        <p className="text-sm text-slate-500 mt-1">Multiple files at once are fine.</p>
        <input
          ref={inputRef}
          type="file"
          accept=".txt"
          multiple
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {uploading && <p className="text-sm text-slate-500">Uploading and parsing…</p>}

      {error && (
        <div className="rounded-xl border border-rose-900 bg-rose-950/40 px-5 py-4 text-sm text-rose-300">
          {error}
        </div>
      )}

      {result && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-5 py-4 flex flex-col gap-2">
          <p className="text-sm text-slate-300 font-medium">
            Imported {result.total_imported} hands, skipped {result.total_duplicates} duplicates.
          </p>
          <ul className="text-sm text-slate-500 flex flex-col gap-1">
            {result.files.map((f, i) => (
              <li key={i}>
                {f.filename}:{' '}
                {f.error ? (
                  <span className="text-rose-400">{f.error}</span>
                ) : (
                  <span>
                    [{f.site}] parsed {f.parsed}, imported {f.imported}, skipped {f.duplicates}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
