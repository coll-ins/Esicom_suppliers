from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf as fitz
from pdf2docx import Converter


MAX_PDF_PAGES = 1000
MAX_DOCX_BYTES = 30 * 1024 * 1024


def convert_file(source_path, original_filename, conversion):
    source = Path(source_path)
    stem = Path(original_filename).stem[:180] or 'converted-file'
    if conversion == 'docx':
        return _convert_pdf(source, stem)
    if conversion == 'pdf':
        return _convert_docx(source, stem)
    raise ValueError('Choose a supported conversion.')


def _convert_docx(source, stem):
    """Word -> PDF without LibreOffice: mammoth turns the document into HTML, WeasyPrint prints it.
    Text, headings, lists, tables and pictures come through; exact Word layout may differ."""
    import mammoth
    from weasyprint import HTML
    from weasyprint.urls import URLFetcher

    if source.stat().st_size > MAX_DOCX_BYTES:
        raise ValueError('Word files must be 30 MB or smaller to convert.')
    try:
        with source.open('rb') as handle:
            result = mammoth.convert_to_html(handle)
    except Exception as exc:  # noqa: BLE001  any parse failure means an unreadable document
        raise ValueError('This Word file could not be read. Save it again as .docx and retry.') from exc
    page = (
        '<!doctype html><html><head><meta charset="utf-8"><style>'
        '@page{size:A4;margin:20mm}body{font-family:sans-serif;font-size:11pt;line-height:1.45}'
        'img{max-width:100%}table{border-collapse:collapse}td,th{border:1px solid #999;padding:4px}'
        '</style></head><body>' + result.value + '</body></html>'
    )
    # Never fetch anything a customer's file points to; only pictures stored inside the file.
    embedded_only = URLFetcher(allowed_protocols={'data'})
    output = source.with_name(f'{stem}-converted.pdf')
    HTML(string=page, url_fetcher=embedded_only).write_pdf(output)
    return output


def _convert_pdf(source, stem):
    with fitz.open(source) as document:
        if document.is_encrypted:
            raise ValueError('Password-protected PDFs cannot be converted.')
        if not document.page_count:
            raise ValueError('This PDF has no pages.')
        if document.page_count > MAX_PDF_PAGES:
            raise ValueError(f'PDFs must have {MAX_PDF_PAGES} pages or fewer to convert.')

    with TemporaryDirectory() as directory:
        output = Path(directory) / f'{stem}-converted.docx'
        converter = Converter(str(source))
        try:
            converter.convert(str(output))
        finally:
            converter.close()
        if not output.is_file() or output.stat().st_size == 0:
            raise ValueError('The PDF did not produce a usable Word document.')
        persistent_output = source.with_name(f'{stem}-converted.docx')
        persistent_output.write_bytes(output.read_bytes())
    return persistent_output
