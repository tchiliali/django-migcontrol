from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.admin.edit_handlers import InlinePanel
from wagtail.admin.edit_handlers import StreamFieldPanel
from wagtail.core import blocks
from wagtail.core.fields import RichTextField
from wagtail.core.fields import StreamField
from wagtail.core.models import Page
from wagtail.core.models.i18n import TranslatableMixin
from wagtail.core.templatetags.wagtailcore_tags import richtext
from wagtail.images import get_image_model_string
from wagtail.images.blocks import ImageChooserBlock
from wagtail.snippets.edit_handlers import SnippetChooserPanel
from wagtail.snippets.models import register_snippet


class LibraryIndexPage(Page):
    template = "library/index.html"

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
        context = super().get_context(request)
        context["media_pages"] = self.get_children().live().type(MediaPage)
        return context


class MediaPage(Page):

    body = RichTextField()

    feature_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=("feature image"),
    )

    authors = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        verbose_name=_("authors"),
    )

    full_title = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        verbose_name=_("full title"),
    )

    publisher = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        verbose_name=_("publisher or journal"),
    )

    year = models.PositiveSmallIntegerField(
        default=timezone.now().year,
        blank=True,
        null=True,
        verbose_name=_("year of publication"),
    )

    media_type = models.CharField(
        max_length=128,
        verbose_name=_("media type"),
        blank=True,
        null=True,
    )

    link = models.URLField(
        max_length=1024,
        blank=True,
        null=True,
        verbose_name=_("Link (URL)"),
    )

    def get_display_country(self):
        return ", ".join(map(lambda c: c.name, self.country))

    def get_display_locations(self):
        return ", ".join(str(ll.location) for ll in self.locations.all())

    def get_body(self):  # noqa: max-complexity=11
        body = richtext(self.body)
        return str(body)

    content_panels = Page.content_panels + [
        FieldPanel("body"),
        FieldPanel("authors"),
        FieldPanel("full_title"),
        FieldPanel("publisher"),
        FieldPanel("year"),
        FieldPanel("media_type"),
        FieldPanel("link"),
        InlinePanel("regions", label="regions"),
        InlinePanel("topics", label="topics"),
    ]


@register_snippet
class RegionSnippet(TranslatableMixin, models.Model):

    name = models.CharField(
        verbose_name=_("region name"),
        help_text=_("Some geographical area, may intersect with other areas"),
        max_length=255,
    )

    panels = [
        FieldPanel("name"),
    ]

    def __str__(self):
        return f"{self.name}"


@register_snippet
class TopicSnippet(TranslatableMixin, models.Model):

    name = models.CharField(
        verbose_name=_("topic name"),
        help_text=_("A topic for the library, can intersect with other topics"),
        max_length=255,
    )

    panels = [
        FieldPanel("name"),
    ]

    def __str__(self):
        return f"{self.name}"


class MediaPageRegion(models.Model):
    page = ParentalKey(
        "library.MediaPage", on_delete=models.CASCADE, related_name="regions"
    )
    region = models.ForeignKey(
        "library.RegionSnippet", on_delete=models.CASCADE, related_name="media"
    )

    panels = [
        SnippetChooserPanel("region"),
    ]

    class Meta:
        unique_together = ("page", "region")


class MediaPageTopic(models.Model):
    page = ParentalKey(
        "library.MediaPage", on_delete=models.CASCADE, related_name="topics"
    )
    topic = models.ForeignKey(
        "library.TopicSnippet", on_delete=models.CASCADE, related_name="media"
    )

    panels = [
        SnippetChooserPanel("topic"),
    ]

    class Meta:
        unique_together = ("page", "topic")
