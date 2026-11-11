import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

MAX_PDF_PAGES = 1000
MAX_DOCX_BYTES = 30 * 1024 * 1024
MAX_DOCX_UNPACKED = 60 * 1024 * 1024  # stops "zip bombs": small files that unpack to gigabytes
CONVERT_TIMEOUT_SECONDS = 90
BACKEND_DIR = Path(__file__).resolve().parent.parent


def docx_unpacked_size(path_or_file):
    import zipfile

    with zipfile.ZipFile(path_or_file) as archive:
        return sum(info.file_size for info in archive.infolist())


def convert_file(source_path, original_filename, conversion):
    """Convert in a child process with a time limit, so one bad file cannot hang the web server.
    Size limits are checked before this runs (see docx_unpacked_size and the upload view)."""
    if conversion not in {"docx", "pdf"}:
        raise ValueError("Choose a supported conversion.")
    code = (
        "import sys\n"
        "from quotes.file_conversion import convert_in_process\n"
        "try:\n"
        "    print(convert_in_process(sys.argv[1], sys.argv[2], sys.argv[3]))\n"
        "except ValueError as exc:\n"
        "    print(exc, file=sys.stderr)\n"
        "    sys.exit(3)\n"
    )
    try:
        proc = subprocess.run(  # noqa: S603  fixed interpreter and code; file paths are passed as arguments
            [sys.executable, "-c", code, str(source_path), original_filename, conversion],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
            timeout=CONVERT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise ValueError("This file took too long to convert. Send it without converting.") from None
    if proc.returncode == 3:
        raise ValueError(
            proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "The file could not be converted."
        )
    if proc.returncode != 0:
        raise RuntimeError(f"Conversion failed (exit {proc.returncode}): {proc.stderr[-500:]}")
    return Path(proc.stdout.strip().splitlines()[-1])


def convert_in_process(source_path, original_filename, conversion):
    source = Path(source_path)
    stem = Path(original_filename).stem[:180] or "converted-file"
    if conversion == "docx":
        return _convert_pdf(source, stem)
    if conversion == "pdf":
        return _convert_docx(source, stem)
    raise ValueError("Choose a supported conversion.")


def _convert_docx(source, stem):
    """Word -> PDF without LibreOffice: mammoth turns the document into HTML, WeasyPrint prints it.
    Text, headings, lists, tables and pictures come through; exact Word layout may differ."""
    import mammoth
    from weasyprint import HTML
    from weasyprint.urls import URLFetcher

    if source.stat().st_size > MAX_DOCX_BYTES:
        raise ValueError("Word files must be 30 MB or smaller to convert.")
    if docx_unpacked_size(source) > MAX_DOCX_UNPACKED:
        raise ValueError("This Word file is too large inside to convert. Send it without converting.")
    try:
        with source.open("rb") as handle:
            result = mammoth.convert_to_html(handle)
    except Exception as exc:  # noqa: BLE001  any parse failure means an unreadable document
        raise ValueError("This Word file could not be read. Save it again as .docx and retry.") from exc
    page = (
        '<!doctype html><html><head><meta charset="utf-8"><style>'
        "@page{size:A4;margin:20mm}body{font-family:sans-serif;font-size:11pt;line-height:1.45}"
        "img{max-width:100%}table{border-collapse:collapse}td,th{border:1px solid #999;padding:4px}"
        "</style></head><body>" + result.value + "</body></html>"
    )
    # Never fetch anything a customer's file points to; only pictures stored inside the file.
    embedded_only = URLFetcher(allowed_protocols={"data"})
    output = source.with_name(f"{stem}-converted.pdf")
    HTML(string=page, url_fetcher=embedded_only).write_pdf(output)
    return output


def _convert_pdf(source, stem):
    import pymupdf as fitz
    from pdf2docx import Converter

    with fitz.open(source) as document:
        if document.is_encrypted:
            raise ValueError("Password-protected PDFs cannot be converted.")
        if not document.page_count:
            raise ValueError("This PDF has no pages.")
        if document.page_count > MAX_PDF_PAGES:
            raise ValueError(f"PDFs must have {MAX_PDF_PAGES} pages or fewer to convert.")

    with TemporaryDirectory() as directory:
        output = Path(directory) / f"{stem}-converted.docx"
        converter = Converter(str(source))
        try:
            converter.convert(str(output))
        finally:
            converter.close()
        if not output.is_file() or output.stat().st_size == 0:
            raise ValueError("The PDF did not produce a usable Word document.")
        persistent_output = source.with_name(f"{stem}-converted.docx")
        persistent_output.write_bytes(output.read_bytes())
    return persistent_output
