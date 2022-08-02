from uuid import uuid4
from django.db import migrations


def create_libraryindex(apps, schema_editor):
    # Get models
    LibraryIndexPage = apps.get_model('library.LibraryIndexPage')
    ContentType = apps.get_model('contenttypes.ContentType')
    Locale = apps.get_model('wagtailcore.Locale')
    from wagtail.core.models import Page  # noqa

    # Create content type for libraryindexpage model
    libraryindex_content_type, __ = ContentType.objects.get_or_create(
        model='libraryindexpage', app_label='library')

    translation_key = uuid4()

    # Create a new homepage
    for locale in Locale.objects.all():
        home = Page.objects.get(
            locale__language_code=locale.language_code,
            depth=2,
        )
        libraryindex = LibraryIndexPage(
            title="Library",
            draft_title="Library",
            slug='library',
            content_type=libraryindex_content_type,
            locale=locale,
            translation_key=translation_key,
            path=home.path + "0001",
            depth=3,
            numchild=0,
            url_path=home.url_path + "library/",
            live=True,
            show_in_menus=True,
        )

        home.add_child(instance=libraryindex)


def remove_libraryindex(apps, schema_editor):
    # Get models
    LibraryIndexPage = apps.get_model('library.LibraryIndexPage')

    # Delete BlogIndexPage
    # Page and Site objects CASCADE
    LibraryIndexPage.objects.filter(slug="library").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0001_initial'),
        ('home', '0004_create_articles'),
    ]

    operations = [
        migrations.RunPython(create_libraryindex, remove_libraryindex),
    ]
