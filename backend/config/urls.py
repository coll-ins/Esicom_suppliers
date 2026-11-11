from django.contrib import admin
from django.urls import include, path
from quotes.views import (
    create_file_submission,
    create_page_section,
    create_quote,
    download_submission_attachment,
    health,
    private_media_not_found,
    public_media,
    site_content,
    upload_page,
    visual_edit_api,
    visual_editor,
)

urlpatterns = [
    path('admin/file-submissions/<int:pk>/<str:file_kind>/', admin.site.admin_view(
        download_submission_attachment
    ), name='file_submission_attachment'),
    path('admin/visual-editor/', visual_editor, name='visual_editor'),
    path('admin/', admin.site.urls),
    path('upload/', upload_page, name='upload_page'),
    path('api/ledger/', include('ledger.urls')),
    path('api/quote/', create_quote, name='create_quote'),
    path('api/file-submissions/', create_file_submission, name='create_file_submission'),
    path('api/health/', health, name='health'),
    path('api/page-sections/<str:page>/', create_page_section, name='create_page_section'),
    path('api/site-content/', site_content, name='site_content'),
    path('api/visual-edits/<str:page>/', visual_edit_api, name='visual_edit_api'),
    path('media/private/<path:path>', private_media_not_found, name='private_media_not_found'),
    path('media/<path:path>', public_media, name='public_media'),
]
