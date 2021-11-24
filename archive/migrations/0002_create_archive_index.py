import uuid

from django.conf import settings
from django.db import migrations

# slug: title, translation_key
homepage_translation_key = uuid.uuid4()

pages = {
    "archive": ("Archive", uuid.uuid4()),
}


def create_pages(apps, schema_editor):
    # Get models
    ArchiveIndexPage = apps.get_model('archive.ArchiveIndexPage')
    ContentType = apps.get_model('contenttypes.ContentType')
    Locale = apps.get_model('wagtailcore.Locale')
    from wagtail.core.models import Page, Locale as LocaleNonMigrated  # noqa

    # Create content type for blogindexpage model
    article_content_type, __ = ContentType.objects.get_or_create(
        model='archiveindexpage', app_label='archive')

    for language_code, __ in settings.LANGUAGES:

        locale = Locale.objects.get(language_code=language_code)

        home = Page.objects.get(
            locale__language_code=language_code,
            slug=f"home-{language_code}" if language_code != "en" else "home",
        )

        for index, (slug, (title, translation_key)) in enumerate(pages.items()):
            index_offset = index + 1
            # Create a new homepage
            article = ArchiveIndexPage(
                title=title,
                draft_title=title,
                slug=f"{slug}",
                content_type=article_content_type,
                locale=locale,
                path=f"{home.path}000{index_offset}",
                depth=3,
                numchild=0,
                translation_key=translation_key,
                url_path="/home{home_append}/{slug}/".format(
                    slug=slug,
                    home_append=f"-{language_code}" if language_code != "en" else ""
                ),
                live=True,
            )

            home.add_child(instance=article)


def remove_pages(apps, schema_editor):
    # Get models
    ArchiveIndexPage = apps.get_model('archive.ArchiveIndexPage')

    # Delete BlogIndexPage
    # Page and Site objects CASCADE
    ArchiveIndexPage.objects.filter(slug="archive").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0001_initial'),
        ('home', '0004_create_articles'),
    ]

    operations = [
        migrations.RunPython(create_pages, remove_pages),
    ]
