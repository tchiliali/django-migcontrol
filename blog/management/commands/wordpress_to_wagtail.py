import json
import os
import re
import urllib.request
import uuid

import bleach
import html2text
from bleach.sanitizer import ALLOWED_TAGS
from bs4 import BeautifulSoup
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.db.models import Q
from django.template.defaultfilters import striptags
from django.template.defaultfilters import truncatechars
from django.utils import translation
from django.utils.html import linebreaks
from django.utils.text import slugify
from PIL import Image as PILImage
from wagtail.core.models import Locale
from wagtail.images.models import Image

from archive.models import ArchivePageLocation
from archive.models import LocationPage
from blog.models import BlogCategory
from blog.models import BlogCategoryBlogPage
from blog.models import BlogPageTag
from blog.models import BlogTag
from blog.models import WordpressMapping
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
    },
    "blog.blogpage": {},
}


def get_archive_page_mapping(
    index,
    locale,
    post_id,
    published,
    title,
    date,
    slug,
    body,
    excerpt,
    user,
    authors,
    meta,
):
    return {
        "title": title,
        "slug": slug,
        "search_description": excerpt,
        "owner": user,
        # "authors": authors,
        "description": body,
        "locale": locale,
        "live": published,
    }


def get_blog_page_mapping(
    index,
    locale,
    post_id,
    published,
    title,
    date,
    slug,
    body,
    excerpt,
    user,
    authors,
    meta,
):

    # Clean up UPPERCASE h1 and h2s in blog posts
    body_soup = BeautifulSoup(body, "html5lib")
    uppercase_re = re.compile(r"^[^a-z]+$")
    for header in body_soup.findAll(["h1", "h2", "h3", "h4", "h5"]):
        if uppercase_re.match(header.text):
            if header.string:
                header.string.replace_with(header.text.title())
    body = str(body_soup)
    return {
        "title": title,
        "slug": slug,
        "search_description": excerpt,
        "date": date,
        "body_richtext": body,
        "owner": user,
        # Not automatic mapping at the moment, we do it manually to check if
        # authors is already set
        # "authors": authors,
        "body_markdown": html2text.html2text(body, bodywidth=0),
        "locale": locale,
        "live": published,
    }


