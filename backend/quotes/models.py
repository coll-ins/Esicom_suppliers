from datetime import timedelta
from pathlib import Path
from uuid import uuid4
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
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

PRODUCT_PAGE_CHOICES = [
    page for page in PAGE_CHOICES
    if page[0] not in {'home', 'about', 'contact'}
]


def validate_image_size(image):
    if image.size > MAX_IMAGE_SIZE:
        raise ValidationError('Images must be 8 MB or smaller.')


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


class CatalogItem(models.Model):
    page = models.CharField(max_length=40, choices=PRODUCT_PAGE_CHOICES)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.CharField(max_length=280)
    image = models.ImageField(
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

    def __str__(self):
        return self.name


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
