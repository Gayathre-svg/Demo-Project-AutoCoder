/*
AutoCoder Dashboard (Final fixed React component)

This file is a safe, environment-agnostic React App component meant for
`src/App.jsx` in a Vite + React project (or other bundlers).

Fixes applied compared to earlier versions:
- Removed any runtime references to the JavaScript token `import` (except the top-level ES import statements required by modules).
- Avoids using `import.meta` anywhere so it will not break in sandboxes that don't support it.
- Uses a global `window.__APP_API_BASE`, `process.env.VITE_API_BASE` fallback, or localStorage to determine backend URL.
- Provides a small UI to submit feature requests to AutoCoder backend and view/download results.

How to use (short):
1. Create a Vite React app (or any React app):
   npm create vite@latest autocoder-dashboard -- --template react
   cd autocoder-dashboard
2. Replace src/App.jsx with this file's content.
3. Optionally add a script in your host HTML to set the backend URL:
   <script>window.__APP_API_BASE = 'http://localhost:9000'</script>
4. npm install && npm run dev

Notes:
- For production, secure the API, use HTTPS, and add authentication.
*/

import React, { useEffect, useState } from 'react'

// Determine default API base without using import.meta or dynamic import token
function getDefaultApiBase() {
  // 1) If an app global is set in the host page (useful in sandboxes)
  try {
    if (typeof window !== 'undefined' && window.__APP_API_BASE) {
      return window.__APP_API_BASE
    }
  } catch (e) {
    // ignore
  }

  // 2) If process.env was injected by a bundler into globalThis
  try {
    if (typeof globalThis !== 'undefined' && globalThis.process && globalThis.process.env && globalThis.process.env.VITE_API_BASE) {
      return globalThis.process.env.VITE_API_BASE
    }
  } catch (e) {
    // ignore
  }

  // 3) sensible local default
  return 'http://localhost:9000'
}

const DEFAULT_API_BASE = getDefaultApiBase()

