from django.db import migrations

# slug: title
pages = {
    "about": "About",
    "contact": "Contact",
    "donate": "Donate",
    "subscribe": "Subscribe",
    "imprint": "Imprint",
    "data-protection": "Data protection",
}


def create_pages(apps, schema_editor):
    # Get models
    Site = apps.get_model('wagtailcore.Site')
    Article = apps.get_model('home.Article')
    ContentType = apps.get_model('contenttypes.ContentType')
    Locale = apps.get_model('wagtailcore.Locale')
    from wagtail.core.models import Page, Locale as LocaleNonMigrated  # noqa

    # Create content type for blogindexpage model
    homepage_content_type, __ = ContentType.objects.get_or_create(
        model='article', app_label='home')

    home = Page.objects.get(pk=Site.objects.get(is_default_site=True).root_page.pk)
    locale = Locale.objects.get(pk=LocaleNonMigrated.get_default().pk)

    for index, (slug, title) in enumerate(pages.items()):
        index_offset = index + 1
        # Create a new homepage
        article = Article(
            title=title,
            draft_title=title,
            slug=slug,
            content_type=homepage_content_type,
            locale=locale,
            path=f"00010001000{index_offset}",
            depth=3,
            numchild=0,
            url_path=f"/home/{slug}/",
            live=True,
        )

        home.add_child(instance=article)


def remove_pages(apps, schema_editor):
    # Get models
    BlogIndexPage = apps.get_model('blog.BlogIndexPage')

    # Delete BlogIndexPage
    # Page and Site objects CASCADE
    BlogIndexPage.objects.filter(slug="blog").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0003_article'),
        ('wagtailcore', '0053_locale_model'),
    ]

    operations = [
        migrations.RunPython(create_pages, create_pages),
    ]
