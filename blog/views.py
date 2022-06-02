from django.conf import settings
from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Atom1Feed
from wagtail.core.models.i18n import Locale
from wagtailmarkdown.utils import render_markdown

from .models import BlogCategory
from .models import BlogIndexPage
from .models import BlogPage


def tag_view(request, tag):
    index = BlogIndexPage.objects.first()
    return index.serve(request, tag=tag)


def category_view(request, category):
    index = BlogIndexPage.objects.first()
    return index.serve(request, category=category)


def locale_view(request, locale):
    index = BlogIndexPage.objects.first()
    locale = Locale.objects.get(language_code=locale)
    return index.serve(request, locale=locale)


def author_view(request, author):
    index = BlogIndexPage.objects.first()
    return index.serve(request, author=author)


class LatestEntriesFeed(Feed):
    """
    If a URL ends with "rss" try to find a matching BlogIndexPage
    and return its items.
    """

    def get_object(self, request, blog_slug):
        return get_object_or_404(BlogIndexPage, slug=blog_slug)

    def title(self, blog):
        if blog.seo_title:
            return blog.seo_title
        return blog.title

    def link(self, blog):
        return blog.full_url

    def description(self, blog):
        return blog.search_description

    def items(self, blog):
        num = getattr(settings, "BLOG_PAGINATION_PER_PAGE", 10)
        return blog.get_descendants().order_by("-blogpage__date")[:num]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        if item.specific.body_markdown:
            return render_markdown(item.specific.body_markdown)
        return item.specific.body_richtext

    def item_link(self, item):
        return item.full_url

    def item_pubdate(self, blog):
        return blog.first_published_at


class LatestEntriesFeedAtom(LatestEntriesFeed):
    feed_type = Atom1Feed


class LatestCategoryFeed(Feed):
    description = "A Blog"

    def title(self, category):
        return "Blog: " + category.name

    def link(self, category):
        return "/blog/category/" + category.slug

    def get_object(self, request, category):
        return get_object_or_404(BlogCategory, slug=category)

    def items(self, obj):
        return BlogPage.objects.filter(categories__category=obj).order_by("-date")[:5]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.body_legacy
