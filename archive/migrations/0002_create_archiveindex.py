from uuid import uuid4
from django.db import migrations


def create_archiveindex(apps, schema_editor):
    # Get models
    ArchiveIndexPage = apps.get_model('archive.ArchiveIndexPage')
    ContentType = apps.get_model('contenttypes.ContentType')
    Locale = apps.get_model('wagtailcore.Locale')
    from wagtail.core.models import Page  # noqa

    # Create content type for archiveindexpage model
    archiveindex_content_type, __ = ContentType.objects.get_or_create(
        model='archiveindexpage', app_label='archive')

    translation_key = uuid4()

    # Create a new homepage
    for locale in Locale.objects.all():
        home = Page.objects.get(
            locale__language_code=locale.language_code,
            depth=2,
        )
        archiveindex = ArchiveIndexPage(
            title="Archive",
            draft_title="Archive",
            slug='archive',
            content_type=archiveindex_content_type,
            locale=locale,
            translation_key=translation_key,
            path=home.path + "0001",
            depth=3,
            numchild=0,
            url_path=home.url_path + "archive/",
            live=True,
            show_in_menus=True,
        )

        home.add_child(instance=archiveindex)


def remove_archiveindex(apps, schema_editor):
    # Get models
    ArchiveIndexPage = apps.get_model('archive.BlogIndexPage')

    # Delete BlogIndexPage
    # Page and Site objects CASCADE
    ArchiveIndexPage.objects.filter(slug="archive").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0001_initial'),
        ('home', '0004_create_articles'),
    ]

    operations = [
        migrations.RunPython(create_archiveindex, remove_archiveindex),
    ]
