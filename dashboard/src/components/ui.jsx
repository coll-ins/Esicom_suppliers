import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { kes, num } from '../lib/money'

const ease = 'transition-[background-color,border-color,color,transform] duration-150 ease-[var(--ease-soft)]'

export function Button({ variant = 'primary', loading, children, className = '', ...props }) {
  const styles = {
    primary: 'bg-navy text-white hover:bg-blue',
    secondary: 'bg-white text-navy border border-line hover:border-blue hover:bg-pale',
    danger: 'bg-white text-danger border border-danger/40 hover:bg-danger-bg',
    quiet: 'text-blue hover:bg-pale',
  }
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-control)] px-4 py-2.5 text-[15px] font-bold active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-55 ${ease} ${styles[variant]} ${className}`}
      {...props}
      disabled={loading || props.disabled}
      aria-busy={loading || undefined}
    >
      {loading ? <Spinner /> : null}
      {children}
    </button>
  )
}

export function ButtonLink({ to, href, variant = 'secondary', children, className = '', ...props }) {
  const styles = {
    primary: 'bg-navy text-white hover:bg-blue',
    secondary: 'bg-white text-navy border border-line hover:border-blue hover:bg-pale',
  }
  const cls = `inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-control)] px-4 py-2.5 text-[15px] font-bold no-underline ${ease} ${styles[variant]} ${className}`
  if (href) return <a href={href} className={cls} {...props}>{children}</a>
  return <Link to={to} className={cls} {...props}>{children}</Link>
}

export function Spinner() {
  return <span className="inline-block size-4 animate-spin rounded-full border-2 border-current border-r-transparent" aria-hidden="true" />
}

// Labelled back button, top-left, 44px tall. Uses history when there is one.
export function BackLink({ to, label }) {
  const navigate = useNavigate()
  return (
    <button
      type="button"
      onClick={() => (window.history.length > 1 ? navigate(-1) : navigate(to))}
      className={`no-print -ml-2 mb-2 inline-flex min-h-11 items-center gap-1.5 rounded-[var(--radius-control)] px-2 text-[15px] font-bold text-blue hover:bg-pale ${ease}`}
    >
      <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6" /></svg>
      Back to {label}
    </button>
  )
}

export function PageHeader({ title, back, actions, children }) {
  return (
    <header className="mb-6">
      {back}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-[26px] leading-tight sm:text-[30px]">{title}</h1>
          {children ? <div className="mt-1 text-muted">{children}</div> : null}
        </div>
        {actions ? <div className="no-print flex flex-wrap gap-2">{actions}</div> : null}
      </div>
    </header>
  )
}

export function Card({ children, className = '', ...props }) {
  const pad = /(^|\s)p-\d/.test(className) ? '' : 'p-5'
  return <section className={`rounded-[var(--radius-card)] border border-line bg-white ${pad} ${className}`} {...props}>{children}</section>
}

export function Field({ label, hint, error, optional, children, className = '' }) {
  const id = useId()
  const hintId = hint ? `${id}-hint` : undefined
  const errId = error ? `${id}-err` : undefined
  const describedBy = [hintId, errId].filter(Boolean).join(' ') || undefined
  return (
    <div className={`grid gap-1.5 ${className}`}>
      <label htmlFor={id} className="text-[15px] font-bold">
        {label} {optional ? <span className="font-normal text-muted">(optional)</span> : null}
      </label>
      {children({ id, 'aria-describedby': describedBy, 'aria-invalid': error ? true : undefined })}
      {hint ? <span id={hintId} className="text-sm text-muted">{hint}</span> : null}
      {error ? <span id={errId} className="text-sm text-danger">{error}</span> : null}
    </div>
  )
}

const control = 'w-full min-h-11 rounded-[var(--radius-control)] border border-line bg-white px-3 py-2.5 text-navy placeholder:text-muted/70 aria-[invalid=true]:border-danger focus:border-blue focus:outline-none focus-visible:outline-3 focus-visible:outline-blue/35'

export function Input(props) {
  return <input className={`${control} tnum`} {...props} />
}

// Password field with a show/hide toggle. Keeps the autoComplete value the browser needs
// to offer to save and autofill the password (current-password / new-password).
export function PasswordInput(props) {
  const [shown, setShown] = useState(false)
  return (
    <div className="relative">
      <input className={`${control} pr-12`} {...props} type={shown ? 'text' : 'password'} />
      <button
        type="button"
        onClick={() => setShown((s) => !s)}
        aria-label={shown ? 'Hide password' : 'Show password'}
        aria-pressed={shown}
        className="absolute inset-y-0 right-0 grid w-11 place-items-center text-muted hover:text-navy"
      >
        {shown ? (
          <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M2 12s3.5-7 10-7c2.1 0 3.9.6 5.4 1.5M22 12s-3.5 7-10 7c-2.1 0-3.9-.6-5.4-1.5" />
            <path d="M3 3l18 18" />
            <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
          </svg>
        )}
      </button>
    </div>
  )
}

export function Select({ children, ...props }) {
  return <select className={`${control} appearance-none bg-[length:16px] bg-[right_12px_center] bg-no-repeat pr-9`} style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2365768a' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E\")" }} {...props}>{children}</select>
}

export function TextArea(props) {
  return <textarea className={`${control} min-h-24`} {...props} />
}

export function Check({ label, hint, checked, onChange, disabled }) {
  const id = useId()
  return (
    <label htmlFor={id} className={`flex min-h-11 cursor-pointer items-start gap-3 py-1 ${disabled ? 'opacity-55' : ''}`}>
      <input id={id} type="checkbox" className="mt-1 size-5 accent-[var(--color-navy)]" checked={!!checked} onChange={(e) => onChange(e.target.checked)} disabled={disabled} />
      <span><span className="font-bold">{label}</span>{hint ? <span className="block text-sm text-muted">{hint}</span> : null}</span>
    </label>
  )
}

// Segmented choice: one tap, big targets.
export function Choice({ value, onChange, options, label }) {
  return (
    <div role="radiogroup" aria-label={label} className="grid auto-cols-fr grid-flow-col gap-1 rounded-[var(--radius-control)] border border-line bg-pale p-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          disabled={o.disabled}
          onClick={() => onChange(o.value)}
          className={`min-h-11 rounded-md px-3 text-[15px] font-bold disabled:opacity-40 ${ease} ${value === o.value ? 'bg-navy text-white' : 'text-navy hover:bg-white'}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

