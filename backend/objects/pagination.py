"""Custom pagination classes.

We keep the project-wide DRF default of 500 for endpoints where the client wants
"all data" (e.g. map markers), but for human-facing list views we use a small
default and let the client override via `?page_size=...` for `Load more` flows.
"""
from rest_framework.pagination import PageNumberPagination


class SmallPagePagination(PageNumberPagination):
    """20 items by default, capped at 100 — designed for personal-feed list pages
    (My objects / My contributions / My routes etc.) where the user pages through
    their own content with a `Load more` button.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
