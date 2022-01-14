import os
import urllib

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand
from PIL import Image as PILImage
from wagtail.documents.models import Document
from wagtail.images.models import Image

from blog import models
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


class Command(BaseCommand):
    """
    Fetches media from a Wordpress XML and stores in Wagtail's Images or
    Documents models.

    Mappings between Wagtail IDs and old Wordpress post_ids (which each media
    item has) needs storage too.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "xml",
            help="Path to Wordpress XML exported media",
        )
        parser.add_argument(
            "--wp-uploads-url",
            type=str,
            default=None,
            help="URL prefix of imported blog's media prefix, e.g.: https://blog.com/wp-content/uploads/",
        )

    def handle(self, *args, **options):
        """gets data from WordPress site"""

        self.base_url = options["wp_uploads_url"]

        self.xml_path = options.get("xml")

        self.xml_parser = XML_parser(self.xml_path, only_attachments=True)
        posts = self.xml_parser.get_posts_data()

        print("Parsed XML, will now import {} items".format(len(posts)))

        for post in posts:
            self.import_to_wagtail(post)

    def import_to_wagtail(self, post):
        """create Image objects and transfer image files to media root"""

        if post["attachment_url"]:
            full_url = post["attachment_url"]
            url_path = urllib.parse.urlparse(full_url).path
        else:
            url_path = post["meta"]["_wp_attached_file"]
            if not url_path:
                print("WHAT")

        extension = url_path.split(".")[-1].lower()
        full_url = urllib.parse.urljoin(self.base_url, urllib.parse.quote(url_path))

        if models.WordpressMapping.objects.filter(wp_url=url_path).exists():
            # Already imported
            print(f"Already imported: {url_path}")
            return
        if models.WordpressMapping.objects.filter(wp_post_id=post["ID"]).exists():
            # Already imported
            print(f"Already imported: {url_path}")
            return
        if extension in ("jpg", "jpeg", "png", "gif"):
            self.import_image(full_url, url_path, title=post["title"], wp_id=post["ID"])
        else:
            self.import_document(
                full_url, url_path, title=post["title"], wp_id=post["ID"]
            )

    def import_image(self, full_url, url_path, title, wp_id):
        __, orig_filename = os.path.split(full_url)
        try:
            remote_image = urllib.request.urlretrieve(full_url)
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            UnicodeEncodeError,
            ValueError,
        ) as e:
            print(f"Ignored - Unable to import image: {full_url}, exception: {e}")
            return
        img_buffer = open(remote_image[0], "rb")
        width, height = PILImage.open(img_buffer).size
        img_buffer.seek(0)
        image = Image(title=title, width=width, height=height)
        try:
            image.file.save(orig_filename, File(img_buffer))
            image.save()
        except TypeError as e:
            print("Unable to import image {}, exception: {}".format(remote_image[0], e))
            raise

        print(f"Successfully imported {full_url}")
        models.WordpressMapping.objects.create(
            wp_url=url_path,
            image=image,
            wp_post_id=wp_id,
        )

    def import_document(self, full_url, url_path, title, wp_id):
        __, orig_filename = os.path.split(url_path)
        try:
            remote_file = urllib.request.urlretrieve(full_url)
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            UnicodeEncodeError,
            ValueError,
        ):
            print(f"Ignored - Unable to import document: {full_url}")
            return

        document = Document(title=title)
        try:
            file_buffer = open(remote_file[0], "rb")
            document.file.save(orig_filename, File(file_buffer))
            document.save()
        except TypeError:
            print("Unable to import document {}".format(remote_file[0]))
            raise

        print(f"Successfully imported {url_path}")
        models.WordpressMapping.objects.create(
            wp_url=url_path,
            document=document,
            wp_post_id=wp_id,
        )
