import { useEffect, useState } from 'react'

type Board = {
  id: string
  name: string
  kind: string
  color: string
  children: Board[]
}

export default function App() {
  const [tree, setTree] = useState<Board[]>([])
  const [stats, setStats] = useState<Record<string, number> | null>(null)

  useEffect(() => {
    fetch('/api/boards/tree').then(r => r.json()).then(setTree)
    fetch('/api/tasks/stats/summary').then(r => r.json()).then(setStats)
  }, [])

  return (
    <div style={{ padding: 16, fontFamily: 'system-ui, sans-serif', background: '#111827', color: '#e5e7eb', minHeight: '100vh' }}>
      <h1 style={{ fontSize: 14, margin: 0 }}>Rogerio Projects &amp; Tasks Tracker</h1>
      <p style={{ fontSize: 11, color: '#9ca3af', margin: '4px 0 16px' }}>
        Backend live. {stats ? `Total tasks: ${stats.total} · Done: ${stats.done} · Completion: ${stats.completion_rate}%` : 'Loading stats…'}
      </p>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {tree.map(section => (
          <div key={section.id} style={{ border: `1px solid ${section.color}`, borderRadius: 6, padding: 12, minWidth: 200 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: section.color, marginBottom: 8 }}>
              {section.name}
            </div>
            {section.children.map(child => (
              <div key={child.id} style={{ fontSize: 11, padding: '3px 0', borderTop: '1px solid #374151' }}>
                <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: child.color, marginRight: 6 }} />
                {child.name}
              </div>
            ))}
          </div>
        ))}
      </div>
      <p style={{ fontSize: 10, color: '#6b7280', marginTop: 16 }}>
        Phase 2 (frontend views) coming — this is the placeholder shell.
      </p>
    </div>
  )
}
