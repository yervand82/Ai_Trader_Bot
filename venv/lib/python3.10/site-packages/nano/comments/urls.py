from django.contrib.contenttypes.views import shortcut

from nano.comments import views
from nano.compat import re_path


urlpatterns = [
    re_path(r'^$',         views.list_comments, name='comments-list-comments'),
    re_path(r'^post$',     views.post_comment, name='comments-post-comment'),
    re_path(r'^cr/(\d+)/(.+)/$', shortcut, name='comments-url-redirect'),
]
