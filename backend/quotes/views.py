import json
import logging
import mimetypes
import re
from io import BytesIO
from datetime import date
from pathlib import Path
import qrcode
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage, send_mail
from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from .file_conversion import convert_file
from .models import FileSubmission, PAGE_CHOICES, PageContent, PageSection, QuoteRequest, SitePhoto, VisualEdit
logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 50 * 1024 * 1024
MAX_EMAIL_ATTACHMENT_SIZE = 15 * 1024 * 1024
MAX_UPLOADS_PER_HOUR = 200
ALLOWED_UPLOAD_EXTENSIONS = {'.pdf', '.docx', '.jpg', '.jpeg', '.png', '.webp'}
CONVERSIONS = {'docx': '.pdf', 'pdf': '.docx'}  # target -> the file type it converts from


def private_media_not_found(request, path):
    return HttpResponseNotFound()


@require_GET
def public_media(request, path):
    media_root = Path(settings.MEDIA_ROOT).resolve()
    try:
        file_path = (media_root / path).resolve(strict=True)
        relative_path = file_path.relative_to(media_root)
    except (OSError, ValueError):
        raise Http404
    if not relative_path.parts or relative_path.parts[0] != 'pages' or not file_path.is_file():
        raise Http404

    content_type = mimetypes.guess_type(file_path.name)[0] or 'application/octet-stream'
    response = FileResponse(file_path.open('rb'), content_type=content_type)
    response['Cache-Control'] = 'public, max-age=3600'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@require_GET
def health(request):
    return JsonResponse({'status': 'ok'})


@require_GET
def site_content(request):
    pages = {}
    for page in PageContent.objects.filter(is_published=True):
        pages[page.page] = {
            'eyebrow': page.eyebrow,
            'title': page.title,
            'highlight': page.highlight,
            'intro': page.intro,
            'image': page.hero_image.url if page.hero_image else '',
        }
    sections = [{
        'id': section.pk,
        'page': section.page,
        'title': section.title,
        'body': section.body,
        'image': section.image.url if section.image else '',
        'button_text': section.button_text,
        'button_url': section.button_url,
    } for section in PageSection.objects.filter(is_published=True)]
    photos = {
        photo.source_path: photo.image.url
        for photo in SitePhoto.objects.all()
    }
    visual_edits = [{
        'page': edit.page,
        'selector': edit.selector,
        'text': edit.text_value if edit.text_enabled else None,
        'image': edit.image.url if edit.image else '',
        'font_family': edit.font_family,
        'font_size': edit.font_size,
        'text_color': edit.text_color,
        'hidden': edit.hidden,
    } for edit in VisualEdit.objects.all()]
    return JsonResponse({
        'pages': pages,
        'sections': sections,
        'photos': photos,
        'visual_edits': visual_edits,
    })


@staff_member_required
@ensure_csrf_cookie
def visual_editor(request):
    selected_page = request.GET.get('page', 'home')
    if selected_page not in dict(PAGE_CHOICES):
        selected_page = 'home'
    return render(request, 'quotes/visual_editor.html', {
        'pages': PAGE_CHOICES,
        'preview_url': settings.ESICOM_EDITOR_PREVIEW_URL,
        'editor_origin': request.build_absolute_uri('/'),
        'selected_page': selected_page,
    })


