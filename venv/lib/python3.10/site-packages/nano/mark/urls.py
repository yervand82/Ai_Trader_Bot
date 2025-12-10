from nano.compat import re_path
from nano.mark import views


urlpatterns = [
    re_path(r'^toggle$',    views.toggle_mark, name='toggle_mark'),
]
