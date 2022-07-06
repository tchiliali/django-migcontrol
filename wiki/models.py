from django.db import models
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.admin.edit_handlers import StreamFieldPanel
from wagtail.core import blocks
from wagtail.core.fields import RichTextField
from wagtail.core.fields import StreamField
from wagtail.core.models import Page
from wagtail.images.blocks import ImageChooserBlock


class WikiIndexPage(Page):
    template = "wiki/index.html"

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
        context["wiki_pages"] = self.get_children().live().type(WikiPage)
        return context


class WikiPage(Page):

    wordpress_post_id = models.PositiveSmallIntegerField(
        blank=True, null=True, editable=False
    )

    country = CountryField(
        verbose_name=_("country"),
        blank=True,
        multiple=True,
        default="",
    )

    short_description = models.TextField(blank=True, null=True)

    description = RichTextField()

    def get_display_country(self):
        return ", ".join(map(lambda c: c.name, self.country))

    content_panels = Page.content_panels + [
        FieldPanel("country"),
        FieldPanel("short_description"),
        FieldPanel("description"),
    ]
