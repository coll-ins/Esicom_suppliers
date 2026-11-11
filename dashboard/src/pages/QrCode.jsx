import { Button, ErrorBox, Loading, PageHeader, asset, useLoad } from '../components/ui'
import { get, qrUrl } from '../lib/api'

export default function QrCode() {
  const [info, error, reload] = useLoad(() => get('/qr/'))
  return (
    <>
      <div className="no-print"><PageHeader title="Upload QR code" actions={<Button onClick={() => window.print()}>Print</Button>}>
        Staff only. Print it and put it at the counter. Scanning it opens the upload page.
      </PageHeader></div>
      <ErrorBox error={error} onRetry={reload} />
      {!info && !error ? <Loading /> : null}
      {info ? (
        <div className="print-area mx-auto grid max-w-md justify-items-center gap-4 rounded-[var(--radius-card)] border border-line bg-white p-8 text-center">
          <img src={asset('images/logo.png')} alt="" className="size-14" />
          <h2 className="text-[24px]">Send us your file</h2>
          <p className="m-0 text-muted">Scan with your phone camera, choose the file, press Send.</p>
          <img src={qrUrl()} alt={`QR code for ${info.url}`} className="size-72 [image-rendering:pixelated]" />
          <p className="m-0 font-bold break-all">{info.url}</p>
          <p className="m-0 text-sm text-muted">PDF, Word, JPG, PNG or WebP. Up to 50 MB.</p>
        </div>
      ) : null}
    </>
  )
}
