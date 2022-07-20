from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from modelcluster.fields import ParentalKey
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.admin.edit_handlers import InlinePanel
from wagtail.admin.edit_handlers import StreamFieldPanel
from wagtail.core import blocks
from wagtail.core.fields import RichTextField
from wagtail.core.fields import StreamField
from wagtail.core.models import Page
from wagtail.images.blocks import ImageChooserBlock
from wagtail.snippets.edit_handlers import SnippetChooserPanel


class ArchiveIndexPage(Page):
    template = "archive/index.html"

    body = StreamField(
        [
            ("heading", blocks.CharBlock(classname="full title")),
            ("paragraph", blocks.RichTextBlock()),
            ("image", ImageChooserBlock()),
        ],
        verbose_name="body",
        blank=True,
        help_text="The main contents of the page",
    )
    content_panels = [
        FieldPanel("title", classname="full title"),
        StreamFieldPanel("body"),
    ]

    def get_context(self, request):
        context = super(ArchiveIndexPage, self).get_context(request)
        context["archive_pages"] = self.get_children().live().type(ArchivePage)
        return context


class LocationPage(Page):

    name = models.CharField(
        verbose_name=_("location name"),
        help_text=_("Typically a city name or region"),
        max_length=255,
    )

    country = CountryField(verbose_name=_("country"))

    content_panels = [
        FieldPanel("name"),
        FieldPanel("country"),
    ]

    def __str__(self):
        return f"{self.name} ({self.country.code})"


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

    def get_display_country(self):
        return ", ".join(map(lambda c: c.name, self.country))

    def get_display_locations(self):
        return ", ".join(str(ll.location) for ll in self.locations.all())

    content_panels = Page.content_panels + [
        FieldPanel("organization_type"),
        FieldPanel("country"),
        FieldPanel("description"),
        InlinePanel("locations", label="locations"),
    ]