// The invoice's navy total band, reused across the app.
export function Band({ label, amount, sub, className = '' }) {
  return (
    <div className={`flex items-center justify-between gap-3 rounded-[var(--radius-control)] bg-navy px-4 py-3.5 text-white ${className}`}>
      <div>
        <div className="font-display text-[17px] font-bold">{label}</div>
        {sub ? <div className="text-sm text-white/70">{sub}</div> : null}
      </div>
      <div className="font-display text-[22px] font-bold tnum">{typeof amount === 'number' ? kes(amount) : amount}</div>
    </div>
  )
}

// A row of named horizontal bars: one hue per job (magnitude = blue, de-emphasised = muted,
// good/bad outcome = ok/danger), never color-only — every bar carries its own text label and
// value, so nothing depends on telling hues apart. Hover/focus shows the exact figure.
export function Bars({ rows, formatValue = num, labelWidth = 'w-24' }) {
  const max = Math.max(1, ...rows.map((r) => Math.abs(r.value)))
  return (
    <ul className="grid gap-2">
      {rows.map((r) => (
        <li key={r.label} className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 text-[15px]">
          <span className={`truncate text-muted ${labelWidth}`} title={r.label}>{r.label}</span>
          <span className="h-3 rounded-full bg-pale">
            <span
              tabIndex={0}
              title={formatValue(r.value)}
              className="block h-3 origin-left rounded-full transition-transform duration-200 ease-[var(--ease-soft)] hover:opacity-80 focus-visible:opacity-80"
              style={{ transform: `scaleX(${Math.max(Math.abs(r.value) / max, r.value ? 0.01 : 0)})`, background: r.color || 'var(--color-blue)' }}
            />
          </span>
          <span className="text-right font-bold tnum">{formatValue(r.value)}</span>
        </li>
      ))}
    </ul>
  )
}

export function TotalsRows({ rows }) {
  return (
    <dl className="grid gap-1">
      {rows.filter(Boolean).map(([label, value]) => (
        <div key={label} className="flex justify-between gap-3 rounded-md bg-pale px-3 py-2">
          <dt>{label}</dt>
          <dd className="font-bold tnum">{kes(value)}</dd>
        </div>
      ))}
    </dl>
  )
}

