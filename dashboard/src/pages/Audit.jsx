import { useState } from 'react'
import { Empty, ErrorBox, Field, Input, Loading, PageHeader, Table, useLoad } from '../components/ui'
import { get } from '../lib/api'

export default function Audit() {
  const [q, setQ] = useState('')
  const [rows, error, reload] = useLoad(() => get(`/audit/?q=${encodeURIComponent(q)}`), [q])
  return (
    <>
      <PageHeader title="Audit log">Who did what and when: every sale, payment, void, refund, change and login.</PageHeader>
      <div className="mb-5 max-w-md"><Field label="Search" hint="Example: ESI-INV-2026-0012, or a customer name.">{(p) => <Input {...p} type="search" value={q} onChange={(e) => setQ(e.target.value)} />}</Field></div>
      <ErrorBox error={error} onRetry={reload} />
      {!rows && !error ? <Loading /> : null}
      {rows && !rows.length ? <Empty title="Nothing found" /> : null}
      {rows?.length ? (
        <Table head={['When', 'Who', 'What happened']}>
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="whitespace-nowrap text-sm tnum">{new Date(r.at).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</td>
              <td className="text-sm">{r.user}</td>
              <td>{r.summary}</td>
            </tr>
          ))}
        </Table>
      ) : null}
    </>
  )
}
