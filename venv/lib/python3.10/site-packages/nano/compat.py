import django

if django.VERSION[:2] < (2, 2):
    from django.utils.encoding import force_text as force_str
    from django.conf.urls import include, url as re_path
else:
    from django.utils.encoding import force_str
    from django.urls import include, re_path


__all__ = [
    "force_str",
    "re_path",
]
