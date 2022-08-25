from django import forms
from django.utils.translation import ugettext_lazy as _

from . import models


class LibraryFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["region"].label_from_instance = self.region_label_from_instance
        self.fields["topic"].label_from_instance = self.topic_label_from_instance

    region = forms.ModelChoiceField(
        queryset=models.RegionSnippet.objects.all(),
        required=False,
        label=_("Region"),
    )
    topic = forms.ModelChoiceField(
        queryset=models.TopicSnippet.objects.all(),
        required=False,
        label=_("Topic"),
    )
    media_type = forms.CharField(
        required=False,
        label=_("Media type"),
    )

    order_by = forms.ChoiceField(
        choices=[
            ("title", _("Title")),
            ("publisher", _("Publisher")),
            ("-first_published_at", _("Date added")),
        ],
        initial="title",
        required=False,
    )

    @staticmethod
    def region_label_from_instance(obj):
        return obj.name

    @staticmethod
    def topic_label_from_instance(obj):
        return obj.name

    def apply_filter(self, qs):
        cd = self.cleaned_data
        if not cd:
            return qs

        if cd["topic"]:
            qs = qs.filter(mediapage__topics__topic=cd["topic"])

        if cd["region"]:
            qs = qs.filter(mediapage__regions__region=cd["region"])

        if cd["media_type"]:
            qs = qs.filter(mediapage__media_type__icontains=cd["media_type"])

        if cd["order_by"]:
            qs = qs.order_by(cd["order_by"])

        return qs
