from modeltranslation.translator import register
from modeltranslation_wagtail.translator import TranslationOptions

from .models import ArchivePage
from .models import LocationPage


@register(LocationPage)
class LocationPageTR(TranslationOptions):
    fields = ("name",)


@register(ArchivePage)
class ArchivePageTR(TranslationOptions):
    fields = ("description",)
