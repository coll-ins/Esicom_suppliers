import { ButtonLink, Empty, ErrorBox, Loading, PageHeader, dateText, useLoad } from '../components/ui'
import { get, uploadUrl } from '../lib/api'

export default function Uploads() {
  const [list, error, reload] = useLoad(() => get('/uploads/'))
  return (
    <>
      <PageHeader title="File uploads" actions={<ButtonLink to="/qr">Upload QR code</ButtonLink>}>
        Files customers sent from the upload page. Each one is also emailed to esicomsuppliers@gmail.com.
      </PageHeader>
      <ErrorBox error={error} onRetry={reload} />
      {!list && !error ? <Loading /> : null}
      {list && !list.length ? <Empty title="No files yet">Print the QR code and put it at the counter. Customers scan it to send files.</Empty> : null}
      <ul className="grid gap-3">
        {(list || []).map((f) => (
          <li key={f.id} className="grid gap-3 rounded-[var(--radius-card)] border border-line bg-white p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
            <div className="min-w-0">
              <div className="truncate font-bold">{f.original_filename}</div>
              <div className="text-sm text-muted">
                {f.reference}, {dateText(f.created_at)}
                {f.name ? `. From ${f.name}` : ''}{f.phone ? ` (${f.phone})` : ''}
              </div>
              {f.note ? <p className="m-0 mt-1 max-w-[75ch]">{f.note}</p> : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <ButtonLink href={uploadUrl(f.id, 'original')}>Download</ButtonLink>
              {f.converted_filename ? <ButtonLink href={uploadUrl(f.id, 'converted')}>Converted copy</ButtonLink> : null}
            </div>
          </li>
        ))}
      </ul>
    </>
  )
}
