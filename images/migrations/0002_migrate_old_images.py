from django.db import migrations


# WARNING! ON POSTGRES YOU HAVE TO LOG IN AND RESET THE PRIMARY KEY SEQUENCE
# FOR NEW IMAGES TO BE ADDED
# ALTER SEQUENCE images_customimage_id_seq RESTART WITH 482;
def forwards_func(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    Image = apps.get_model("wagtailimages", "Image")
    CustomImage = apps.get_model("images", "CustomImage")
    CustomRendition = apps.get_model("images", "CustomRendition")

    for old_img in Image.objects.all():

        new_image = CustomImage.objects.create(
            pk=old_img.pk,
            title=old_img.title,
            file=old_img.file,
            width=old_img.width,
            height=old_img.height,
            created_at=old_img.created_at,
            uploaded_by_user=old_img.uploaded_by_user,
            tags=old_img.tags,
            focal_point_x=old_img.focal_point_x,
            focal_point_y=old_img.focal_point_y,
            focal_point_width=old_img.focal_point_width,
            focal_point_height=old_img.focal_point_height,
            file_size=old_img.file_size,
        )

        for old_rendition in old_img.renditions.all():
            CustomRendition.objects.create(
                filter_spec=old_rendition.filter_spec,
                file=old_rendition.file,
                width=old_rendition.width,
                height=old_rendition.height,
                focal_point_key=old_rendition.focal_point_key,
                image=new_image,
            )


def reverse_func(apps, schema_editor):
    CustomImage = apps.get_model("images", "CustomImage")
    db_alias = schema_editor.connection.alias
    CustomImage.objects.using(db_alias).all().delete()


class Migration(migrations.Migration):

    dependencies = [("images", "0001_initial")]

    operations = [migrations.RunPython(forwards_func, reverse_func)]