@staff_member_required
@require_http_methods(['GET', 'POST', 'DELETE'])
def visual_edit_api(request, page):
    if page not in dict(PAGE_CHOICES):
        return JsonResponse({'detail': 'Choose a website page from the editor.'}, status=404)

    if request.method == 'GET':
        edits = VisualEdit.objects.filter(page__in=[page, 'global'])
        return JsonResponse({'edits': [{
            'selector': edit.selector,
            'text': edit.text_value if edit.text_enabled else '',
            'text_enabled': edit.text_enabled,
            'image': edit.image.url if edit.image else '',
            'font_family': edit.font_family,
            'font_size': edit.font_size or '',
            'text_color': edit.text_color,
            'hidden': edit.hidden,
        } for edit in edits]})

    selector = request.POST.get('selector', '') if request.method == 'POST' else request.GET.get('selector', '')
    if request.content_type == 'application/json':
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'detail': 'The editor sent invalid data.'}, status=400)
        selector = payload.get('selector', '')
    else:
        payload = request.POST

    edit_page = 'global' if selector.startswith(('header >', 'footer >', '.topline >')) else page
    if request.method == 'DELETE':
        edit = get_object_or_404(VisualEdit, page=edit_page, selector=selector)
        edit.delete()
        return JsonResponse({'ok': True})

    edit = VisualEdit.objects.filter(page=edit_page, selector=selector).first()
    if edit is None:
        edit = VisualEdit(page=edit_page, selector=selector)
    edit.text_value = payload.get('text', '')
    edit.text_enabled = str(payload.get('text_enabled', '')).lower() in {'true', '1', 'on'}
    edit.font_family = payload.get('font_family', '')
    font_size = payload.get('font_size', '')
    try:
        edit.font_size = int(font_size) if font_size else None
    except (TypeError, ValueError):
        return JsonResponse({'detail': 'Font size must be a number.'}, status=400)
    edit.text_color = payload.get('text_color', '').strip()
    edit.hidden = str(payload.get('hidden', '')).lower() in {'true', '1', 'on'}
    if 'image' in request.FILES:
        edit.image = request.FILES['image']
    elif str(payload.get('remove_image', '')).lower() in {'true', '1', 'on'}:
        edit.image = ''

    try:
        edit.save()
    except ValidationError as error:
        return JsonResponse({'detail': error.messages[0]}, status=400)

    return JsonResponse({'ok': True})


@staff_member_required
@require_POST
def create_page_section(request, page):
    if page not in dict(PAGE_CHOICES):
        return JsonResponse({'detail': 'Choose a website page from the editor.'}, status=404)

    section = PageSection(
        page=page,
        title=request.POST.get('title', '').strip(),
        body=request.POST.get('body', '').strip(),
        button_text=request.POST.get('button_text', '').strip(),
        button_url=request.POST.get('button_url', '').strip(),
        display_order=(PageSection.objects.filter(page=page).order_by('-display_order')
                       .values_list('display_order', flat=True).first() or 0) + 1,
        is_published=True,
    )
    if 'image' in request.FILES:
        section.image = request.FILES['image']
    try:
        section.full_clean()
        section.save()
    except ValidationError as error:
        return JsonResponse({'detail': error.messages[0]}, status=400)
    return JsonResponse({'ok': True, 'id': section.pk}, status=201)


def _validate_upload(uploaded_file):
    extension = Path(uploaded_file.name.replace('\\', '/')).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        return None, 'This file type is not accepted. Send a PDF, a Word file (.docx), or a JPG, PNG or WebP photo.'
    if not uploaded_file.size:
        return None, 'The selected file is empty.'
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        return None, f'This file is {uploaded_file.size // (1024 * 1024)} MB. Files must be 50 MB or smaller.'

    uploaded_file.seek(0)
    signature = uploaded_file.read(5)
    uploaded_file.seek(0)
    if extension == '.pdf':
        if not signature.startswith(b'%PDF-'):
            return None, 'The selected file is not a valid PDF.'
    elif extension == '.docx':
        import zipfile
        try:
            with zipfile.ZipFile(uploaded_file) as archive:
                if 'word/document.xml' not in archive.namelist():
                    return None, 'The selected file is not a valid Word document.'
                if sum(info.file_size for info in archive.infolist()) > 200 * 1024 * 1024:
                    return None, 'This Word file is damaged or too large inside. Save it again and retry.'
        except zipfile.BadZipFile:
            return None, 'The selected file is not a valid Word document.'
        finally:
            uploaded_file.seek(0)
    else:
        from PIL import Image, UnidentifiedImageError
        try:
            image = Image.open(uploaded_file)
            image_format = image.format
            image.verify()
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
            return None, 'The selected image could not be opened.'
        finally:
            uploaded_file.seek(0)
        expected = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.webp': 'WEBP'}[extension]
        if image_format != expected:
            return None, 'The file contents do not match its image extension.'
    return extension, None


def _client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.rsplit(',', 1)[-1].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


