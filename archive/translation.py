from modeltranslation.translator import register
from modeltranslation_wagtail.translator import TranslationOptions

from .models import ArchiveIndexPage
from .models import ArchivePage
from .models import LocationPage


@register(LocationPage)
class LocationPageTR(TranslationOptions):
    fields = ("name",)


@register(ArchiveIndexPage)
class ArchiveIndexPageTR(TranslationOptions):
    fields = ("body",)


@register(ArchivePage)
class ArchivePageTR(TranslationOptions):
    fields = ("description", "short_description")
