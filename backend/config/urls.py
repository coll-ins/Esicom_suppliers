from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from quotes.views import (
    create_file_submission,
    create_quote,
    download_file_submission,
    download_submission_attachment,
    file_upload_qr,
    health,
    private_media_not_found,
    site_content,
)

urlpatterns = [
    path('admin/file-submissions/<int:pk>/<str:file_kind>/', admin.site.admin_view(
        download_submission_attachment
    ), name='file_submission_attachment'),
    path('admin/', admin.site.urls),
    path('api/quote/', create_quote, name='create_quote'),
    path('api/file-submissions/', create_file_submission, name='create_file_submission'),
    path('api/file-submissions/<uuid:token>/download/', download_file_submission, name='download_file_submission'),
    path('api/file-upload-qr/', file_upload_qr, name='file_upload_qr'),
    path('api/health/', health, name='health'),
    path('api/site-content/', site_content, name='site_content'),
]

if settings.DEBUG:
    urlpatterns += [path('media/private/<path:path>', private_media_not_found)]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
