import { useState } from 'react'
import { pdfUrl, post } from '../lib/api'
import { emailError } from '../lib/validate'
import { Button, ButtonLink, Dialog, ErrorBox, Field, Input, Notice } from './ui'

export function whatsappHref(doc) {
  const w = doc.whatsapp || {}
  return `https://wa.me/${encodeURIComponent(w.phone || '')}?text=${encodeURIComponent(w.text || '')}`
}

// Open / download the PDF, send on WhatsApp (staff attach the PDF by hand), email it.
export default function Share({ doc }) {
  const [open, setOpen] = useState(false)
  const [to, setTo] = useState(doc.customer_email || '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [sent, setSent] = useState('')
  const err = emailError(to) || (!to.trim() ? 'Type the email address, for example accounts@company.co.ke.' : '')

  const send = async () => {
    if (err) return
    setBusy(true)
    setError(null)
    try {
      const r = await post(`/documents/${doc.id}/email/`, { to: to.trim() })
      setSent(r.detail)
      setOpen(false)
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap gap-2">
        <ButtonLink href={pdfUrl(doc.id)} target="_blank" rel="noopener">Open PDF</ButtonLink>
        <ButtonLink href={`${pdfUrl(doc.id)}?download=1`}>Download PDF</ButtonLink>
        <ButtonLink href={whatsappHref(doc)} target="_blank" rel="noopener">Send on WhatsApp</ButtonLink>
        <Button variant="secondary" onClick={() => { setOpen(true); setSent('') }}>Email</Button>
      </div>
      <p className="m-0 text-sm text-muted">WhatsApp opens with a message ready. Download the PDF first, then attach it in the chat.</p>
      {sent ? <Notice>{sent}</Notice> : null}
      <Dialog open={open} title={`Email ${doc.number}`} onClose={() => setOpen(false)}>
        <ErrorBox error={error} />
        <Field label="Send to" hint="The PDF goes as an attachment." error={to ? err : ''}>
          {(p) => <Input {...p} type="email" inputMode="email" value={to} onChange={(e) => setTo(e.target.value)} />}
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={send} loading={busy} disabled={!!err}>Send email</Button>
        </div>
      </Dialog>
    </div>
  )
}
