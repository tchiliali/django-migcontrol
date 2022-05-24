import datetime

from bs4 import BeautifulSoup
from compressor.css import CssCompressor
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage
from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Count
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import slugify
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.tags import ClusterTaggableManager
from taggit.models import Tag
from taggit.models import TaggedItemBase
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.admin.edit_handlers import FieldRowPanel
from wagtail.admin.edit_handlers import InlinePanel
from wagtail.admin.edit_handlers import MultiFieldPanel
from wagtail.admin.edit_handlers import StreamFieldPanel
from wagtail.core import blocks
from wagtail.core import hooks
from wagtail.core.fields import StreamField
from wagtail.core.models import Page
from wagtail.core.templatetags.wagtailcore_tags import richtext
from wagtail.documents import get_document_model_string
from wagtail.images import get_image_model_string
from wagtail.images.blocks import ImageChooserBlock
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.search import index
from wagtail.snippets.models import register_snippet
from wagtailmarkdown.blocks import MarkdownBlock
from wagtailmarkdown.edit_handlers import MarkdownPanel
from wagtailmarkdown.fields import MarkdownField
from wagtailmarkdown.templatetags.wagtailmarkdown import markdown

from home.models import ArticleBase
from migcontrol.utils import toc


COMMENTS_APP = getattr(settings, "COMMENTS_APP", None)


def get_blog_context(context):
    """Get context data useful on all blog related pages"""
    context["authors"] = (
        get_user_model()
        .objects.filter(
            owned_pages__live=True, owned_pages__content_type__model="blogpage"
        )
        .annotate(Count("owned_pages"))
        .order_by("-owned_pages__count")
    )
    context["all_categories"] = BlogCategory.objects.all()
    context["root_categories"] = (
        BlogCategory.objects.filter(
            parent=None,
        )
        .prefetch_related(
            "children",
        )
        .annotate(
            blog_count=Count("blogpage"),
        )
    )
    return context


class BlogIndexPage(ArticleBase, Page):
    template = "blog/index.html"

    @property
    def blogs(self):
        # Get list of blog pages that exist - we don't care which blog they
        # belong to for now, as blogs are not language sensitive
        blogs = BlogPage.objects.all().live()
        blogs = (
            blogs.order_by("-date")
            .select_related("owner")
            .prefetch_related(
                "tagged_items__tag",
                "categories",
                "categories__category",
            )
        )
        return blogs

    def get_context(  # noqa: max-complexity=14
        self, request, tag=None, category=None, author=None, *args, **kwargs
    ):
        context = super(BlogIndexPage, self).get_context(request, *args, **kwargs)
        blogs = self.blogs

        if tag is None:
            tag = request.GET.get("tag")
        if tag:
            blogs = blogs.filter(tags__slug=tag)
        if category is None:  # Not coming from category_view in views.py
            if request.GET.get("category"):
                category = get_object_or_404(
                    BlogCategory, slug=request.GET.get("category")
                )
        if category:
            if not request.GET.get("category"):
                category = get_object_or_404(BlogCategory, slug=category)
            blogs = blogs.filter(categories__category__name=category)
        if author:
            if isinstance(author, str) and not author.isdigit():
                blogs = blogs.filter(author__username=author)
            else:
                blogs = blogs.filter(author_id=author)

        # Pagination
        page = request.GET.get("page")
        page_size = 12
        if hasattr(settings, "BLOG_PAGINATION_PER_PAGE"):
            page_size = settings.BLOG_PAGINATION_PER_PAGE

        if page_size is not None:
            paginator = Paginator(blogs, page_size)  # Show 10 blogs per page
            try:
                blogs = paginator.page(page)
            except PageNotAnInteger:
                blogs = paginator.page(1)
            except EmptyPage:
                blogs = paginator.page(paginator.num_pages)

        context["blogs"] = blogs
        context["category"] = category
        context["tag"] = tag
        context["author"] = author
        context["COMMENTS_APP"] = COMMENTS_APP
        context = get_blog_context(context)

        return context

    class Meta:
        verbose_name = _("Blog index")

    subpage_types = ["blog.BlogPage"]


