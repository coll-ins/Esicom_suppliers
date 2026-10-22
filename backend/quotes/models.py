from datetime import timedelta
from pathlib import Path
import re
from uuid import uuid4
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils.text import slugify
from django.utils import timezone

MAX_IMAGE_SIZE = 8 * 1024 * 1024

PAGE_CHOICES = [
    ('home', 'Home page'),
    ('office-supplies', 'Office supplies'),
    ('computer-consumables', 'Computer consumables'),
    ('bulk-printing', 'Bulk printing'),
    ('branding', 'Corporate branding'),
    ('about', 'About Esicom'),
    ('contact', 'Contact'),
    ('paper-filing', 'Paper & filing'),
    ('business-cards', 'Business cards'),
    ('branded-apparel', 'Branded apparel'),
    ('diaries-asset-tags', 'Diaries & asset tags'),
]

VISUAL_PAGE_CHOICES = [('global', 'Site header and footer'), *PAGE_CHOICES]

PRODUCT_PAGE_CHOICES = [
    page for page in PAGE_CHOICES
    if page[0] not in {'home', 'about', 'contact'}
]

SITE_PHOTO_CHOICES = [
    ('/images/photography/apparel.webp', 'Branded apparel photo'),
    ('/images/photography/boxed-supplies.jpg', 'Boxed office supplies photo'),
    ('/images/photography/computer.webp', 'Computer workspace photo'),
    ('/images/photography/meeting-room.webp', 'Meeting room photo'),
    ('/images/photography/notebook.webp', 'Notebook photo'),
    ('/images/photography/printing.webp', 'Printing photo'),
    ('/images/photography/stationery-box.jpg', 'Stationery box photo'),
    ('/images/photography/stationery.webp', 'Stationery photo'),
    ('/images/photography/stock-boxed-pens.webp', 'Packaged pens photo'),
    ('/images/photography/stock-copy-paper.webp', 'Copy paper photo'),
    ('/images/photography/stock-office-box.webp', 'Office supplies hero photo'),
    ('/images/photography/workspace.webp', 'Office workspace photo'),
]


def validate_image_size(image):
    if image.size > MAX_IMAGE_SIZE:
        raise ValidationError('Images must be 8 MB or smaller.')


def public_image_storage():
    from os import environ
    if environ.get('CLOUDINARY_URL'):
        from cloudinary_storage.storage import MediaCloudinaryStorage
        return MediaCloudinaryStorage()
    from django.core.files.storage import FileSystemStorage
    return FileSystemStorage()


def content_image_path(instance, filename):
    extension = Path(filename).suffix.lower()
    if isinstance(instance, CatalogItem):
        return f'catalog/{instance.category}/{uuid4().hex}{extension}'
    return f'pages/{uuid4().hex}{extension}'


class PageContent(models.Model):
    page = models.CharField(max_length=40, choices=PAGE_CHOICES, unique=True)
    eyebrow = models.CharField(max_length=100)
    title = models.CharField(max_length=180)
    highlight = models.CharField(max_length=80, blank=True)
    intro = models.TextField(max_length=500)
    hero_image = models.ImageField(
        storage=public_image_storage,
        upload_to=content_image_path,
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), validate_image_size],
        help_text='Optional. Upload an authentic Esicom photo to replace the stock image.',
    )
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['page']
        verbose_name = 'website page'
        verbose_name_plural = 'website pages'

    def __str__(self):
        return self.get_page_display()

    def save(self, *args, **kwargs):
        old_name = None
        if self.pk:
            old_name = PageContent.objects.filter(pk=self.pk).values_list('hero_image', flat=True).first()
        super().save(*args, **kwargs)
        if old_name and old_name != self.hero_image.name:
            self.hero_image.storage.delete(old_name)

    def delete(self, *args, **kwargs):
        if self.hero_image:
            self.hero_image.delete(save=False)
        return super().delete(*args, **kwargs)


