from django.db import migrations, models
from django.core.validators import FileExtensionValidator
import quotes.models


PAGE_COPY = [
    ('home', 'A Nairobi supplier for the workday', 'Everything your office', 'needs.', 'Everyday stationery, printing supplies and branded merchandise. Tell us what you need; we’ll take it from there.'),
    ('office-supplies', 'OFFICE SUPPLIES', 'The everyday essentials.', '', 'Pens, paper, notebooks and office supplies for the workday.'),
    ('computer-consumables', 'COMPUTER CONSUMABLES', 'Keep work moving.', '', 'Toners, ink cartridges and computer essentials. Share your printer model and we’ll help you find the right fit.'),
    ('bulk-printing', 'BULK PRINTING', 'Let’s get your print job sorted.', '', 'Tell us what you’re printing, how many you need and when you need them.'),
    ('branding', 'CORPORATE BRANDING', 'Give your brand a useful life.', '', 'Branded shirts, business cards, diaries and practical merchandise. Bring your logo and tell us what you have in mind.'),
    ('about', 'ABOUT ESICOM SUPPLIERS', 'One local team for the workday.', '', 'We help Nairobi businesses source everyday office supplies, printing and branded merchandise.'),
    ('contact', 'CONTACT · REQUEST A QUOTE', 'What can we help you find?', '', 'Send us your list, product photo or print brief. Our team in Nairobi will take it from there.'),
    ('paper-filing', 'PAPER & FILING', 'Paper, pens and the rest.', '', 'Reams of copy paper, boxed stationery, files and folders. Let us know what your office needs.'),
    ('business-cards', 'BUSINESS CARDS', 'Business cards, made personal.', '', 'Tell us about the artwork, quantity and finish you have in mind.'),
    ('branded-apparel', 'BRANDED APPAREL', 'Merchandise made yours.', '', 'Bring your logo and team requirements. We’ll discuss apparel and other branded items with you.'),
    ('diaries-asset-tags', 'DIARIES & ASSET TAGS', 'Useful things, with your name on them.', '', 'Branded diaries, stationery and asset tags for your organisation.'),
]


def create_default_page_copy(apps, schema_editor):
    PageContent = apps.get_model('quotes', 'PageContent')
    PageContent.objects.using(schema_editor.connection.alias).bulk_create([
        PageContent(page=page, eyebrow=eyebrow, title=title, highlight=highlight, intro=intro)
        for page, eyebrow, title, highlight, intro in PAGE_COPY
    ])


class Migration(migrations.Migration):
    dependencies = [('quotes', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='PageContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page', models.CharField(choices=[
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
                ], max_length=40, unique=True)),
                ('eyebrow', models.CharField(max_length=100)),
                ('title', models.CharField(max_length=180)),
                ('highlight', models.CharField(blank=True, max_length=80)),
                ('intro', models.TextField(max_length=500)),
                ('hero_image', models.ImageField(blank=True, help_text='Optional. Upload an authentic Esicom photo to replace the stock image.', upload_to=quotes.models.content_image_path, validators=[
                    FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']),
                    quotes.models.validate_image_size,
                ])),
                ('is_published', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'website page',
                'verbose_name_plural': 'website pages',
                'ordering': ['page'],
            },
        ),
        migrations.CreateModel(
            name='CatalogItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page', models.CharField(choices=[
                    ('office-supplies', 'Office supplies'),
                    ('computer-consumables', 'Computer consumables'),
                    ('bulk-printing', 'Bulk printing'),
                    ('branding', 'Corporate branding'),
                    ('paper-filing', 'Paper & filing'),
                    ('business-cards', 'Business cards'),
                    ('branded-apparel', 'Branded apparel'),
                    ('diaries-asset-tags', 'Diaries & asset tags'),
                ], max_length=40)),
                ('name', models.CharField(max_length=120)),
                ('slug', models.SlugField(blank=True, max_length=140, unique=True)),
                ('description', models.CharField(max_length=280)),
                ('image', models.ImageField(help_text='Upload a clear photo of the actual product or branded merchandise.', upload_to=quotes.models.content_image_path, validators=[
                    FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']),
                    quotes.models.validate_image_size,
                ])),
                ('is_featured', models.BooleanField(default=True, help_text='Featured products appear on the homepage as well as their category page.')),
                ('is_published', models.BooleanField(default=True)),
                ('display_order', models.PositiveSmallIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'product / merchandise',
                'verbose_name_plural': 'products & merchandise',
                'ordering': ['display_order', 'name'],
            },
        ),
        migrations.RunPython(create_default_page_copy, migrations.RunPython.noop),
    ]
