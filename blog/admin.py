from django.contrib import admin
from django.contrib.admin import ModelAdmin

from . import models


@admin.register(models.WordpressMapping)
class WordpressMappingAdmin(ModelAdmin):
    list_display = ("wp_url", "wp_post_id", "page", "image", "document")
