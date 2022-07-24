from django.contrib import admin
from django.contrib.admin import ModelAdmin
from wagtail.contrib.modeladmin.helpers.button import ButtonHelper
from wagtail.contrib.modeladmin.options import ModelAdmin as WagtailModelAdmin
from wagtail.contrib.modeladmin.options import modeladmin_register

from . import models


@admin.register(models.WordpressMapping)
class WordpressMappingAdmin(ModelAdmin):
    list_display = ("wp_url", "wp_post_id", "page", "image", "document")


class BlogButtonHelper(ButtonHelper):

    # Define classes for our button, here we can set an icon for example
    view_button_classnames = ["button-small", "icon", "icon-site"]

    def view_button(self, obj):
        # Define a label for our button
        text = "View {}".format(self.verbose_name)
        return {
            "url": obj.get_absolute_url(),  # decide where the button links to
            "label": text,
            "classname": self.finalise_classname(self.view_button_classnames),
            "title": text,
        }

    def get_buttons_for_obj(
        self, obj, exclude=None, classnames_add=None, classnames_exclude=None
    ):
        """
        This function is used to gather all available buttons.
        We append our custom button to the btns list.
        """
        btns = super().get_buttons_for_obj(
            obj, exclude, classnames_add, classnames_exclude
        )
        if "view" not in (exclude or []):
            btns.append(self.view_button(obj))
        return btns


@modeladmin_register
class BlogPagWagtailAdmin(WagtailModelAdmin):
    model = models.BlogPage
    list_display = ("__str__", "date", "live")
    search_fields = ("title", "body_richtext", "body_mixed")
    menu_icon = "site"
    menu_order = 200
    button_helper_class = BlogButtonHelper
