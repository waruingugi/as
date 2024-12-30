from rest_framework import pagination


class StandardPageNumberPagination(pagination.PageNumberPagination):
    page_size: int = 100
    max_page_size: int = 100
    page_query_param: str = "page"
    page_size_query_param = "page_size"