@register_snippet
class BlogCategory(models.Model):
    name = models.CharField(max_length=80, unique=True, verbose_name=_("Category Name"))
    slug = models.SlugField(unique=True, max_length=80)
    parent = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        related_name="children",
        help_text=_(
            "Categories, unlike tags, can have a hierarchy. You might have a "
            "Jazz category, and under that have children categories for Bebop"
            " and Big Band. Totally optional."
        ),
        on_delete=models.CASCADE,
    )
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Blog Category")
        verbose_name_plural = _("Blog Categories")

    panels = [
        FieldPanel("name"),
        FieldPanel("parent"),
        FieldPanel("description"),
    ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.parent:
            parent = self.parent
            if self.parent == self:
                raise ValidationError("Parent category cannot be self.")
            if parent.parent and parent.parent == self:
                raise ValidationError("Cannot have circular Parents.")

    def save(self, *args, **kwargs):
        if not self.slug:
            slug = slugify(self.name)
            count = BlogCategory.objects.filter(slug=slug).count()
            if count > 0:
                slug = "{}-{}".format(slug, count)
            self.slug = slug
        return super(BlogCategory, self).save(*args, **kwargs)


class BlogCategoryBlogPage(models.Model):
    category = models.ForeignKey(
        BlogCategory,
        related_name="+",
        verbose_name=_("Category"),
        on_delete=models.CASCADE,
    )
    page = ParentalKey("BlogPage", related_name="categories")
    panels = [
        FieldPanel("category"),
    ]


class BlogPageTag(TaggedItemBase):
    content_object = ParentalKey("BlogPage", related_name="tagged_items")


@register_snippet
class BlogTag(Tag):
    class Meta:
        proxy = True


def limit_author_choices():
    """Limit choices in blog author field based on config settings"""
    LIMIT_AUTHOR_CHOICES = getattr(settings, "BLOG_LIMIT_AUTHOR_CHOICES_GROUP", None)
    if LIMIT_AUTHOR_CHOICES:
        if isinstance(LIMIT_AUTHOR_CHOICES, str):
            limit = Q(groups__name=LIMIT_AUTHOR_CHOICES)
        else:
            limit = Q()
            for s in LIMIT_AUTHOR_CHOICES:
                limit = limit | Q(groups__name=s)
        if getattr(settings, "BLOG_LIMIT_AUTHOR_CHOICES_ADMIN", False):
            limit = limit | Q(is_staff=True)
    else:
        limit = {"is_staff": True}
    return limit


class BlogPage(Page):
    body_richtext = models.TextField(verbose_name=_("body (HTML)"), blank=True)
    body_markdown = MarkdownField(
        default="", verbose_name=_("body (Markdown)"), blank=True
    )
    body_mixed = StreamField(
        [
            ("heading", blocks.CharBlock(classname="full title")),
            ("paragraph", blocks.RichTextBlock()),
            ("image", ImageChooserBlock()),
            ("markdown", MarkdownBlock()),
        ],
        verbose_name="body (mixed)",
        blank=True,
        help_text="Avoiding this at first because data might be hard to migrate?",
    )

    add_toc = models.BooleanField(
        default=False,
        verbose_name=_("Display TOC (Table Of Contents)"),
        help_text=_("A TOC can be auto-generated"),
    )

    tags = ClusterTaggableManager(through=BlogPageTag, blank=True)
    date = models.DateField(
        _("Post date"),
        default=datetime.datetime.today,
        help_text=_(
            "This date may be displayed on the blog post. It is not "
            "used to schedule posts to go live at a later date."
        ),
    )
    header_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Header image"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        limit_choices_to=limit_author_choices,
        verbose_name=_("Author"),
        on_delete=models.SET_NULL,
        related_name="author_pages",
    )

    search_fields = Page.search_fields + [
        index.SearchField("body_markdown"),
        index.SearchField("body_richtext"),
    ]
    blog_categories = models.ManyToManyField(
        BlogCategory, through=BlogCategoryBlogPage, blank=True
    )

    settings_panels = Page.settings_panels + [
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel("go_live_at"),
                        FieldPanel("expire_at"),
                    ],
                    classname="label-above",
                ),
            ],
            "Scheduled publishing",
            classname="publishing",
        ),
        FieldPanel("date"),
        FieldPanel("author"),
    ]

    def get_body(self):
        if self.body_richtext:
            body = richtext(self.body_richtext)
        elif self.body_markdown:
            body = markdown(self.body_markdown)
        else:
            body = "".join([str(f.value) for f in self.body_mixed])

        # Now let's add some id=... attributes to all h{1,2,3,4,5}
        soup = BeautifulSoup(body, "html5lib")

        # Beautiful soup unfortunately adds some noise to the structure, so we
        # remove this again - see:
        # https://stackoverflow.com/questions/21452823/beautifulsoup-how-should-i-obtain-the-body-contents
        for attr in ["head", "html", "body"]:
            if hasattr(soup, attr):
                getattr(soup, attr).unwrap()

        for element in soup.find_all(["h1", "h2", "h3", "h4", "h5"]):
            element["id"] = "header-" + slugify(element.text)

        return str(soup)

    def get_toc(self):
        """
        [(name, [*children])]
        """
        html = self.get_body()
        soup = BeautifulSoup(html)
        # Need to build this in a list, otherwise evaluating whether it is
        # empty or not causes problems in templates
        return_list = []
        for element, children in toc(soup.find_all(["h1", "h2", "h3", "h4", "h5"])):
            return_list.append((element, children))
        return return_list

    def save_revision(self, *args, **kwargs):
        if not self.author:
            self.author = self.owner
        return super(BlogPage, self).save_revision(*args, **kwargs)

    def get_absolute_url(self):
        return self.url

    def get_blog_index(self):
        # Find closest ancestor which is a blog index
        return self.get_ancestors().type(BlogIndexPage).last()

    def get_context(self, request, *args, **kwargs):
        context = super(BlogPage, self).get_context(request, *args, **kwargs)
        context["blogs"] = self.get_blog_index().blogindexpage.blogs
        context = get_blog_context(context)
        context["COMMENTS_APP"] = COMMENTS_APP
        return context

    class Meta:
        verbose_name = _("Blog page")
        verbose_name_plural = _("Blog pages")

    parent_page_types = ["blog.BlogIndexPage"]


