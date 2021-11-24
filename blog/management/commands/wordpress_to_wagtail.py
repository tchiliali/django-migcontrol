import os
import re
import urllib.request
import uuid

from bs4 import BeautifulSoup
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.utils.html import linebreaks
from django.utils.text import slugify
from wagtail.core.models import Locale
from wagtail.images.models import Image

from archive.models import ArchivePageLocation
from archive.models import LocationPage
from blog.models import BlogCategory
from blog.models import BlogCategoryBlogPage
from blog.models import BlogPageTag
from blog.models import BlogTag
from blog.wp_xml_parser import XML_parser

try:
    import lxml  # noqa
except ImportError as e:
    print("You must have lxml installed to run xml imports." " Run `pip install lxml`.")
    raise e

try:
    import html
except ImportError:  # 2.x
    import HTMLParser

    html = HTMLParser.HTMLParser()

User = get_user_model()

pattern_country_code = re.compile(r"\(([a-zA-Z]{2})\)")


def noop_mapping(value, *args):
    return value


def get_country(land, page, index):  # noqa: max-complexity=27
    land = land.strip().lower()
    if land == "deutschland":
        return ("de",)
    if land == "deutschland/frankreich":
        return ["de", "fr"]
    if land == "österreich":
        return ("at",)
    if land == "türkei (TR)":
        return ("tr",)
    if land == "frankreich":
        return ("fr",)
    if land == "uk":
        return ("gb",)
    if land == "china":
        return ("cn",)
    if land == "spanien":
        return ("es",)
    if land == "kroatien":
        return ("hr",)
    if land == "italien":
        return ("it",)
    if land == "belgien":
        return ("be",)
    if land == "türkei":
        return ("tr",)
    if land == "niederlande":
        return ("nl",)
    if land == "polen":
        return ("pl",)
    if land == "italien/uk":
        return "it", "gb"
    if land == "israel":
        return ("il",)
    if land == "portugal":
        return ("pt",)
    if land == "usa":
        return ("us",)
    if land == "australien":
        return ("au",)
    if land == "schweiz":
        return ("ch",)
    if land == "irland":
        return ("ie",)
    if land == "de":
        return ("de",)
    if land == "deutschland / usa":
        return ["de", "us"]
    if land == "":
        return []
    elif pattern_country_code.findall(land):
        country_code = pattern_country_code.findall(land)[0]
        country_code = country_code.lower()
        if country_code == "uk":
            return ("gb",)
        return (country_code,)
    else:
        print(f"Did not understand {land}")
        raise ValueError


def get_locations(locations, page, index):
    locations = locations.replace(", ", ",")
    for location in locations.split(","):
        if not pattern_country_code.findall(location):
            return []
        country = pattern_country_code.findall(location)[0].strip().lower()
        if country == "uk":
            country = "gb"
        location_name = re.sub(re.compile(r"(\s*\([a-zA-Z]{2}\))"), "", location)
        slug = slugify(location_name) + "-" + slugify(f"{country}")
        print(f"{slug} {country}")
        try:
            location_page = LocationPage.objects.get(
                slug=slug,
            )
        except LocationPage.DoesNotExist:
            location_page = LocationPage(
                country=country,
                name=location_name,
                title=location_name,
                slug=slug,
            )
            index.add_child(instance=location_page)
        try:
            archive_location_page = ArchivePageLocation.objects.get(
                page=page,
                location=location_page,
            )
        except ArchivePageLocation.DoesNotExist:
            archive_location_page = ArchivePageLocation.objects.create(
                location=location_page,
                page=page,
            )
        yield archive_location_page


# {app.model: {wp_meta_key: (attr_name, mapping_func)}}
WP_POSTMETA_MAPPING = {
    "archive.archivepage": {
        "branche": ("organization_type", noop_mapping),
        "land": ("country", get_country),
        "standorte": ("locations", get_locations),
        "kurztext": ("short_description", noop_mapping),
    }
}