@require_GET
def upload_page(request):
    """Public page customers reach by scanning the QR code in the shop. It only uploads and sends."""
    return render(request, 'quotes/upload.html', {
        'max_mb': MAX_UPLOAD_SIZE // (1024 * 1024),
        'email_mb': MAX_EMAIL_ATTACHMENT_SIZE // (1024 * 1024),
    })


@csrf_exempt
@require_POST
def create_file_submission(request):
    ip = _client_ip(request)
    key = f'esicom-file-upload:{ip}'
    count = cache.get(key, 0)
    if count >= MAX_UPLOADS_PER_HOUR:
        return JsonResponse({'detail': 'Too many uploads from this connection. Please try again in an hour.'}, status=429)
    if request.POST.get('website', '').strip():
        return JsonResponse({'ok': True}, status=201)
    cache.set(key, count + 1, timeout=3600)

    uploaded_file = request.FILES.get('file')
    if uploaded_file is None:
        return JsonResponse({'detail': 'Choose a file to send.'}, status=400)
    extension, error = _validate_upload(uploaded_file)
    if error:
        return JsonResponse({'detail': error}, status=400)
    conversion = request.POST.get('conversion', '').strip().lower()
    if conversion and CONVERSIONS.get(conversion) != extension:
        return JsonResponse({
            'detail': 'That conversion does not fit this file. PDF can become Word, and Word can become PDF.'
        }, status=400)

    name = request.POST.get('name', '').strip()
    phone = request.POST.get('phone', '').strip()
    note = request.POST.get('note', '').strip()
    if len(name) > 120 or len(note) > 500:
        return JsonResponse({'detail': 'Your name must be under 120 characters and the note under 500.'}, status=400)
    if phone:
        from ledger.validators import PHONE_HELP, display_ke_phone, normalize_ke_phone
        try:
            phone = display_ke_phone(normalize_ke_phone(phone))
        except ValueError:
            return JsonResponse({'detail': f'Phone: use a {PHONE_HELP}'}, status=400)

    original_name = uploaded_file.name.replace('\\', '/').split('/')[-1][:255]
    submission = FileSubmission(
        original_filename=original_name, delivery_method='email', delivery_consent=True,
        name=name, phone=phone, note=note,
    )
    converted_path = None
    try:
        submission.uploaded_file.save(original_name, uploaded_file, save=False)
        submission.save()
        if conversion:
            converted_path = convert_file(submission.uploaded_file.path, original_name, conversion)
            if converted_path.stat().st_size > MAX_UPLOAD_SIZE:
                raise ValueError('The converted file is larger than 50 MB. Send it without converting.')
            contents = converted_path.read_bytes()
            converted_path.unlink(missing_ok=True)
            submission.converted_file.save(converted_path.name, ContentFile(contents), save=False)
        submission.save()
    except ValueError as exc:
        _discard_submission(submission, converted_path)
        return JsonResponse({'detail': str(exc)}, status=422)
    except Exception:
        _discard_submission(submission, converted_path)
        logger.exception('File submission processing failed.')
        return JsonResponse({'detail': 'The file could not be converted. Send it without converting.'}, status=500)

    _email_submission(submission)
    return JsonResponse({
        'ok': True,
        'reference': f'ES-F{submission.pk}',
        'filename': Path(submission.converted_file.name).name if submission.converted_file else original_name,
        'converted': bool(submission.converted_file),
    }, status=201)


def _email_submission(submission):
    """Email the file to Esicom. The file is already saved and listed in the dashboard,
    so a mail failure is logged, not shown to the customer."""
    dashboard = settings.ESICOM_DASHBOARD_URL.rstrip('/')
    lines = [
        f'Reference: ES-F{submission.pk}',
        f'File: {submission.original_filename}',
        f'Name: {submission.name or "Not given"}',
        f'Phone: {submission.phone or "Not given"}',
        f'Note: {submission.note or "None"}',
    ]
    attachment = submission.converted_file or submission.uploaded_file
    attach = attachment.size <= MAX_EMAIL_ATTACHMENT_SIZE
    lines.append('The file is attached.' if attach else 'The file is too large to attach. Open it in the dashboard.')
    if dashboard:
        lines.append(f'Dashboard: {dashboard}/uploads')
    email = EmailMessage(
        f'New file from a customer: ES-F{submission.pk}', '\n'.join(lines),
        settings.DEFAULT_FROM_EMAIL, [settings.ESICOM_ENQUIRY_EMAIL],
    )
    try:
        if attach:
            with attachment.open('rb') as handle:
                email.attach(Path(attachment.name).name, handle.read(), mimetypes.guess_type(attachment.name)[0])
        email.send(fail_silently=False)
    except Exception:
        logger.exception('File submission %s saved but the email failed.', submission.pk)


