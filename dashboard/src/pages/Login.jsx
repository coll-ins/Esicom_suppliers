import { useState } from 'react'
import { Button, ErrorBox, Field, Input, Notice, asset } from '../components/ui'
import { post } from '../lib/api'
import { useAuth } from '../lib/auth'

export default function Login() {
  const { login } = useAuth()
  const [mode, setMode] = useState('login') // login | request | confirm
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState('')

  const run = (fn) => async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await fn()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[minmax(0,1fr)_520px]">
      <div className="h-44 bg-cover bg-center sm:h-64 lg:h-auto" style={{ backgroundImage: `url(${asset('images/login.webp')})` }} role="img" aria-label="Esicom office supplies" />
      <main className="mx-auto grid w-full max-w-[520px] content-center gap-6 px-4 py-8 sm:px-8 lg:px-12">
        <div className="flex items-center gap-3">
          <img src={asset('images/logo.png')} alt="" className="size-12" />
          <div>
            <div className="font-display text-[18px] font-bold">Esicom Suppliers</div>
            <div className="text-muted">Ledger: sales, invoices and stock</div>
          </div>
        </div>

        {mode === 'login' ? (
          <form className="grid gap-4" onSubmit={run(() => login(email.trim(), password))} noValidate>
            <h1 className="text-[28px]">Log in</h1>
            <ErrorBox error={error} />
            {notice ? <Notice>{notice}</Notice> : null}
            <Field label="Email" hint="The email the owner registered for you, for example jane@gmail.com.">
              {(p) => <Input {...p} type="email" autoComplete="username" inputMode="email" value={email} onChange={(e) => setEmail(e.target.value)} required />}
            </Field>
            <Field label="Password">
              {(p) => <Input {...p} type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />}
            </Field>
            <Button type="submit" loading={busy}>Log in</Button>
            <button type="button" className="min-h-11 justify-self-start font-bold text-blue underline" onClick={() => { setMode('request'); setError(null); setNotice('') }}>
              Forgot password, or first time here?
            </button>
          </form>
        ) : null}

        {mode === 'request' ? (
          <form
            className="grid gap-4"
            noValidate
            onSubmit={run(async () => {
              const r = await post('/auth/reset/request/', { email: email.trim() })
              setNotice(r.detail)
              setMode('confirm')
            })}
          >
            <h1 className="text-[28px]">Set a new password</h1>
            <p className="m-0 text-muted">We email you a 6-digit code. It works once and expires in 15 minutes.</p>
            <ErrorBox error={error} />
            <Field label="Email" hint="Example: jane@gmail.com">
              {(p) => <Input {...p} type="email" autoComplete="username" inputMode="email" value={email} onChange={(e) => setEmail(e.target.value)} />}
            </Field>
            <Button type="submit" loading={busy}>Email me a code</Button>
            <button type="button" className="min-h-11 justify-self-start font-bold text-blue underline" onClick={() => setMode('login')}>Back to log in</button>
          </form>
        ) : null}

        {mode === 'confirm' ? (
          <form
            className="grid gap-4"
            noValidate
            onSubmit={run(async () => {
              const r = await post('/auth/reset/confirm/', { email: email.trim(), code: code.trim(), password: newPassword })
              setNotice(r.detail)
              setPassword('')
              setMode('login')
            })}
          >
            <h1 className="text-[28px]">Enter the code</h1>
            {notice ? <Notice tone="info">{notice}</Notice> : null}
            <ErrorBox error={error} />
            <Field label="6-digit code" hint="From the email we just sent. Example: 482913.">
              {(p) => <Input {...p} inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} />}
            </Field>
            <Field label="New password" hint="At least 8 characters, not only numbers, not a common password.">
              {(p) => <Input {...p} type="password" autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />}
            </Field>
            <Button type="submit" loading={busy}>Save new password</Button>
            <button type="button" className="min-h-11 justify-self-start font-bold text-blue underline" onClick={() => setMode('request')}>Send a new code</button>
          </form>
        ) : null}
      </main>
    </div>
  )
}