function PrettyJSON({ data }) {
  return (
    <pre style={{ background: '#0b1220', color: '#d6f8ff', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 320 }}>
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

export default function App() {
  const [apiBase, setApiBase] = useState(() => {
    try {
      return localStorage.getItem('ac_api_base') || DEFAULT_API_BASE
    } catch (e) {
      return DEFAULT_API_BASE
    }
  })
  const [apiBaseInput, setApiBaseInput] = useState(apiBase)

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState(null)
  const [error, setError] = useState(null)
  const [jobs, setJobs] = useState([])
  const [apiToken, setApiToken] = useState('')

  useEffect(() => {
    try {
      const saved = localStorage.getItem('ac_jobs')
      if (saved) setJobs(JSON.parse(saved))
    } catch (e) {
      // ignore
    }
  }, [])

  useEffect(() => {
    try {
      localStorage.setItem('ac_jobs', JSON.stringify(jobs))
    } catch (e) {}
  }, [jobs])

  useEffect(() => {
    try {
      localStorage.setItem('ac_api_base', apiBase)
    } catch (e) {}
  }, [apiBase])

  async function submitFeature(e) {
    e.preventDefault()
    setLoading(true)
    setResponse(null)
    setError(null)

    const payload = { title, description }
    const headers = { 'Content-Type': 'application/json' }
    if (apiToken) headers['Authorization'] = `Bearer ${apiToken}`

    try {
      const endpoint = `${apiBase.replace(/\/$/, '')}/feature_request`
      const res = await fetch(endpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      })

      const contentType = res.headers.get('content-type') || ''
      let data
      if (contentType.includes('application/json')) {
        data = await res.json()
      } else {
        const text = await res.text()
        try {
          data = JSON.parse(text)
        } catch (e) {
          data = { text }
        }
      }

      if (!res.ok) {
        setError(data)
      } else {
        const job = { id: Date.now(), title, created_at: new Date().toISOString(), result: data }
        setJobs((prev) => [job, ...prev].slice(0, 30))
        setResponse(data)
        setTitle('')
        setDescription('')
      }
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  function downloadResult(res) {
    const blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `autocoder_result_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{ fontFamily: 'Inter, system-ui, sans-serif', padding: 24, background: '#f3f6fb', minHeight: '100vh' }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
          <h1 style={{ margin: 0 }}>AutoCoder Dashboard</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ fontSize: 12, color: '#666' }}>Backend: {apiBase}</div>
            <input value={apiBaseInput} onChange={(e) => setApiBaseInput(e.target.value)} style={{ padding: 6, borderRadius: 6, border: '1px solid #e6eef8' }} />
            <button onClick={() => { setApiBase(apiBaseInput); }} style={{ padding: '6px 8px', borderRadius: 6, background: '#eef5ff', border: '1px solid #e6eef8' }}>Set</button>
          </div>
        </header>

        <section style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 16 }}>
          <div>
            <form onSubmit={submitFeature} style={{ background: '#fff', padding: 16, borderRadius: 8, boxShadow: '0 6px 18px rgba(22,34,55,0.06)' }}>
              <label style={{ display: 'block', marginBottom: 6, fontWeight: 600 }}>Feature Title</label>
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder='Add palindrome checker' style={{ width: '100%', padding: 10, marginBottom: 12, borderRadius: 6, border: '1px solid #e6eef8' }} required />

              <label style={{ display: 'block', marginBottom: 6, fontWeight: 600 }}>Description / Requirements</label>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={6} placeholder='Describe behavior, edge cases, and tests' style={{ width: '100%', padding: 10, marginBottom: 12, borderRadius: 6, border: '1px solid #e6eef8' }} required />

              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <button type='submit' disabled={loading} style={{ background: '#0f62fe', color: '#fff', padding: '10px 14px', borderRadius: 6, border: 'none' }}>{loading ? 'Generating...' : 'Submit Feature'}</button>
                <button type='button' onClick={() => { setTitle(''); setDescription(''); setResponse(null); setError(null); }} style={{ padding: '10px 12px', borderRadius: 6, background: '#eef5ff', border: '1px solid #e6eef8' }}>Clear</button>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                  <input value={apiToken} onChange={(e) => setApiToken(e.target.value)} placeholder='Optional API token' style={{ padding: 8, borderRadius: 6, border: '1px solid #e6eef8' }} />
                </div>
              </div>
            </form>

            <div style={{ marginTop: 16 }}>
              <h3 style={{ marginBottom: 8 }}>Latest Result</h3>
              {error && <div style={{ background: '#ffecec', padding: 10, borderRadius: 6, color: '#9c2a2a' }}>{typeof error === 'string' ? error : JSON.stringify(error)}</div>}
              {response ? (
                <div style={{ marginTop: 8 }}>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button onClick={() => downloadResult(response)} style={{ padding: '8px 10px', borderRadius: 6, border: 'none', background: '#12b981', color: '#fff' }}>Download JSON</button>
                    <button onClick={() => navigator.clipboard.writeText(JSON.stringify(response))} style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid #e6eef8', background: '#fff' }}>Copy</button>
                  </div>
                  <div style={{ marginTop: 10 }}>
                    <PrettyJSON data={response} />
                  </div>
                </div>
              ) : (
                <div style={{ background: '#fff', padding: 12, borderRadius: 6, color: '#666' }}>No result yet. Submit a feature to get generated code & tests.</div>
              )}
            </div>
          </div>

          <aside>
            <div style={{ background: '#fff', padding: 12, borderRadius: 8, boxShadow: '0 6px 18px rgba(22,34,55,0.06)' }}>
              <h4 style={{ marginTop: 0 }}>Jobs</h4>
              {jobs.length === 0 && <div style={{ color: '#666' }}>No jobs yet — submit a feature.</div>}
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 8 }}>
                {jobs.map(j => (
                  <li key={j.id} style={{ border: '1px solid #eef5ff', padding: 8, borderRadius: 6 }}>
                    <div style={{ fontWeight: 600 }}>{j.title}</div>
                    <div style={{ fontSize: 12, color: '#888' }}>{new Date(j.created_at).toLocaleString()}</div>
                    <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
                      <button onClick={() => setResponse(j.result)} style={{ padding: '6px 8px', borderRadius: 6, border: 'none', background: '#0f62fe', color: '#fff' }}>View</button>
                      <button onClick={() => downloadResult(j.result)} style={{ padding: '6px 8px', borderRadius: 6, border: '1px solid #e6eef8', background: '#fff' }}>Download</button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            <div style={{ marginTop: 12, background: '#fff', padding: 12, borderRadius: 8 }}>
              <h4 style={{ marginTop: 0 }}>Quick Health</h4>
              <button onClick={async () => {
                try {
                  const r = await fetch(`${apiBase.replace(/\/$/, '')}/health`)
                  const d = await r.json()
                  alert(JSON.stringify(d))
                } catch (e) { alert(String(e)) }
              }} style={{ padding: '8px 10px', borderRadius: 6, background: '#eef5ff', border: '1px solid #e6eef8' }}>Ping Backend</button>

              <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>Store: localStorage (jobs). For production, use a real backend job queue.</div>
            </div>
          </aside>
        </section>

        <footer style={{ marginTop: 20, color: '#999', fontSize: 12 }}>AutoCoder Dashboard — prototype UI. Secure your API in production.</footer>
      </div>
    </div>
  )
}