def _discard_submission(submission, converted_path):
    if converted_path and converted_path.exists():
        converted_path.unlink()
    if submission.pk:
        submission.delete()
        return
    for file_field in (submission.uploaded_file, submission.converted_file):
        if file_field:
            file_field.delete(save=False)


def download_submission_attachment(request, pk, file_kind):
    submission = get_object_or_404(FileSubmission, pk=pk)
    if file_kind == 'original':
        file_field = submission.uploaded_file
    elif file_kind == 'converted' and submission.converted_file:
        file_field = submission.converted_file
    else:
        raise Http404
    return _file_response(file_field)


def _file_response(file_field):
    file_name = Path(file_field.name).name
    content_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'
    response = FileResponse(file_field.open('rb'), as_attachment=True, filename=file_name, content_type=content_type)
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@csrf_exempt
@require_POST
def create_quote(request):
    # Small IP-based throttle; configure a shared cache (e.g. Redis) for production multi-worker deployments.
    ip = request.META.get('REMOTE_ADDR', 'unknown')
    key = f'esicom-quote:{ip}'
    count = cache.get(key, 0)
    if count >= 8:
        return JsonResponse({'detail': 'Too many enquiries from this connection. Please email us instead.'}, status=429)
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'detail': 'Please submit a valid enquiry.'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'detail': 'Please submit a valid enquiry.'}, status=400)
    if str(payload.get('website', '')).strip():
        return JsonResponse({'detail': 'Enquiry received.'}, status=200)
    name = str(payload.get('name', '')).strip()
    company = str(payload.get('company', '')).strip()
    phone = str(payload.get('phone', '')).strip()
    email = str(payload.get('email', '')).strip()
    needs = str(payload.get('needs', '')).strip()
    quantity = str(payload.get('quantity', '')).strip()
    source = str(payload.get('source', 'website')).strip()[:40] or 'website'
    if len(name) < 2 or len(name) > 120:
        return JsonResponse({'detail': 'Enter your name (at least 2 characters).'}, status=400)
    if not phone or len(phone) > 40 or not re.fullmatch(r'[+()\-\d\s.]{5,40}', phone):
        return JsonResponse({'detail': 'Enter a valid phone number.'}, status=400)
    if email and (len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email)):
        return JsonResponse({'detail': 'Enter a valid email address.'}, status=400)
    if len(needs) < 8 or len(needs) > 5000:
        return JsonResponse({'detail': 'Please describe what you need (8–5000 characters).'}, status=400)
    if len(company) > 160 or len(quantity) > 100:
        return JsonResponse({'detail': 'One of the fields is too long.'}, status=400)
    required_date = None
    raw_date = str(payload.get('date', '')).strip()
    if raw_date:
        try:
            required_date = date.fromisoformat(raw_date)
        except ValueError:
            return JsonResponse({'detail': 'Enter a valid required date.'}, status=400)
    quote = QuoteRequest.objects.create(name=name, company=company, phone=phone, email=email, needs=needs, quantity=quantity, required_date=required_date, source=source)
    cache.set(key, count + 1, timeout=3600)
    subject = f'New Esicom website quotation request #{quote.pk}'
    body = '\n'.join([
        f'Enquiry reference: #{quote.pk}', f'Name: {name}', f'Company: {company or "Not provided"}',
        f'Phone: {phone}', f'Email: {email or "Not provided"}', f'Quantity: {quantity or "Not provided"}',
        f'Required date: {required_date or "Not provided"}', '', 'Request details:', needs,
    ])
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.ESICOM_ENQUIRY_EMAIL], fail_silently=False)
    except Exception:
        # Persist the enquiry even if email credentials or the mail server are not configured.
        logger.exception('Quote request %s was saved but notification email failed.', quote.pk)
    return JsonResponse({'ok': True, 'reference': quote.pk}, status=201)