class CatalogItem(models.Model):
    page = models.CharField(max_length=40, choices=PRODUCT_PAGE_CHOICES)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.CharField(max_length=280)
    image = models.ImageField(
        storage=public_image_storage,
        upload_to=content_image_path,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), validate_image_size],
        help_text='Upload a clear photo of the actual product or branded merchandise.',
    )
    is_featured = models.BooleanField(
        default=True,
        help_text='Featured products appear on the homepage as well as their category page.',
    )
    is_published = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'product / merchandise'
        verbose_name_plural = 'products & merchandise'

    def save(self, *args, **kwargs):
        old_name = None
        if self.pk:
            old_name = CatalogItem.objects.filter(pk=self.pk).values_list('image', flat=True).first()
        if not self.slug:
            base_slug = slugify(self.name)[:140] or 'product'
            candidate = base_slug
            suffix = 2
            while CatalogItem.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                ending = f'-{suffix}'
                candidate = f'{base_slug[:140 - len(ending)]}{ending}'
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)
        if old_name and old_name != self.image.name:
            self.image.storage.delete(old_name)

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        self.image.delete(save=False)
        return super().delete(*args, **kwargs)


class SitePhoto(models.Model):
    source_path = models.CharField(max_length=120, choices=SITE_PHOTO_CHOICES, unique=True)
    image = models.ImageField(
        storage=public_image_storage,
        upload_to=content_image_path,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), validate_image_size],
        help_text='Upload a JPG, PNG or WebP image no larger than 8 MB.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['source_path']
        verbose_name = 'website photo'
        verbose_name_plural = 'website photos'

    def __str__(self):
        return self.get_source_path_display()

    def save(self, *args, **kwargs):
        old_name = None
        if self.pk:
            old_name = SitePhoto.objects.filter(pk=self.pk).values_list('image', flat=True).first()
        super().save(*args, **kwargs)
        if old_name and old_name != self.image.name:
            self.image.storage.delete(old_name)

    def delete(self, *args, **kwargs):
        self.image.delete(save=False)
        return super().delete(*args, **kwargs)


