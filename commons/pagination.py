from rest_framework import pagination

from commons.constants import PAGE_SIZE


class StandardPageNumberPagination(pagination.PageNumberPagination):
    page_size: int = PAGE_SIZE
    max_page_size: int = PAGE_SIZE
    page_query_param: str = "page"
    page_size_query_param = "page_size"


class MultiplierPageNumberPagination(pagination.PageNumberPagination):
    page_size: int = 150
    max_page_size: int = 150
    page_query_param: str = "page"
    page_size_query_param = "page_size"
