from nano.compat import re_path
from nano.faq import views


urlpatterns = [
    re_path(r'^$',     views.list_faqs),
]