const pills = {
  paid: 'bg-ok-bg text-ok', issued: 'bg-pale text-blue', unpaid: 'bg-warn-bg text-warn', overdue: 'bg-danger-bg text-danger',
  void: 'bg-line text-muted', ok: 'bg-ok-bg text-ok', reorder: 'bg-warn-bg text-warn', out: 'bg-danger-bg text-danger',
  new: 'bg-pale text-blue', contacted: 'bg-warn-bg text-warn', quoted: 'bg-ok-bg text-ok', closed: 'bg-line text-muted',
}
const pillText = { ok: 'In stock', reorder: 'At reorder level', out: 'Out of stock' }

export function Pill({ status }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[13px] font-bold whitespace-nowrap ${pills[status] || 'bg-pale text-blue'}`}>
      {pillText[status] || status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

export function Empty({ title, children, action }) {
  return (
    <div className="grid justify-items-start gap-2 rounded-[var(--radius-card)] border border-dashed border-line bg-white p-6">
      <h3 className="text-[17px]">{title}</h3>
      {children ? <p className="m-0 max-w-[60ch] text-muted">{children}</p> : null}
      {action}
    </div>
  )
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-control)] border border-danger/30 bg-danger-bg px-4 py-3 text-danger">
      <span>{error.message || String(error)}</span>
      {onRetry ? <Button variant="secondary" onClick={onRetry}>Try again</Button> : null}
    </div>
  )
}

export function Notice({ children, tone = 'ok' }) {
  const tones = { ok: 'border-ok/30 bg-ok-bg text-ok', warn: 'border-warn/30 bg-warn-bg text-warn', info: 'border-line bg-pale text-navy' }
  return <div role="status" className={`rounded-[var(--radius-control)] border px-4 py-3 ${tones[tone]}`}>{children}</div>
}

export function Loading() {
  return (
    <div className="flex min-h-32 items-center gap-3 text-muted" role="status">
      <Spinner /> Loading…
    </div>
  )
}

// Load data for a screen; returns [data, error, reload, setData].
export function useLoad(loader, deps = []) {
  const [state, setState] = useState({ data: null, error: null })
  const latest = useRef(0)
  const run = useCallback(() => {
    const n = ++latest.current
    setState((s) => ({ ...s, error: null }))
    loader()
      .then((data) => n === latest.current && setState({ data, error: null }))
      .catch((error) => n === latest.current && setState({ data: null, error }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(() => { run() }, [run])
  return [state.data, state.error, run, (data) => setState({ data, error: null })]
}

export function Dialog({ open, title, onClose, children }) {
  const ref = useRef(null)
  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) d.showModal()
    if (!open && d.open) d.close()
  }, [open])
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onCancel={onClose}
      className="m-auto w-[min(560px,calc(100vw-32px))] rounded-[var(--radius-card)] border border-line p-0 text-navy backdrop:bg-navy/40"
    >
      {open ? (
        <div className="grid gap-4 p-5">
          <div className="flex items-start justify-between gap-3">
            <h2 className="text-[20px]">{title}</h2>
            <button type="button" onClick={onClose} className="-mr-2 -mt-1 grid size-11 place-items-center rounded-md text-muted hover:bg-pale" aria-label="Close">
              <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
            </button>
          </div>
          {children}
        </div>
      ) : null}
    </dialog>
  )
}

export function Table({ head, children, empty }) {
  return (
    <div className="overflow-x-auto rounded-[var(--radius-card)] border border-line bg-white">
      <table className="w-full min-w-[560px] border-collapse text-left text-[15px]">
        <thead>
          <tr className="bg-navy text-white">
            {head.map((h, i) => (
              <th key={i} className={`px-3 py-2.5 font-bold first:rounded-tl-[13px] last:rounded-tr-[13px] ${h.right ? 'text-right' : ''}`}>{h.label ?? h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="[&_td]:border-b [&_td]:border-line [&_td]:px-3 [&_td]:py-2.5 [&_tr:last-child_td]:border-b-0">{children}</tbody>
      </table>
      {empty}
    </div>
  )
}

// Public files (logo, photos) live under the app's base path, /dashboard/.
export const asset = (path) => import.meta.env.BASE_URL + path

export function dateText(value) {
  if (!value) return ''
  const d = new Date(value.length === 10 ? value + 'T00:00:00' : value)
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function todayIso() {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}
