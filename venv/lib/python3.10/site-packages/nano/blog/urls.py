from nano.blog import views
from nano.compat import re_path

urlpatterns = [
    re_path(r'^(?P<year>\d{4})/(?P<month>[01]\d)/(?P<day>[0123]\d)/$', views.list_entries_by_date),
    re_path(r'^(?P<year>\d{4})/(?P<month>[01]\d)/$', views.list_entries_by_year_and_month),
    re_path(r'^(?P<year>\d{4})/$',     views.list_entries_by_year),
    re_path(r'^latest/$',              views.list_latest_entries),
    re_path(r'^today/$',               views.list_entries_for_today),
    re_path(r'^$',                     views.list_entries),
]
