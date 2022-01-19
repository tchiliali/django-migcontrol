from django.db import migrations

def create_sync(apps, schema_editor):
    LocaleSynchronization = apps.get_model('wagtail_localize.LocaleSynchronization')
    Locale = apps.get_model('wagtailcore.Locale')

    # from: to
    mappings = {
        "en": ("de", "fr", "ar"),
        "de": ("en",),
    }

    for source, dests in mappings.items():
        source_locale = Locale.objects.get(language_code=source)
        for dest in dests:
            dest_locale = Locale.objects.get(language_code=dest)
            LocaleSynchronization.objects.create(
                locale=dest_locale,
                sync_from=source_locale,
            )

def remove_sync(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0006_homepage_body'),
        ('wagtail_localize', '0015_translationcontext_field_path'),
    ]

    operations = [
        migrations.RunPython(create_sync, remove_sync),
    ]
