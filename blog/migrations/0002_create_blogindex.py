from uuid import uuid4
from django.db import migrations


def create_blogindex(apps, schema_editor):
    # Get models
    BlogIndexPage = apps.get_model('blog.BlogIndexPage')
    ContentType = apps.get_model('contenttypes.ContentType')
    Locale = apps.get_model('wagtailcore.Locale')
    from wagtail.core.models import Page  # noqa

    # Create content type for blogindexpage model
    blogindex_content_type, __ = ContentType.objects.get_or_create(
        model='blogindexpage', app_label='blog')

    translation_key = uuid4()

    for locale in Locale.objects.all():
        home = Page.objects.get(
            locale__language_code=locale.language_code,
            depth=2,
        )

        # Create a new homepage
        blogindex= BlogIndexPage(
            title="Blog",
            draft_title="Blog",
            slug='blog',
            content_type=blogindex_content_type,
            locale=locale,
            path=home.path + "0001",
            depth=3,
            numchild=0,
            url_path=home.url_path + "blog/",
            live=True,
        )

        home.add_child(instance=blogindex)


def remove_blogindex(apps, schema_editor):
    # Get models
    BlogIndexPage = apps.get_model('blog.BlogIndexPage')

    # Delete BlogIndexPage
    # Page and Site objects CASCADE
    BlogIndexPage.objects.filter(slug="blog").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0001_initial'),
        ('home', '0004_create_articles'),
    ]

    operations = [
        migrations.RunPython(create_blogindex, remove_blogindex),
    ]