class Command(BaseCommand):
    """
    This is a management command to migrate a Wordpress site to Wagtail.
    Two arguments should be used

    1) Path of the XML file to import from
    2) The name of the index page under which each page should be nested
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "xml",
            help="Path to Wordpress XML exported stuff",
        )
        parser.add_argument(
            "index_slug", help="Slug of blog index page to attach blogs"
        )
        parser.add_argument("--app", default=False, help="Django app to use")
        parser.add_argument(
            "--index-model", default=False, help="Django app index page model"
        )
        parser.add_argument(
            "--post-model", default=False, help="Django app post page model"
        )
        parser.add_argument(
            "--locale", type=str, default=None, help="Hard-code a locale"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        """gets data from WordPress site"""

        self.IndexModel = apps.get_model(options["app"], options["index_model"])
        self.PostModel = apps.get_model(options["app"], options["post_model"])
        self.xml_path = options.get("xml")
        self.locale = options.get("locale", None)
        self.mappings = WP_POSTMETA_MAPPING.get(
            "{}.{}".format(options["app"].lower(), options["post_model"].lower()), {}
        )
        try:
            self.index_page = self.IndexModel.objects.get(
                slug__iexact=options["index_slug"],
                locale__language_code__iexact=self.locale,
            )
        except self.IndexModel.DoesNotExist:
            raise CommandError(
                "Incorrect blog index slug {} - have you created it?".format(
                    options["index_slug"]
                )
            )

        self.xml_parser = XML_parser(self.xml_path)
        posts = self.xml_parser.get_posts_data()

        # self.should_import_comments = options.get("import_comments")
        self.create_blog_pages(posts, self.index_page)

    def prepare_url(self, url):
        if url.startswith("//"):
            url = "http:{}".format(url)
        if url.startswith("/"):
            prefix_url = self.url
            if prefix_url and prefix_url.endswith("/"):
                prefix_url = prefix_url[:-1]
            url = "{}{}".format(prefix_url or "", url)
        return url

    def convert_html_entities(self, text, *args, **options):
        """converts html symbols so they show up correctly in wagtail"""
        return html.unescape(text)

    def create_images_from_urls_in_content(self, body):
        """create Image objects and transfer image files to media root"""
        soup = BeautifulSoup(body, "html5lib")
        for img in soup.findAll("img"):
            old_url = img["src"]
            if "width" in img:
                width = img["width"]
            if "height" in img:
                height = img["height"]
            else:
                width = 100
                height = 100
            __, file_ = os.path.split(img["src"])
            if not img["src"]:
                continue  # Blank image
            if img["src"].startswith("data:"):
                continue  # Embedded image
            try:
                remote_image = urllib.request.urlretrieve(self.prepare_url(img["src"]))
            except (
                urllib.error.HTTPError,
                urllib.error.URLError,
                UnicodeEncodeError,
                ValueError,
            ):
                print("Unable to import " + img["src"])
                continue
            image = Image(title=file_, width=width, height=height)
            try:
                image.file.save(file_, File(open(remote_image[0], "rb")))
                image.save()
                new_url = image.file.url
                body = body.replace(old_url, new_url)
                body = self.convert_html_entities(body)
            except TypeError:
                print("Unable to import image {}".format(remote_image[0]))
        return body

    def create_user(self, author):
        username = author["username"]
        first_name = author["first_name"]
        last_name = author["last_name"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=username, first_name=first_name, last_name=last_name
            )
            user.save()
        return user

    #
    #     def create_comment(self, blog_post_type, blog_post_id, comment_text, date):
    #         from django_comments_xtd.models import MaxThreadLevelExceededException
    #         from django_comments_xtd.models import XtdComment
    #         # Assume that the timezone wanted is the one that's active during parsing
    #         if date is not None and settings.USE_TZ and timezone.is_naive(date):
    #             date = timezone.make_aware(date, timezone.get_current_timezone())
    #
    #         new_comment = XtdComment.objects.get_or_create(
    #             site_id=self.site_id,
    #             content_type=blog_post_type,
    #             object_pk=blog_post_id,
    #             comment=comment_text,
    #             submit_date=date,
    #         )[0]
    #         return new_comment
    #
    #     def lookup_comment_by_wordpress_id(self, comment_id, comments):
    #         """ Returns Django comment object with this wordpress id """
    #         for comment in comments:
    #             if comment.wordpress_id == comment_id:
    #                 return comment
    #
    #     def import_comments(  # noqa: max-complexity=18
    #         self, post_id, slug, *args, **options
    #     ):
    #         try:
    #             mysite = Site.objects.get_current()
    #             self.site_id = mysite.id
    #         except Site.DoesNotExist:
    #             print("site does not exist")
    #             return
    #         if getattr(self, "xml_path", None):
    #             comments = self.xml_parser.get_comments_data(slug)
    #         else:
    #             comments = self.get_posts_data(self.url, post_id, get_comments=True)
    #         imported_comments = []
    #         for comment in comments:
    #             try:
    #                 blog_post = self.PostModel.objects.get(slug=slug)
    #                 blog_post_type = ContentType.objects.get_for_model(blog_post)
    #             except self.PostModel.DoesNotExist:
    #                 print("cannot find this blog post")
    #                 continue
    #             comment_text = self.convert_html_entities(comment.get("content"))
    #             date = datetime.strptime(comment.get("date"), "%Y-%m-%dT%H:%M:%S")
    #             status = comment.get("status")
    #             if status != "approved":
    #                 continue
    #             comment_author = comment.get("author")
    #             new_comment = self.create_comment(
    #                 blog_post_type, blog_post.pk, comment_text, date
    #             )
    #             new_comment.wordpress_id = comment.get("ID")
    #             new_comment.parent_wordpress_id = comment.get("parent")
    #             if type(comment_author) is int:
    #                 pass
    #             else:
    #                 if "username" in comment_author:
    #                     user_name = comment["author"]["username"]
    #                     user_url = comment["author"]["URL"]
    #                     try:
    #                         current_user = User.objects.get(username=user_name)
    #                         new_comment.user = current_user
    #                     except User.DoesNotExist:
    #                         pass
    #
    #                     new_comment.user_name = user_name
    #                     new_comment.user_url = user_url
    #
    #             new_comment.save()
    #             imported_comments.append(new_comment)

    #
    #         # Now assign parent comments
    #         for comment in imported_comments:
    #             if str(comment.parent_wordpress_id or 0) == "0":
    #                 continue
    #             for sub_comment in imported_comments:
    #                 if sub_comment.wordpress_id == comment.parent_wordpress_id:
    #                     comment.parent_id = sub_comment.id
    #                     try:
    #                         comment._calculate_thread_data()
    #                         comment.save()
    #                     except MaxThreadLevelExceededException:
    #                         print(
    #                             "Warning, max thread level exceeded on {}".format(
    #                                 comment.id
    #                             )
    #                         )
    #                     break

    def create_categories_and_tags(self, page, categories):
        tags_for_blog_entry = []
        categories_for_blog_entry = []
        for records in categories.values():
            if records[0]["taxonomy"] == "post_tag":
                for record in records:
                    tag_name = record["name"]
                    new_tag = BlogTag.objects.get_or_create(name=tag_name)[0]
                    tags_for_blog_entry.append(new_tag)

            if records[0]["taxonomy"] == "category":
                for record in records:
                    category_name = record["name"]
                    new_category = BlogCategory.objects.get_or_create(
                        name=category_name
                    )[0]
                    if record.get("parent"):
                        parent_category = BlogCategory.objects.get_or_create(
                            name=record["parent"]["name"]
                        )[0]
                        parent_category.slug = record["parent"]["slug"]
                        parent_category.save()
                        parent = parent_category
                        new_category.parent = parent
                    else:
                        parent = None
                    categories_for_blog_entry.append(new_category)
                    new_category.save()

        # loop through list of BlogCategory and BlogTag objects and create
        # BlogCategoryBlogPages(bcbp) for each category and BlogPageTag objects
        # for each tag for this blog page
        for category in categories_for_blog_entry:
            BlogCategoryBlogPage.objects.get_or_create(category=category, page=page)[0]
        for tag in tags_for_blog_entry:
            BlogPageTag.objects.get_or_create(tag=tag, content_object=page)[0]

    def create_blog_pages(  # noqa: max-complexity=12
        self, posts, blog_index, *args, **options
    ):
        """create Blog post entries from wordpress data"""
        for post in posts:
            # post_id = post.get("ID")
            title = post.get("title")
            if title:
                new_title = self.convert_html_entities(title)
                title = new_title
            slug = post.get("slug")
            description = post.get("description")
            if description:
                description = self.convert_html_entities(description)

            body = post.get("content")
            if "<p>" not in body:
                body = linebreaks(body)

            # get image info from content and create image objects
            body = self.create_images_from_urls_in_content(body)

            # author/user data
            author = post.get("author")
            user = self.create_user(author)
            # categories = post.get("terms")
            # format the date
            # date = post.get("date")[:10]
            try:
                new_entry = self.PostModel.objects.get(slug=slug)
                new_entry.title = title
                new_entry.owner = user
                new_entry.author = user
            except self.PostModel.DoesNotExist:
                post_model_kwargs = {}
                if self.locale:
                    post_model_kwargs["locale"] = Locale.objects.get(
                        language_code=self.locale
                    )
                    post_model_kwargs["translation_key"] = uuid.uuid4()

                new_entry = blog_index.add_child(
                    instance=self.PostModel(
                        title=title,
                        slug=slug,
                        search_description="description",
                        # date=date,
                        # bbody_richtext=body,
                        owner=user,
                        author=user,
                        description=body,
                        # body_markdown=html2text.html2text(body, bodywidth=0),
                        **post_model_kwargs,
                    )
                )

            new_entry.country = []
            for key, value in post.get("meta").items():
                print(key)
                if key in self.mappings.keys():
                    print(f"Setting {key}")
                    setattr(
                        new_entry,
                        self.mappings[key][0],
                        self.mappings[key][1](value, new_entry, self.index_page),
                    )

            new_entry.save()

            featured_image = post.get("featured_image")
            if featured_image is not None:
                title = post["featured_image"]["title"]
                source = post["featured_image"]["source"]
                path, file_ = os.path.split(source)
                source = source.replace("stage.swoon", "swoon")
                try:
                    remote_image = urllib.request.urlretrieve(self.prepare_url(source))
                    width = 640
                    height = 290
                    header_image = Image(title=title, width=width, height=height)
                    header_image.file.save(file_, File(open(remote_image[0], "rb")))
                    header_image.save()
                except UnicodeEncodeError:
                    header_image = None
                    print("unable to set header image {}".format(source))
            else:
                header_image = None
            new_entry.header_image = header_image
            new_entry.save()
            # if categories:
            #     self.create_categories_and_tags(new_entry, categories)
            # if self.should_import_comments:
            #     self.import_comments(post_id, slug)
