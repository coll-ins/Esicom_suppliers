from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf as fitz
from PIL import Image, UnidentifiedImageError
from pdf2docx import Converter


IMAGE_FORMATS = {
    'jpeg': ('JPEG', 'jpg'),
    'png': ('PNG', 'png'),
    'webp': ('WEBP', 'webp'),
}
MAX_IMAGE_PIXELS = 40_000_000
MAX_PDF_PAGES = 50


def convert_file(source_path, original_filename, conversion):
    source = Path(source_path)
    stem = Path(original_filename).stem[:180] or 'converted-file'

    if conversion in IMAGE_FORMATS:
        return _convert_image(source, stem, conversion)
    if conversion == 'docx':
        return _convert_pdf(source, stem)
    raise ValueError('Choose a supported conversion.')


def _convert_image(source, stem, conversion):
    image_format, extension = IMAGE_FORMATS[conversion]
    output = None
    try:
        with Image.open(source) as image:
            if image.format not in {'JPEG', 'PNG', 'WEBP'}:
                raise ValueError('Only JPEG, PNG, and WebP images can be converted.')
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise ValueError('This image is too large to convert.')
            image.load()
            if image_format == 'JPEG':
                if image.mode in ('RGBA', 'LA') or 'transparency' in image.info:
                    background = Image.new('RGB', image.size, 'white')
                    foreground = image.convert('RGBA')
                    background.paste(foreground, mask=foreground.getchannel('A'))
                    image = background
                else:
                    image = image.convert('RGB')
            output = source.with_name(f'{stem}-converted.{extension}')
            image.save(output, format=image_format)
    except (OSError, UnidentifiedImageError) as exc:
        if output and output.exists():
            output.unlink()
        raise ValueError('The selected image could not be opened.') from exc
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
