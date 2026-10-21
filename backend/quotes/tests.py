import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf as fitz
from PIL import Image
from django.core.cache import cache
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from .models import CatalogItem, FileSubmission, PageContent, PageSection, QuoteRequest, SitePhoto, VisualEdit


class QuoteAPITests(TestCase):
    def setUp(self):
        cache.clear()

    def test_health_endpoint(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_only_public_content_media_is_served(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            public_file = Path(media_root) / 'pages' / 'hero.png'
            private_file = Path(media_root) / 'private' / 'file-submissions' / 'customer.png'
            public_file.parent.mkdir(parents=True)
            private_file.parent.mkdir(parents=True)
            public_file.write_bytes(b'public image')
            private_file.write_bytes(b'private submission')

            public_response = self.client.get('/media/pages/hero.png')
            self.assertEqual(public_response.status_code, 200)
            self.assertEqual(b''.join(public_response.streaming_content), b'public image')
            public_response.close()

            self.assertEqual(self.client.get('/media/private/file-submissions/customer.png').status_code, 404)
            self.assertEqual(self.client.get('/media/pages/../private/file-submissions/customer.png').status_code, 404)

    def test_site_content_exposes_published_page_copy(self):
        response = self.client.get('/api/site-content/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['pages']['home']['title'], 'Everything your office')
        self.assertIn('office-supplies', response.json()['pages'])
        self.assertEqual(response.json()['products'], [])
        self.assertEqual(response.json()['sections'], [])
        self.assertEqual(response.json()['photos'], {})

    def test_site_content_exposes_only_published_sections_and_photo_replacements(self):
        PageSection.objects.create(
            page='home',
            title='New homepage message',
            body='A useful update for customers.',
        )
        PageSection.objects.create(
            page='home',
            title='Draft message',
            is_published=False,
        )
        SitePhoto.objects.create(
            source_path='/images/photography/apparel.webp',
            image='pages/new-apparel-photo.webp',
        )

        response = self.client.get('/api/site-content/')
        content = response.json()

        self.assertEqual(len(content['sections']), 1)
        self.assertEqual(content['sections'][0]['title'], 'New homepage message')
        self.assertEqual(
            content['photos']['/images/photography/apparel.webp'],
            '/media/pages/new-apparel-photo.webp',
        )

    def test_unpublished_page_copy_is_not_public(self):
        PageContent.objects.filter(page='home').update(is_published=False)
        response = self.client.get('/api/site-content/')
        self.assertNotIn('home', response.json()['pages'])

    def test_only_published_catalog_items_are_public(self):
        CatalogItem.objects.create(
            page='office-supplies',
            name='Box of pens',
            description='Packaged pens for your team.',
            image='catalog/box-of-pens.webp',
        )
        CatalogItem.objects.create(
            page='office-supplies',
            name='Draft item',
            description='Not ready to publish.',
            image='catalog/draft.webp',
            is_published=False,
        )
        response = self.client.get('/api/site-content/')
        self.assertEqual(len(response.json()['products']), 1)
        self.assertEqual(response.json()['products'][0]['name'], 'Box of pens')
        self.assertTrue(response.json()['products'][0]['image'].endswith('/media/catalog/box-of-pens.webp'))

    def test_site_content_is_read_only(self):
        response = self.client.post('/api/site-content/', data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 405)

    def test_visual_editor_requires_staff_login(self):
        response = self.client.get('/admin/visual-editor/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.headers['Location'])
        response = self.client.post('/api/visual-edits/home/', {'selector': 'main'})
        self.assertEqual(response.status_code, 302)

    def test_staff_visual_editor_renders_the_live_page_preview(self):
        user = get_user_model().objects.create_user(
            username='site-editor',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(user)
        response = self.client.get('/admin/visual-editor/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Live website preview')
        self.assertContains(response, 'click wording or a photo')
        self.assertContains(response, 'http://127.0.0.1:4174')
        self.assertContains(self.client.get('/admin/'), 'Open visual website editor')

    def test_staff_can_save_and_publish_a_visual_text_change(self):
        user = get_user_model().objects.create_user(
            username='site-editor',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(user)
        selector = 'main[data-content-page="home"] > section:nth-of-type(1) > div:nth-of-type(1)'
        response = self.client.post('/api/visual-edits/home/', {
            'selector': selector,
            'text': 'Updated homepage copy',
            'text_enabled': 'true',
            'font_family': 'Manrope',
            'font_size': '24',
            'text_color': '#183c35',
            'hidden': 'false',
        })
        self.assertEqual(response.status_code, 200)
        edit = VisualEdit.objects.get(page='home', selector=selector)
        self.assertEqual(edit.text_value, 'Updated homepage copy')
        self.assertEqual(edit.font_size, 24)
        public_content = self.client.get('/api/site-content/').json()
        self.assertEqual(public_content['visual_edits'][0]['text'], 'Updated homepage copy')

    def test_header_visual_changes_are_shared_across_all_pages(self):
        user = get_user_model().objects.create_user(
            username='site-editor',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(user)
        selector = 'header > div:nth-of-type(1) > a:nth-of-type(1)'
        response = self.client.post('/api/visual-edits/home/', {
            'selector': selector,
            'text': 'Updated brand label',
            'text_enabled': 'true',
        })
        self.assertEqual(response.status_code, 200)
        edit = VisualEdit.objects.get(selector=selector)
        self.assertEqual(edit.page, 'global')
        self.assertIn(
            selector,
            [change['selector'] for change in self.client.get('/api/visual-edits/contact/').json()['edits']],
        )

    def test_staff_can_add_a_page_section_from_the_visual_editor(self):
        user = get_user_model().objects.create_user(
            username='site-editor',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(user)
        response = self.client.post('/api/page-sections/home/', {
            'title': 'A new customer message',
            'body': 'New wording added from the visual editor.',
            'button_text': 'Contact us',
            'button_url': '/contact/',
        })
        self.assertEqual(response.status_code, 201)
        public_content = self.client.get('/api/site-content/').json()
        self.assertEqual(public_content['sections'][0]['title'], 'A new customer message')
        self.assertEqual(public_content['sections'][0]['body'], 'New wording added from the visual editor.')

    def test_staff_can_replace_a_photo_from_the_visual_editor(self):
        user = get_user_model().objects.create_user(
            username='site-editor',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(user)
        image_data = BytesIO()
        Image.new('RGB', (8, 8), (20, 90, 50)).save(image_data, format='PNG')
        selector = (
            'main[data-content-page="home"] > section:nth-of-type(1) > '
            'div:nth-of-type(1) > div:nth-of-type(2) > img:nth-of-type(1)'
        )
        response = self.client.post('/api/visual-edits/home/', {
            'selector': selector,
            'text_enabled': 'false',
            'font_family': '',
            'font_size': '',
            'text_color': '',
            'hidden': 'false',
            'image': SimpleUploadedFile('new-photo.png', image_data.getvalue(), content_type='image/png'),
        })
        self.assertEqual(response.status_code, 200)
        public_edit = self.client.get('/api/site-content/').json()['visual_edits'][0]
        self.assertTrue(public_edit['image'].startswith('/media/pages/'))

    def test_visual_edit_rejects_arbitrary_selector(self):
        user = get_user_model().objects.create_user(
            username='site-editor',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(user)
        response = self.client.post('/api/visual-edits/home/', {
            'selector': 'body',
            'text': 'Invalid',
            'text_enabled': 'true',
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(VisualEdit.objects.count(), 0)

    def test_catalog_admin_requires_authentication(self):
        response = self.client.get('/admin/quotes/catalogitem/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.headers['Location'])

    def test_valid_quote_is_saved(self):
        payload = {
            'name': 'Test Customer',
            'company': 'Example Organisation',
            'phone': '0728942669',
            'email': 'customer@example.com',
            'needs': 'Bulk printing of business cards',
            'quantity': '250',
            'date': '2026-11-10',
            'source': 'website',
        }
        response = self.client.post('/api/quote/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['ok'])
        self.assertEqual(QuoteRequest.objects.count(), 1)
        quote = QuoteRequest.objects.get()
        self.assertEqual(quote.phone, '0728942669')
        self.assertEqual(quote.quantity, '250')
        self.assertEqual(str(quote.required_date), '2026-11-10')

    def test_invalid_json_is_rejected(self):
        response = self.client.post('/api/quote/', data='{bad', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(QuoteRequest.objects.count(), 0)

    def test_honeypot_does_not_save_quote(self):
        payload = {'website': 'bot-filled-this', 'name': 'Bot User', 'phone': '0728942669', 'needs': 'Spam enquiry details'}
        response = self.client.post('/api/quote/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(QuoteRequest.objects.count(), 0)

    def test_bad_phone_is_rejected(self):
        payload = {'name': 'Test Customer', 'phone': 'not-a-number', 'needs': 'Office supplies request'}
        response = self.client.post('/api/quote/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(QuoteRequest.objects.count(), 0)

    def test_get_is_not_allowed_for_quote_submission(self):
        response = self.client.get('/api/quote/')
        self.assertEqual(response.status_code, 405)


class FileSubmissionAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.media = TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media.name,
            ESICOM_PUBLIC_SITE_URL='https://esicom.example',
        )
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        self.media.cleanup()

    @staticmethod
    def png_file(name='artwork.png'):
        image_data = BytesIO()
        Image.new('RGBA', (12, 12), (220, 40, 30, 128)).save(image_data, format='PNG')
        return SimpleUploadedFile(name, image_data.getvalue(), content_type='image/png')

    @staticmethod
    def pdf_file(name='brief.pdf'):
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text((72, 72), 'Esicom test brief')
        data = pdf.tobytes()
        pdf.close()
        return SimpleUploadedFile(name, data, content_type='application/pdf')

    def test_upload_is_saved_and_available_from_private_download_link(self):
        response = self.client.post('/api/file-submissions/', {'file': self.png_file(), 'delivery_consent': 'on'})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['ok'])
        submission = FileSubmission.objects.get()
        self.assertTrue(submission.uploaded_file.name.startswith('private/file-submissions/'))
        self.assertEqual(self.client.get(submission.uploaded_file.url).status_code, 404)
        download = self.client.get(response.json()['download_url'])
        self.assertEqual(download.status_code, 200)
        self.assertIn('attachment;', download['Content-Disposition'])
        download.close()

    def test_email_delivery_attaches_the_uploaded_file(self):
        response = self.client.post('/api/file-submissions/', {'file': self.png_file(), 'delivery_consent': 'on'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['delivery'], 'email')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['esicomsuppliers@gmail.com'])
        self.assertEqual(len(mail.outbox[0].attachments), 1)
        attachment_name, attachment_data, content_type = mail.outbox[0].attachments[0]
        self.assertEqual(attachment_name, 'artwork.png')
        self.assertTrue(attachment_data.startswith(b'\x89PNG'))
        self.assertIn('is attached', mail.outbox[0].body)
        self.assertTrue(FileSubmission.objects.get().delivery_consent)

    def test_email_delivery_fails_explicitly_when_only_console_email_is_configured(self):
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'):
            response = self.client.post('/api/file-submissions/', {
                'file': self.png_file(),
                'delivery_consent': 'on',
            })
        self.assertEqual(response.status_code, 503)
        self.assertTrue(response.json()['saved'])
        self.assertIn('email is not configured', response.json()['detail'])
        self.assertEqual(FileSubmission.objects.count(), 1)

    def test_submission_requires_delivery_consent(self):
        response = self.client.post('/api/file-submissions/', {'file': self.png_file()})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FileSubmission.objects.count(), 0)

    def test_whatsapp_delivery_does_not_send_an_email(self):
        response = self.client.post('/api/file-submissions/', {
            'file': self.png_file(),
            'delivery': 'whatsapp',
            'delivery_consent': 'on',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['delivery'], 'whatsapp')
        self.assertEqual(mail.outbox, [])
        self.assertEqual(FileSubmission.objects.get().delivery_method, 'whatsapp')

    def test_email_attachment_size_limit_directs_large_files_to_whatsapp(self):
        response = self.client.post('/api/file-submissions/', {
            'file': SimpleUploadedFile('large.pdf', b'x' * (15 * 1024 * 1024 + 1)),
            'delivery': 'email',
            'delivery_consent': 'on',
        })
        self.assertEqual(response.status_code, 413)
        self.assertIn('Choose WhatsApp', response.json()['detail'])
        self.assertEqual(FileSubmission.objects.count(), 0)

    def test_image_can_be_converted_and_downloaded(self):
        response = self.client.post('/api/file-submissions/', {
            'file': self.png_file(),
            'conversion': 'webp',
            'delivery_consent': 'on',
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['converted'])
        self.assertTrue(response.json()['filename'].endswith('-converted.webp'))
        submission = FileSubmission.objects.get()
        self.assertTrue(submission.converted_file)
        download = self.client.get(response.json()['download_url'])
        self.assertEqual(download.status_code, 200)
        download.close()

    def test_pdf_can_be_converted_to_word(self):
        response = self.client.post('/api/file-submissions/', {
            'file': self.pdf_file(),
            'conversion': 'docx',
            'delivery_consent': 'on',
        })
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(response.json()['filename'].endswith('-converted.docx'))
        self.assertEqual(mail.outbox[-1].attachments[0][0], 'brief-converted.docx')
        download = self.client.get(response.json()['download_url'])
        self.assertEqual(download.status_code, 200)
        download.close()

    def test_file_type_must_match_actual_image_content(self):
        response = self.client.post('/api/file-submissions/', {
            'file': SimpleUploadedFile('fake.jpg', b'%PDF-not-a-jpeg'),
            'delivery_consent': 'on',
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FileSubmission.objects.count(), 0)

    def test_conversion_must_be_supported_for_the_uploaded_file(self):
        response = self.client.post('/api/file-submissions/', {
            'file': self.pdf_file(),
            'conversion': 'webp',
            'delivery_consent': 'on',
        })
        self.assertEqual(response.status_code, 400)

    def test_download_link_remains_available_until_submission_is_deleted(self):
        submission = FileSubmission.objects.create(
            original_filename='artwork.png',
            uploaded_file=self.png_file(),
        )
        response = self.client.get(f'/api/file-submissions/{submission.download_token}/download/')
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_staff_deletion_removes_original_and_converted_files(self):
        submission = FileSubmission.objects.create(
            original_filename='artwork.png',
            uploaded_file=self.png_file(),
            converted_file=self.png_file('artwork-converted.png'),
        )
        original_name = submission.uploaded_file.name
        converted_name = submission.converted_file.name
        url = f'/admin/file-submissions/{submission.pk}/original/'
        staff = get_user_model().objects.create_superuser(
            username='file-delete-admin',
            email='delete-admin@example.com',
            password='test-password',
        )
        self.client.force_login(staff)
        response = self.client.post(f'/admin/quotes/filesubmission/{submission.pk}/delete/', {'post': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(FileSubmission.objects.filter(pk=submission.pk).exists())
        self.assertFalse(submission.uploaded_file.storage.exists(original_name))
        self.assertFalse(submission.converted_file.storage.exists(converted_name))
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_qr_endpoint_returns_png(self):
        response = self.client.get('/api/file-upload-qr/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertTrue(response.content.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_admin_can_download_private_upload_only_after_login(self):
        submission = FileSubmission.objects.create(
            original_filename='artwork.png',
            uploaded_file=self.png_file(),
        )
        url = f'/admin/file-submissions/{submission.pk}/original/'
        self.assertEqual(self.client.get(url).status_code, 302)
        staff = get_user_model().objects.create_superuser(
            username='file-admin',
            email='admin@example.com',
            password='test-password',
        )
        self.client.force_login(staff)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_upload_attempts_are_rate_limited_per_forwarded_client_ip(self):
        for _ in range(200):
            response = self.client.post(
                '/api/file-submissions/',
                {'file': SimpleUploadedFile('unsupported.txt', b'not a supported file'), 'delivery_consent': 'on'},
                HTTP_X_FORWARDED_FOR='198.51.100.10, 203.0.113.17',
            )
            self.assertEqual(response.status_code, 400)
        response = self.client.post(
            '/api/file-submissions/',
            {'file': self.png_file(), 'delivery_consent': 'on'},
            HTTP_X_FORWARDED_FOR='198.51.100.10, 203.0.113.17',
        )
        self.assertEqual(response.status_code, 429)
