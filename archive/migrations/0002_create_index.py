from django.db import migrations


def create_archiveindex(apps, schema_editor):
    # Get models
    Site = apps.get_model('wagtailcore.Site')
    ArchiveIndexPage = apps.get_model('archive.ArchiveIndexPage')
    ContentType = apps.get_model('contenttypes.ContentType')
    Locale = apps.get_model('wagtailcore.Locale')
    from wagtail.core.models import Page, Locale as LocaleNonMigrated  # noqa

    # Create content type for archiveindexpage model
    archiveindex_content_type, __ = ContentType.objects.get_or_create(
        model='archiveindexpage', app_label='archive')

    home = Page.objects.get(pk=Site.objects.get(is_default_site=True).root_page.pk)
    locale = Locale.objects.get(pk=LocaleNonMigrated.get_default().pk)

    # Create a new homepage
    archiveindex= ArchiveIndexPage(
        title="Archive",
        draft_title="Archive",
        slug='archive',
        content_type=archiveindex_content_type,
        locale=locale,
        path="000100010001",
        depth=3,
        numchild=0,
        url_path="/home/archive/",
        live=True,
    )

    home.add_child(instance=archiveindex)


def remove_archiveindex(apps, schema_editor):
    # Get models
    BlogIndexPage = apps.get_model('archive.BlogIndexPage')

    # Delete BlogIndexPage
    # Page and Site objects CASCADE
    BlogIndexPage.objects.filter(slug="archive").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0001_initial'),
        ('home', '0004_create_articles'),
    ]

    operations = [
        migrations.RunPython(create_archiveindex, remove_archiveindex),
    ]
