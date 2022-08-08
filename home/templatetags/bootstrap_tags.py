from django import template
from django.contrib import messages
from django.forms import BaseForm
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

register = template.Library()


@register.inclusion_tag("bootstrap/form.html", takes_context=True)
def bootstrap_form(context, form_obj, skip_csrf_token=False):
    if not isinstance(form_obj, BaseForm):
        raise TypeError(
            "Error including form, it's not a form, it's a %s" % type(form_obj)
        )
    context.update({"form": form_obj, "skip_csrf_token": skip_csrf_token})
    return context


@register.filter()
def bootstrap_render_field(field, extra_class=""):
    if field.field.widget.input_type == "select":
        extra_class += " form-select"
    if field.field.widget.input_type == "checkbox":
        extra_class += " form-check-input"
    else:
        extra_class += " form-control"
    return field.as_widget(attrs={"class": " " + extra_class})


@register.inclusion_tag("bootstrap/button_panel.html", takes_context=True)
def bootstrap_buttons(
    context,
    submit=_("Submit"),
    submit2_label=None,
    submit2_name=None,
    go_back=None,
    reset=False,
    submit_css_class=None,
):

    if go_back is not None:
        referer = getattr(context.get("request", {}), "META", {}).get(
            "HTTP_REFERER", None
        )
        if not referer:
            referer = reverse("login")
        go_back = {"label": go_back, "referer": referer}

    submit2 = None
    if submit2_label is not None:
        submit2 = {"label": submit2_label, "name": submit2_name}

    context.update(
        {
            "button_submit": submit,
            "go_back": go_back,
            "reset": reset,
            "submit2": submit2,
            "submit_css_class": submit_css_class,
        }
    )
    return context


@register.filter()
def bootstrap_message_tag(message):
    """Takes a message object from django.contrib.message and returns
    a bootstrap danger/warning/info/success/default CSS class"""
    lvl = message.level
    if lvl >= messages.ERROR:
        return "danger"
    if lvl >= messages.WARNING:
        return "warning"
    if lvl >= messages.SUCCESS:
        return "success"
    if lvl >= messages.INFO:
        return "info"
    return "default"
