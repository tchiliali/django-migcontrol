from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from modelcluster.fields import ParentalKey
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.admin.edit_handlers import InlinePanel
from wagtail.core.fields import RichTextField
from wagtail.core.models import Page
from wagtail.snippets.edit_handlers import SnippetChooserPanel

from home.models import Article


class ArchiveIndexPage(Article):
    template = "archive/index.html"


class LocationPage(Page):

    name = models.CharField(
        verbose_name=_("location name"),
        help_text=_("Typically a city name or region"),
        max_length=255,
    )

    country = CountryField(verbose_name=_("country"))

    def __str__(self):
        return f"{self.name} ({self.country})"


class ArchivePageLocation(models.Model):
    page = ParentalKey(
        "archive.ArchivePage", on_delete=models.CASCADE, related_name="locations"
    )
    location = models.ForeignKey(
        "archive.LocationPage", on_delete=models.CASCADE, related_name="archivepages"
    )

    panels = [
        SnippetChooserPanel("location"),
    ]

    class Meta:
        unique_together = ("page", "location")


class ArchivePage(Page):

    wordpress_post_id = models.PositiveSmallIntegerField(
        blank=True, null=True, editable=False
    )

    organization_type = models.CharField(
        verbose_name=_("organization type"),
        blank=True,
        null=True,
        max_length=255,
    )

    country = CountryField(
        verbose_name=_("country"),
        blank=True,
        multiple=True,
        default="",
    )

    short_description = models.TextField(blank=True, null=True)

    description = RichTextField()

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        # limit_choices_to=limit_author_choices,
        verbose_name=_("Author"),
        on_delete=models.SET_NULL,
        related_name="author_archives",
    )

    content_panels = Page.content_panels + [
        FieldPanel("organization_type"),
        FieldPanel("country"),
        FieldPanel("short_description"),
        FieldPanel("description"),
        InlinePanel("locations", label="locations"),
    ]
