import { useEffect, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [text, setText] = useState('')
  const [graph, setGraph] = useState(null)

  const loadGraph = async () => {
    const res = await fetch(`${API_URL}/graph`)
    const data = await res.json()
    setGraph(data)
  }

  const ingest = async () => {
    await fetch(`${API_URL}/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    })
    setText('')
    loadGraph()
  }

  useEffect(() => {
    loadGraph()
  }, [])

  return (
    <div>
      <h1>Second Brain</h1>
      <textarea value={text} onChange={e => setText(e.target.value)} />
      <button onClick={ingest}>Ingest</button>
      <pre>{graph ? JSON.stringify(graph, null, 2) : 'Loading...'}</pre>
    </div>
  )
}

export default App
