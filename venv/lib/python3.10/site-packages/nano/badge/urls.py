from nano.badge import views
from nano.compat import re_path

urlpatterns = [
    re_path(r'^$',                 views.list_badges, name='badge-list'),
    re_path(r'^(?P<pk>[0-9]+)/$',  views.show_badge, name='badge-detail'),
]