class WordpressMapping(models.Model):
    """
    Mappings between Wordpress stuff and Wagtail stuff. Used to clean up
    imported content containing for instance links, images or attachments.

    Also useful for making a URL mapping from old wordpress URLs like
    /wp-content/uploads/<...>
    """

    wp_url = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
    )
    wp_post_id = models.IntegerField(
        unique=True,
        blank=True,
        null=True,
    )
    page = models.ForeignKey(
        Page,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Wagtail image"),
    )
    document = models.ForeignKey(
        get_document_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Wagtail image"),
    )


BlogPage.content_panels = [
    FieldPanel("title", classname="full title"),
    MultiFieldPanel(
        [
            FieldPanel("tags"),
            InlinePanel("categories", label=_("Categories")),
        ],
        heading="Tags and Categories",
    ),
    ImageChooserPanel("header_image"),
    MarkdownPanel("body_markdown"),
    FieldPanel("body_richtext", classname="collapsed"),
    StreamFieldPanel("body_mixed"),
]


@hooks.register("insert_global_admin_css")
def import_fontawesome_stylesheet():
    elem = '<link rel="stylesheet" type="text/x-scss" href="{}scss/fontawesome.scss">'.format(
        settings.STATIC_URL
    )
    compressor = CssCompressor("css", content=elem)
    output = ""
    for x in compressor.hunks():
        output += x
    return format_html(compressor.output(forced=True))
