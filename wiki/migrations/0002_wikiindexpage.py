from uuid import uuid4
from django.db import migrations


def create_wikiindex(apps, schema_editor):
    # Get models
    WikiIndexPage = apps.get_model('wiki.WikiIndexPage')
    ContentType = apps.get_model('contenttypes.ContentType')
    Locale = apps.get_model('wagtailcore.Locale')
    from wagtail.core.models import Page  # noqa

    # Create content type for wikiindexpage model
    wikiindex_content_type, __ = ContentType.objects.get_or_create(
        model='wikiindexpage', app_label='wiki')

    translation_key = uuid4()

    # Create a new homepage
    for locale in Locale.objects.all():
        home = Page.objects.get(
            locale__language_code=locale.language_code,
            depth=2,
        )
        wikiindex = WikiIndexPage(
            title="Wiki",
            draft_title="Wiki",
            slug='wiki',
            content_type=wikiindex_content_type,
            locale=locale,
            translation_key=translation_key,
            path=home.path + "0001",
            depth=3,
            numchild=0,
            url_path=home.url_path + "wiki/",
            live=True,
            show_in_menus=True,
        )

        home.add_child(instance=wikiindex)


def remove_wikiindex(apps, schema_editor):
    # Get models
    WikiIndexPage = apps.get_model('wiki.WikiIndexPage')

    # Delete BlogIndexPage
    # Page and Site objects CASCADE
    WikiIndexPage.objects.filter(slug="wiki").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('wiki', '0001_initial'),
        ('home', '0004_create_articles'),
    ]

    operations = [
        migrations.RunPython(create_wikiindex, remove_wikiindex),
    ]
