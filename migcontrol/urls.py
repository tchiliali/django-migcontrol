from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include
from django.urls import path
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.core import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail_footnotes import urls as footnotes_urls

from blog import urls as blog_urls
from search import views as search_views

urlpatterns = [
    path("documents/", include(wagtaildocs_urls)),
    path("footnotes/", include(footnotes_urls)),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# Translatable URLs
# These will be available under a language code prefix. For example /en/search/
urlpatterns += i18n_patterns(
    path("_admin/", admin.site.urls),
    path("wagtail/", include(wagtailadmin_urls)),
    path("search/", search_views.search, name="search"),
    path("blog/", include(blog_urls)),
    path("", include(wagtail_urls)),
)
