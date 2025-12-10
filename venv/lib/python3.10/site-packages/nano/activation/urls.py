from django.shortcuts import render

from nano.activation.views import activate_key
from nano.compat import re_path


urlpatterns = [
    re_path(r'^activate$',       activate_key, name='nano-activate-key'),
    re_path(r'^activation_ok/$', render,
                             {'template_name': 'nano/activation/activated.html'},
                             name='nano-activation-ok'),
]
