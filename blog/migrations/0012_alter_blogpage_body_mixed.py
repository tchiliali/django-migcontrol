# Generated by Django 3.2.13 on 2022-07-11 21:20

from django.db import migrations
import wagtail.core.blocks
import wagtail.core.fields
import wagtail.images.blocks
import wagtail_footnotes.blocks


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0011_rm_body_markdown'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blogpage',
            name='body_mixed',
            field=wagtail.core.fields.StreamField([('heading', wagtail.core.blocks.CharBlock(form_classname='full title')), ('paragraph', wagtail_footnotes.blocks.RichTextBlockWithFootnotes()), ('image', wagtail.images.blocks.ImageChooserBlock())], blank=True, help_text='Avoiding this at first because data might be hard to migrate?', verbose_name='body (mixed)'),
        ),
    ]
