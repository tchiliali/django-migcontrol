# models.py
from django.db import models
from wagtail.images.models import AbstractImage
from wagtail.images.models import AbstractRendition
from wagtail.images.models import Image


class CustomImage(AbstractImage):
    # Add any extra fields to image here

    # eg. To add a caption field:
    caption = models.CharField(max_length=1024, blank=True)

    admin_form_fields = Image.admin_form_fields + (
        # Then add the field names here to make them appear in the form:
        "caption",
    )


class CustomRendition(AbstractRendition):
    image = models.ForeignKey(
        CustomImage, on_delete=models.CASCADE, related_name="renditions"
    )

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)
