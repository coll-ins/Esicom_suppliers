import { PageHeader } from '../components/ui'
import { MyAccount } from './Settings'

export default function Account() {
  return (
    <>
      <PageHeader title="My account" />
      <div className="max-w-3xl"><MyAccount /></div>
    </>
  )
}
