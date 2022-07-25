import re

from django import template
from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.utils.safestring import mark_safe
from sorl.thumbnail import get_thumbnail
from wagtail.core.models import Page
from wagtail.core.models import Site
from wagtail.core.templatetags.wagtailcore_tags import pageurl


register = template.Library()


@register.simple_tag(takes_context=True)
def slugurl_localized(context, slug):
    """
    A language-aware version of Wagtail's slugurl tag

    Returns the URL for the page that has the given slug.

    First tries to find a page on the current site. If that fails or a request
    is not available in the context, then returns the URL for the first page
    that matches the slug on any site.
    """
    page = None
    try:
        site = Site.find_for_request(context["request"])
        current_site = site
    except KeyError:
        # No site object found - allow the fallback below to take place.
        pass
    else:
        if current_site is not None:
            page = Page.objects.in_site(current_site).filter(slug=slug).first()

    # If no page is found, fall back to searching the whole tree.
    if page is None:
        page = Page.objects.filter(slug=slug).first()

    if page:
        # call pageurl() instead of page.relative_url() here so we get the ``accepts_kwarg`` logic
        return pageurl(context, page.localized)


class StaticPath(str):
    def __new__(cls, path: str, storage: FileSystemStorage):
        obj = super().__new__(cls, path)
        obj.storage = storage
        return obj


storage = FileSystemStorage(location="/")


@register.simple_tag(takes_context=False)
def get_static_thumbnail(file_: str, geometry, *args, **kwargs):
    disk_path = finders.find(file_)
    if disk_path:
        return get_thumbnail(
            StaticPath(disk_path, storage),
            geometry,
            *args,
            **kwargs,
        )


@register.simple_tag(takes_context=True)
def get_site_root(context):
    # This returns a core.Page. The main menu needs to have the site.root_page
    # defined else will return an object attribute error ('str' object has no
    # attribute 'get_children')
    return Site.find_for_request(context["request"]).root_page.localized


@register.simple_tag(takes_context=False)
def get_page_by_slug(parent, slug):
    # This returns a core.Page. The main menu needs to have the site.root_page
    # defined else will return an object attribute error ('str' object has no
    # attribute 'get_children')
    return parent.get_children().get(slug=slug)


@register.simple_tag(takes_context=True)
def richtext_footnotes(context, html):
    """
    example: {% richtext_footnotes page.body|richtext %}

    html: already processed richtext field html
    Assumes "page" in context.
    """
    FIND_FOOTNOTE_TAG = re.compile(r'<footnote id="(.*?)">.*?</footnote>')

    if not isinstance(context.get("page"), Page):
        return html

    page = context["page"]
    if not hasattr(page, "footnotes_list"):
        page.footnotes_list = []
    footnotes = {str(footnote.uuid): footnote for footnote in page.footnotes.all()}

    def replace_tag(match):
        try:
            index = process_footnote(match.group(1), page)
        except (KeyError, ValidationError):
            return ""
        else:
            return f'<a href="#footnote-{index}" id="footnote-source-{index}"><sup>[{index}]</sup></a>'

    def process_footnote(footnote_id, page):
        footnote = footnotes[footnote_id]
        if footnote not in page.footnotes_list:
            page.footnotes_list.append(footnote)
        # Add 1 to the index as footnotes are indexed starting at 1 not 0.
        return page.footnotes_list.index(footnote) + 1

    return mark_safe(FIND_FOOTNOTE_TAG.sub(replace_tag, html))
