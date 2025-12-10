from __future__ import unicode_literals

from nano.compat import re_path
from nano.privmsg import views


urlpatterns = [
    re_path(r'^add$',          views.add_pm, name='add_pm'),
    re_path(r'^(?P<msgid>[1-9][0-9]*)/archive$', views.move_to_archive, name='archive_pm'),
    re_path(r'^(?P<msgid>[1-9][0-9]*)/delete$', views.delete, name='delete_pm'),
    #re_path(r'^(?:(?P<action>(archive|sent))/?)?$', views.show_pms, name='show_pms'),
    re_path(r'^archive/$', views.show_pm_archived, name='show_archived_pms'),
    re_path(r'^sent/$', views.show_pm_sent, name='show_sent_pms'),
    re_path(r'^$', views.show_pm_received, name='show_pms'),
    #re_path(r'^$', views.show_pms, {u'action': u'received'}, name='show_pms'),
]
