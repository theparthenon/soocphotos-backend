"""Custom pagination classes."""

from rest_framework.pagination import PageNumberPagination


class HugeResultsSetPagination(PageNumberPagination):
    """Custom pagination class for a huge result between 50000 and 100000 items."""

    page_size = 50000
    page_size_query_param = "page_size"
    max_page_size = 100000


class StandardResultsSetPagination(PageNumberPagination):
    """Custom pagination class for a standard result between 1000 and 100000 items."""

    page_size = 10000
    page_size_query_param = "page_size"
    max_page_size = 100000


class RegularResultsSetPagination(PageNumberPagination):
    """Custom pagination class for a regular result between 100 and 100000 items."""

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 100000


class TinyResultsSetPagination(PageNumberPagination):
    """Custom pagination class for a tiny result between 20 and 50 items."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50
