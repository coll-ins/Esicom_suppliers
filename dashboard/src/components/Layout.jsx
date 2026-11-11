import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { Icon } from './icons'

const NAV = [
  { to: '/', label: 'Home', icon: 'home', end: true },
  { to: '/sell', label: 'Record a sale', icon: 'sell' },
  { to: '/documents', label: 'Documents', icon: 'docs' },
  { to: '/customers', label: 'Customers', icon: 'customers' },
  { to: '/payments', label: 'Payments', icon: 'payments' },
  { to: '/stock', label: 'Stock', icon: 'stock' },
  { to: '/buy-list', label: 'Buy list', icon: 'buy' },
  { to: '/reports', label: 'Reports', icon: 'reports' },
  { to: '/quotations/new', label: 'New quotation', icon: 'quote' },
  { to: '/leads', label: 'Website leads', icon: 'leads' },
  { to: '/uploads', label: 'File uploads', icon: 'uploads' },
  { to: '/qr', label: 'Upload QR code', icon: 'qr' },
  { to: '/settings', label: 'Settings', icon: 'settings', owner: true },
  { to: '/audit', label: 'Audit log', icon: 'audit', owner: true },
  { to: '/account', label: 'My account', icon: 'customers' },
]

// Phone bottom bar: the four things done most at the counter, plus everything else.
const TABS = [
  { to: '/', label: 'Home', icon: 'home', end: true },
  { to: '/sell', label: 'Sell', icon: 'sell' },
  { to: '/documents', label: 'Documents', icon: 'docs' },
  { to: '/stock', label: 'Stock', icon: 'stock' },
]

const linkCls = ({ isActive }) =>
  `flex min-h-11 items-center gap-3 rounded-[var(--radius-control)] px-3 text-[15px] font-bold transition-colors duration-150 ${
    isActive ? 'bg-white/12 text-white' : 'text-white/75 hover:bg-white/8 hover:text-white'
  }`

function NavList({ me, onNavigate }) {
  return (
    <nav aria-label="Main" className="grid gap-0.5">
      {NAV.filter((n) => !n.owner || me.role === 'owner').map((n) => (
        <NavLink key={n.to} to={n.to} end={n.end} className={linkCls} onClick={onNavigate}>
          <Icon name={n.icon} /> {n.label}
        </NavLink>
      ))}
    </nav>
  )
}

function Who({ me, logout }) {
  return (
    <div className="mt-auto grid gap-2 border-t border-white/12 pt-4">
      <div className="px-3 text-sm text-white/70">
        <div className="font-bold text-white">{me.name}</div>
        {me.role === 'owner' ? 'Owner' : 'Staff'}
      </div>
      <button type="button" onClick={logout} className="flex min-h-11 items-center gap-3 rounded-[var(--radius-control)] px-3 text-[15px] font-bold text-white/75 hover:bg-white/8 hover:text-white">
        <Icon name="logout" /> Log out
      </button>
    </div>
  )
}

export default function Layout() {
  const { me, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const location = useLocation()
  useEffect(() => setOpen(false), [location.pathname])

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[256px_minmax(0,1fr)]">
      <aside className="no-print sticky top-0 hidden h-dvh self-start flex-col gap-6 bg-navy p-4 text-white lg:flex">
        <Brand />
        <div className="-mx-1 overflow-y-auto px-1"><NavList me={me} /></div>
        <Who me={me} logout={logout} />
      </aside>

      <header className="no-print sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-line bg-white/95 px-4 py-2 backdrop-blur lg:hidden">
        <div className="flex items-center gap-2.5">
          <img src="/images/logo.png" alt="" className="size-9" />
          <span className="font-display text-[16px] font-bold">Esicom ledger</span>
        </div>
        <button type="button" onClick={() => setOpen(true)} className="grid size-11 place-items-center rounded-md hover:bg-pale" aria-label="Open menu">
          <Icon name="menu" className="size-6" />
        </button>
      </header>

      {open ? (
        <div className="no-print fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <button type="button" className="absolute inset-0 bg-navy/40" aria-label="Close menu" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 right-0 flex w-[min(300px,85vw)] flex-col gap-5 overflow-y-auto bg-navy p-4 text-white">
            <div className="flex items-center justify-between">
              <Brand />
              <button type="button" onClick={() => setOpen(false)} className="grid size-11 place-items-center rounded-md hover:bg-white/10" aria-label="Close menu">
                <svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
              </button>
            </div>
            <NavList me={me} onNavigate={() => setOpen(false)} />
            <Who me={me} logout={logout} />
          </div>
        </div>
      ) : null}

      <main id="main" className="mx-auto w-full max-w-[1280px] px-4 pb-28 pt-5 sm:px-6 lg:px-10 lg:pb-12 lg:pt-8">
        <Outlet />
      </main>

      <nav aria-label="Quick" className="no-print fixed inset-x-0 bottom-0 z-20 grid grid-cols-4 border-t border-line bg-white pb-[env(safe-area-inset-bottom)] lg:hidden">
        {TABS.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.end}
            className={({ isActive }) => `flex min-h-14 flex-col items-center justify-center gap-0.5 text-[12px] font-bold ${isActive ? 'text-navy' : 'text-muted'}`}
          >
            {({ isActive }) => (
              <>
                <span className={`grid h-7 w-12 place-items-center rounded-full ${isActive ? 'bg-pale' : ''}`}><Icon name={t.icon} /></span>
                {t.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}

function Brand() {
  return (
    <div className="flex items-center gap-3 px-1">
      <img src="/images/logo.png" alt="" className="size-10" />
      <div className="leading-tight">
        <div className="font-display text-[16px] font-bold">Esicom Suppliers</div>
        <div className="text-[13px] text-white/65">Ledger</div>
      </div>
    </div>
  )
}