class PageSection(models.Model):
    page = models.CharField(max_length=40, choices=PAGE_CHOICES)
    title = models.CharField(max_length=140)
    body = models.TextField(max_length=1600, blank=True)
    image = models.ImageField(
        storage=public_image_storage,
        upload_to=content_image_path,
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), validate_image_size],
        help_text='Optional. JPG, PNG or WebP, no larger than 8 MB.',
    )
    button_text = models.CharField(max_length=80, blank=True)
    button_url = models.CharField(
        max_length=300,
        blank=True,
        help_text='Optional. Use a website path such as /contact/ or a full https:// URL.',
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['page', 'display_order', 'id']
        verbose_name = 'extra page section'
        verbose_name_plural = 'extra page sections'

    def __str__(self):
        return f'{self.get_page_display()} — {self.title}'

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.core.validators import URLValidator

        if self.button_url and not self.button_url.startswith('/'):
            try:
                URLValidator(schemes=['http', 'https'])(self.button_url)
            except ValidationError as exc:
                raise ValidationError({'button_url': 'Enter a website path or an http/https URL.'}) from exc
        elif self.button_url.startswith('//'):
            raise ValidationError({'button_url': 'Enter a website path beginning with one slash, not two.'})

    def save(self, *args, **kwargs):
        old_name = None
        if self.pk:
            old_name = PageSection.objects.filter(pk=self.pk).values_list('image', flat=True).first()
        super().save(*args, **kwargs)
        if old_name and old_name != self.image.name:
            self.image.storage.delete(old_name)

    def delete(self, *args, **kwargs):
        if self.image:
            self.image.delete(save=False)
        return super().delete(*args, **kwargs)


class VisualEdit(models.Model):
    FONT_CHOICES = [
        ('', 'Keep the website default'),
        ('Manrope', 'Manrope'),
        ('DM Sans', 'DM Sans'),
        ('Georgia', 'Georgia'),
        ('Arial', 'Arial'),
        ('system-ui', 'System default'),
    ]
    page = models.CharField(max_length=40, choices=VISUAL_PAGE_CHOICES)
    selector = models.CharField(max_length=1200)
    text_value = models.TextField(blank=True)
    text_enabled = models.BooleanField(default=False)
    image = models.ImageField(
        storage=public_image_storage,
        upload_to=content_image_path,
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), validate_image_size],
    )
    font_family = models.CharField(max_length=30, choices=FONT_CHOICES, blank=True)
    font_size = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(8), MaxValueValidator(96)],
    )
    text_color = models.CharField(
        max_length=7,
        blank=True,
        validators=[RegexValidator(r'^#[0-9a-fA-F]{6}$', 'Enter a hex colour such as #183c35.')],
    )
    hidden = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['page', 'selector']
        constraints = [
            models.UniqueConstraint(fields=['page', 'selector'], name='unique_visual_edit_per_page_element'),
        ]

    def __str__(self):
        return f'{self.get_page_display()} — {self.selector[:60]}'

    def clean(self):
        from django.core.exceptions import ValidationError

        allowed_selector = re.fullmatch(
            r'(?:main\[data-content-page="(?P<main_page>[a-z0-9-]+)"\]|header|footer|\.topline)'
            r'(?:(?: > [a-z][a-z0-9-]*:nth-of-type\([1-9]\d*\))|'
            r'(?: \[data-editor-key="[a-z0-9-]+"\]))+',
            self.selector,
        )
        if not allowed_selector:
            raise ValidationError({'selector': 'Select an element from the visual preview.'})
        main_page = allowed_selector.group('main_page')
        if (main_page and main_page != self.page) or (not main_page and self.page != 'global'):
            raise ValidationError({'page': 'This visual change belongs to a different page.'})

    def save(self, *args, **kwargs):
        old_name = None
        if self.pk:
            old_name = VisualEdit.objects.filter(pk=self.pk).values_list('image', flat=True).first()
        self.full_clean()
        super().save(*args, **kwargs)
        if old_name and old_name != self.image.name:
            self.image.storage.delete(old_name)

    def delete(self, *args, **kwargs):
        if self.image:
            self.image.delete(save=False)
        return super().delete(*args, **kwargs)


class QuoteRequest(models.Model):
    STATUS_CHOICES = [('new', 'New'), ('contacted', 'Contacted'), ('quoted', 'Quoted'), ('closed', 'Closed')]
    name = models.CharField(max_length=120)
    company = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=40)
    email = models.EmailField(blank=True)
    needs = models.TextField(max_length=5000)
    quantity = models.CharField(max_length=100, blank=True)
    required_date = models.DateField(null=True, blank=True)
    source = models.CharField(max_length=40, default='website')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return f'{self.name} — {self.created_at:%Y-%m-%d %H:%M}'


def submission_file_path(instance, filename):
    safe_name = filename.replace('\\', '/').split('/')[-1]
    return f'private/file-submissions/{instance.download_token}/{safe_name}'


def file_submission_expiry():
    return timezone.now() + timedelta(days=7)


class FileSubmission(models.Model):
    DELIVERY_CHOICES = [('email', 'Email attachment'), ('whatsapp', 'WhatsApp share')]
    download_token = models.UUIDField(default=uuid4, unique=True, editable=False)
    original_filename = models.CharField(max_length=255)
    uploaded_file = models.FileField(upload_to=submission_file_path)
    converted_file = models.FileField(upload_to=submission_file_path, blank=True)
    delivery_method = models.CharField(max_length=12, choices=DELIVERY_CHOICES, default='email')
    delivery_consent = models.BooleanField(default=False)
    name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'file submission'
        verbose_name_plural = 'file submissions'

    def __str__(self):
        return f'{self.original_filename} — {self.created_at:%Y-%m-%d %H:%M}'

    def delete(self, *args, **kwargs):
        for field in (self.uploaded_file, self.converted_file):
            if field:
                field.delete(save=False)
        return super().delete(*args, **kwargs)
