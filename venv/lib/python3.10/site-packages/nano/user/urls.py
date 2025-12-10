from django.shortcuts import render

from nano.compat import re_path
from nano.user import views


signup_done_data = {'template_name': 'nano/user/signup_done.html'}

# 'project_name' should be a setting
password_reset_data = {'project_name': 'CALS'}

urlpatterns = [
    re_path(r'^signup/$',           views.signup, name='nano_user_signup'),
    re_path(r'^password/reset/$',   views.password_reset, password_reset_data, name='nano_user_password_reset'),
    re_path(r'^password/change/$',  views.password_change, name='nano_user_password_change'),
    re_path(r'^signup/done/$',      render, signup_done_data, name='nano_user_signup_done'),
]
