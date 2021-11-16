from django.db import models  # noqa
from wagtail.core.models import Page


class HomePage(Page):
    """
    This is the landing page
    """

    pass


class Article(Page):
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
