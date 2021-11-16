from django.db import migrations


def create_blogindex(apps, schema_editor):
    # Get models
    Site = apps.get_model('wagtailcore.Site')
    BlogIndexPage = apps.get_model('blog.BlogIndexPage')
    ContentType = apps.get_model('contenttypes.ContentType')
    Locale = apps.get_model('wagtailcore.Locale')
    from wagtail.core.models import Page, Locale as LocaleNonMigrated  # noqa

    # Create content type for blogindexpage model
    blogindex_content_type, __ = ContentType.objects.get_or_create(
        model='blogindexpage', app_label='blog')

    home = Page.objects.get(pk=Site.objects.get(is_default_site=True).root_page.pk)
    locale = Locale.objects.get(pk=LocaleNonMigrated.get_default().pk)

    # Create a new homepage
    blogindex= BlogIndexPage(
        title="Blog",
        draft_title="Blog",
        slug='blog',
        content_type=blogindex_content_type,
        locale=locale,
        path="000100010001",
        depth=3,
        numchild=0,
        url_path="/home/blog/",
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
        ('home', '0002_create_homepage'),
    ]

    operations = [
        migrations.RunPython(create_blogindex, remove_blogindex),
    ]
