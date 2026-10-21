from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import CatalogItem, FileSubmission, PageContent, PageSection, QuoteRequest, SitePhoto

admin.site.site_header = 'Esicom Suppliers — Website Editor'
admin.site.site_title = 'Esicom Website Editor'
admin.site.index_title = 'Manage your website content'


@admin.register(SitePhoto)
class SitePhotoAdmin(admin.ModelAdmin):
    list_display = ('get_source_path_display', 'image_preview', 'updated_at')
    readonly_fields = ('image_preview', 'updated_at')
    fields = ('source_path', 'image', 'image_preview', 'updated_at')

    @admin.display(description='Current photo')
    def image_preview(self, obj):
        if not obj or not obj.image:
            return 'No photo uploaded'
        return format_html(
            '<img src="{}" alt="" style="max-width:180px;max-height:110px;object-fit:cover;border-radius:8px">',
            obj.image.url,
        )

    def delete_queryset(self, request, queryset):
        for photo in queryset:
            photo.delete()


@admin.register(PageSection)
class PageSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'page', 'is_published', 'display_order', 'updated_at')
    list_filter = ('page', 'is_published')
    search_fields = ('title', 'body')
    list_editable = ('is_published', 'display_order')
    readonly_fields = ('updated_at',)
    fieldsets = (
        ('What visitors will see', {
            'fields': ('page', 'title', 'body', 'image'),
            'description': 'Add an optional section to a page. Leave the photo blank if you only want text.',
        }),
        ('Optional button', {'fields': ('button_text', 'button_url')}),
        ('Visibility and order', {'fields': ('is_published', 'display_order', 'updated_at')}),
    )

    def delete_queryset(self, request, queryset):
        for section in queryset:
            section.delete()


@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    list_display = ('get_page_display', 'title', 'is_published', 'updated_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'intro')
    readonly_fields = ('updated_at',)
    fieldsets = (
        ('Page copy', {'fields': ('page', 'eyebrow', 'title', 'highlight', 'intro', 'is_published')}),
        ('Page photo', {'fields': ('hero_image',)}),
        ('Last updated', {'fields': ('updated_at',)}),
    )

    def delete_queryset(self, request, queryset):
        for page in queryset:
            page.delete()


@admin.register(CatalogItem)
class CatalogItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'page', 'is_featured', 'is_published', 'display_order', 'updated_at')
    list_filter = ('page', 'is_featured', 'is_published')
    search_fields = ('name', 'description', 'slug')
    list_editable = ('is_featured', 'is_published', 'display_order')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('updated_at',)
    fieldsets = (
        ('Product details', {'fields': ('name', 'slug', 'page', 'description', 'image')}),
        ('Website placement', {'fields': ('is_featured', 'is_published', 'display_order')}),
        ('Last updated', {'fields': ('updated_at',)}),
    )

    def delete_queryset(self, request, queryset):
        for item in queryset:
            item.delete()


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'name', 'company', 'phone', 'email', 'status')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'company', 'phone', 'email', 'needs')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 30


@admin.register(FileSubmission)
class FileSubmissionAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'original_filename', 'delivery_method', 'name', 'phone')
    list_filter = ('created_at',)
    search_fields = ('original_filename', 'name', 'phone', 'note')
    readonly_fields = ('created_at', 'delivery_consent', 'original_download', 'converted_download')
    actions = None
    fieldsets = (
        ('Submission', {'fields': ('created_at', 'delivery_method', 'delivery_consent', 'original_filename', 'original_download', 'converted_download')}),
        ('Contact details', {'fields': ('name', 'phone', 'note')}),
    )
    list_per_page = 30

    @admin.display(description='Original file')
    def original_download(self, obj):
        url = reverse('file_submission_attachment', args=(obj.pk, 'original'))
        return format_html('<a href="{}">Download original file</a>', url)

    @admin.display(description='Converted file')
    def converted_download(self, obj):
        if not obj.converted_file:
            return 'No converted file'
        url = reverse('file_submission_attachment', args=(obj.pk, 'converted'))
        return format_html('<a href="{}">Download converted file</a>', url)

    def has_add_permission(self, request):
        return False

    def delete_queryset(self, request, queryset):
        for submission in queryset.iterator():
            submission.delete()
