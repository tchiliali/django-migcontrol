from django.db import models  # noqa
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.admin.edit_handlers import StreamFieldPanel
from wagtail.core import blocks
from wagtail.core.fields import StreamField
from wagtail.core.models import Page
from wagtail.images.blocks import ImageChooserBlock


class HomePage(Page):
    """
    This is the landing page
    """

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


class ArticleBase(models.Model):
    """
    This mixin can be reused in Page models of other applications that need
    the same structure.
    """

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

    class Meta:
        abstract = True


class Article(ArticleBase, Page):
    """
    We are using this model as a default article page. This covers the following
    page types:

    * Landing page
    * About page
    * Contact page
    * Donate page
    * Subscribe page
    * Data protection page
    * Imprint page
    """

    pass
