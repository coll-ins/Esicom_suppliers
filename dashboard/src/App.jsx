import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { Loading } from './components/ui'
import { useAuth } from './lib/auth'
import Account from './pages/Account'
import Audit from './pages/Audit'
import BuyList from './pages/BuyList'
import CreditNote from './pages/CreditNote'
import CustomerView from './pages/CustomerView'
import Customers from './pages/Customers'
import DocumentView from './pages/DocumentView'
import Documents from './pages/Documents'
import Home from './pages/Home'
import Leads from './pages/Leads'
import Login from './pages/Login'
import Payments from './pages/Payments'
import ProductView from './pages/ProductView'
import QrCode from './pages/QrCode'
import Reports from './pages/Reports'
import Sell from './pages/Sell'
import Settings from './pages/Settings'
import Stock from './pages/Stock'
import Uploads from './pages/Uploads'

export default function App() {
  const { me } = useAuth()
  if (me === undefined) {
    return <div className="grid min-h-dvh place-items-center"><Loading /></div>
  }
  if (me === null) return <Login />
  const owner = me.role === 'owner'
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="sell" element={<Sell mode="sale" />} />
        <Route path="quotations/new" element={<Sell mode="quotation" />} />
        <Route path="documents" element={<Documents />} />
        <Route path="documents/:id" element={<DocumentView />} />
        <Route path="documents/:id/credit-note" element={<CreditNote />} />
        <Route path="customers" element={<Customers />} />
        <Route path="customers/:id" element={<CustomerView />} />
        <Route path="payments" element={<Payments />} />
        <Route path="stock" element={<Stock />} />
        <Route path="stock/:id" element={<ProductView />} />
        <Route path="buy-list" element={<BuyList />} />
        <Route path="reports" element={<Reports />} />
        <Route path="leads" element={<Leads />} />
        <Route path="uploads" element={<Uploads />} />
        <Route path="qr" element={<QrCode />} />
        <Route path="account" element={<Account />} />
        {owner ? <Route path="settings" element={<Settings />} /> : null}
        {owner ? <Route path="audit" element={<Audit />} /> : null}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