WP_POST_MAPPING = {
    "archive.archivepage": get_archive_page_mapping,
    "blog.blogpage": get_blog_page_mapping,
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
            "--use-wagtail-locale",
            action="store_true",
            help="Uses the Wagtail locale and translation_key",
        )
        parser.add_argument(
            "--locale", type=str, default=None, help="Hard-code a locale"
        )
        parser.add_argument(
            "--wp-base-url",
            type=str,
            default=None,
            help="URL prefix of imported blog.: https://example-blog.com/ - this URL should have for instance wp-content nested in the first level.",
        )
        parser.add_argument(
            "--create-other-locales",
            type=str,
            default=None,
            help="Create versions in other locales",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        """gets data from WordPress site"""

        self.IndexModel = apps.get_model(options["app"], options["index_model"])
        self.PostModel = apps.get_model(options["app"], options["post_model"])
        self.xml_path = options.get("xml")
        self.locale = options.get("locale", None)
        self.wagtail_locale = options.get("use_wagtail_locale", False)
        self.create_other_locales = options.get("create_other_locales", False)
        self.wordpress_base_url = options["wp_base_url"]
        self.meta_mappings = WP_POSTMETA_MAPPING.get(
            "{}.{}".format(options["app"].lower(), options["post_model"].lower()), {}
        )
        self.mappings = WP_POST_MAPPING.get(
            "{}.{}".format(options["app"].lower(), options["post_model"].lower()), {}
        )
        try:
            self.index_page = self.IndexModel.objects.get(
                Q(locale__language_code__iexact=self.locale)
                if self.wagtail_locale
                else Q(),
                slug__iexact=options["index_slug"],
            )
        except self.IndexModel.DoesNotExist:
            raise CommandError(
                "Incorrect blog index slug '{}' - have you created it?".format(
                    options["index_slug"]
                )
            )

        self.xml_parser = XML_parser(self.xml_path)
        posts = self.xml_parser.get_posts_data()

        self.create_blog_pages(posts, self.index_page)

    def prepare_url(self, url):
        if url.startswith("//"):
            url = "http:{}".format(url)
        if url.startswith("/"):
            prefix_url = self.url
            if prefix_url and prefix_url.endswith("/"):
                prefix_url = prefix_url[:-1]
            url = "{}{}".format(prefix_url or "", url)
        p_resized = re.compile(r"(.+)-\d+x\d+(\.[a-zA-Z]{3,4})")
        matches = p_resized.findall(url)
        if matches:
            url = matches[0][0] + matches[0][1]
        return url

    def convert_html_entities(self, text, *args, **options):
        """converts html symbols so they show up correctly in wagtail"""
        return html.unescape(text)

    def create_images_from_urls_in_content(self, body):
        """create Image objects and transfer image files to media root"""
        soup = BeautifulSoup(body, "html5lib")
        for img in soup.findAll("img"):
            old_url = img["src"]
            __, file_ = os.path.split(img["src"])
            if not img["src"]:
                continue  # Blank image
            if img["src"].startswith("data:"):
                continue  # Embedded image

            cleaned_path = urllib.parse.urlparse(self.prepare_url(img["src"])).path
            try:

                image = WordpressMapping.objects.get(wp_url=cleaned_path or "404").image
                print(f"Found already imported image {cleaned_path}")
            except WordpressMapping.DoesNotExist:
                try:
                    remote_image = urllib.request.urlretrieve(
                        self.prepare_url(img["src"])
                    )
                except (
                    urllib.error.HTTPError,
                    urllib.error.URLError,
                    UnicodeEncodeError,
                    ValueError,
                ):
                    print("Unable to import " + img["src"])
                    continue
                img_buffer = open(remote_image[0], "rb")
                width, height = PILImage.open(img_buffer).size
                img_buffer.seek(0)
                image = Image(title=file_, width=width, height=height)
                image.file.save(file_, File(img_buffer))
                image.save()
                WordpressMapping.objects.create(
                    wp_url=urllib.parse.urlparse(cleaned_path).path, image=image
                )

            new_url = image.file.url
            body = body.replace(old_url, new_url)
            body = self.convert_html_entities(body)
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

    def create_categories_and_tags(self, page, categories):
        tags_for_blog_entry = []
        categories_for_blog_entry = []
        for records in categories:
            if records["taxonomy"] == "post_tag":
                tag_name = records["name"]
                new_tag = BlogTag.objects.get_or_create(name=tag_name)[0]
                tags_for_blog_entry.append(new_tag)

            if records["taxonomy"] == "category":
                category_name = records["name"]
                slug = records["slug"]
                new_category = BlogCategory.objects.get_or_create(
                    slug=slug,
                )[0]
                new_category.name = category_name
                new_category.save()
                if records.get("parent"):
                    parent_category = BlogCategory.objects.get_or_create(
                        slug=records["parent"]["slug"],
                    )[0]
                    parent_category.name = records["parent"]["name"]
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

    def clean_body(self, body):
        return bleach.clean(
            body,
            tags=ALLOWED_TAGS + ["p", "h1", "h2", "h3", "h4", "h5", "caption"],
            attributes=[
                "href",
            ],
            strip=True,
        )

    def create_blog_pages(  # noqa: max-complexity=12
        self, posts, blog_index, *args, **options
    ):
        """create Blog post entries from wordpress data"""
        for post in posts:
            post_id = post.get("ID")
            title = post.get("title")
            if title:
                new_title = self.convert_html_entities(title)
                title = new_title
            slug = slugify(post.get("slug"))
            description = post.get("description")
            if description:
                description = self.convert_html_entities(description)

            body = post.get("content")
            if isinstance(body, list):
                print(f"Error: Empty content? {body}")
                continue
            if "<p>" not in body:
                # Ensure that we have only double linebreaks
                body = body.replace("\n\n", "¤¤¤¤¤¤")
                body = body.replace("\n", "\n\n")
                body = body.replace("¤¤¤¤¤¤", "\n\n")
                body = linebreaks(body)

            body = self.clean_body(body)

            # get image info from content and create image objects
            body = self.create_images_from_urls_in_content(body)

            excerpt = post.get("excerpt") or truncatechars(striptags(body), 100)

            # author/user data
            authors = ""
            for author in post.get("authors").values():
                if authors != "":
                    authors += ", "
                if author["first_name"]:
                    authors += author["first_name"]
                    if author["last_name"]:
                        authors += " " + author["last_name"]
                elif author["username"]:
                    authors += author["username"]
                else:
                    authors += "pseudonym"

            user = self.create_user(post.get("creator"))
            categories = post.get("terms").get("category")
            if categories:
                for cat_dict in categories:
                    if "en" in cat_dict:
                        raise Exception("English category")

            # format the date
            date = post.get("date")[:10]

            post_model_kwargs = {}
            restore_locale = translation.get_language()
            locale = None

            published = post.get("status") == "publish"

            # Special detection of German blog posts
            if any(c["slug"] == "de" for c in categories):
                if self.wagtail_locale:
                    locale = Locale.objects.get(language_code="de")
                    post_model_kwargs["translation_key"] = uuid.uuid4()
                else:
                    translation.activate("de")
            elif any(c["slug"] == "fr" for c in categories):
                if self.wagtail_locale:
                    locale = Locale.objects.get(language_code="fr")
                    post_model_kwargs["translation_key"] = uuid.uuid4()
                else:
                    translation.activate("fr")
            elif any(c["slug"] == "ar" for c in categories):
                if self.wagtail_locale:
                    locale = Locale.objects.get(language_code="ar")
                    post_model_kwargs["translation_key"] = uuid.uuid4()
                else:
                    translation.activate("ar")
            elif self.locale:
                if self.wagtail_locale:
                    locale = Locale.objects.get(language_code=self.locale)
                    post_model_kwargs["translation_key"] = uuid.uuid4()
                else:
                    translation.activate(self.locale)

            print(f"Creating page '{title}'")
            page = self.create_page(
                self.index_page,
                locale,
                post_id,
                published,
                title,
                date,
                slug,
                body,
                excerpt,
                user,
                authors,
                post.get("meta"),
                **post_model_kwargs,
            )

            self.create_categories_and_tags(page, categories)

            translation.activate(restore_locale)

    def create_page(  # noqa max-complexity: 16
        self,
        index,
        locale,
        post_id,
        published,
        title,
        date,
        slug,
        body,
        excerpt,
        user,
        authors,
        meta,
        **kwargs,
    ):

        try:
            new_entry = self.PostModel.objects.get(slug=slug)
            for k, v in self.mappings(
                index,
                locale,
                post_id,
                published,
                title,
                date,
                slug,
                body,
                excerpt,
                user,
                authors,
                meta,
            ).items():
                setattr(new_entry, k, v)
        except self.PostModel.DoesNotExist:
            new_entry = index.add_child(
                instance=self.PostModel(
                    **self.mappings(
                        index,
                        locale,
                        post_id,
                        published,
                        title,
                        date,
                        slug,
                        body,
                        excerpt,
                        user,
                        authors,
                        meta,
                    ),
                    **kwargs,
                )
            )

        new_entry.country = []
        for key, value in meta.items():
            if key in self.meta_mappings.keys():
                value = self.meta_mappings[key][1](value, new_entry, self.index_page)
                print(f"Setting {key} to {value}")
                setattr(
                    new_entry,
                    self.meta_mappings[key][0],
                    value,
                )

        if not new_entry.authors:
            new_entry.authors = authors

        new_entry.save()

        header_image = None
        featured_image = kwargs.get("featured_image", None)
        if featured_image is not None:
            source = featured_image["source"]
            __, file_ = os.path.split(source)
            source = source.replace("stage.swoon", "swoon")
            try:
                remote_image = urllib.request.urlretrieve(self.prepare_url(source))
                img_buffer = open(remote_image[0], "rb")
                width, height = PILImage.open(img_buffer).size
                img_buffer.seek(0)
                header_image = Image(
                    title=featured_image["title"], width=width, height=height
                )
                header_image.file.save(file_, File(open(img_buffer, "rb")))
                header_image.save()
                print("Found and saved remote image from featured_image value")
            except UnicodeEncodeError:
                print("unable to set header image {}".format(source))

        else:
            api_url = urllib.parse.urljoin(
                self.wordpress_base_url, f"wp-json/wp/v2/posts/{post_id}?_embed"
            )
            try:
                response = urllib.request.urlopen(api_url)
                print(f"Success fetching {api_url}")
                json_data = json.loads(response.read())
                if json_data["featured_media"]:
                    print("Using featured_media value")
                    try:
                        featured_image_post_id = json_data["featured_media"]
                        header_image = WordpressMapping.objects.get(
                            wp_post_id=featured_image_post_id
                        ).image
                    except WordpressMapping.DoesNotExist:
                        print(
                            f"Featured Image Post ID {featured_image_post_id} has not been imported"
                        )
                elif json_data["featured_img"]:
                    print("fetching {}".format(json_data["featured_img"]))
                    __, file_ = os.path.split(json_data["featured_img"])
                    remote_image = urllib.request.urlretrieve(
                        urllib.parse.urljoin(
                            self.wordpress_base_url, json_data["featured_img"]
                        ),
                    )
                    img_buffer = open(remote_image[0], "rb")
                    width, height = PILImage.open(img_buffer).size
                    img_buffer.seek(0)
                    header_image = Image(
                        title=f"Featured image for {title}", width=width, height=height
                    )
                    header_image.file.save(file_, File(img_buffer))
                    header_image.save()

            except urllib.error.HTTPError:
                print(f"Error fetching {api_url}")

        print("Setting header image to: {}".format(header_image))
        new_entry.header_image = header_image
        new_entry.save()
        return new_entry
