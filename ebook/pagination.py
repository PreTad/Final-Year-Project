from collections import OrderedDict
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
class PageNumberSizePagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    page_size = 5
    page_size_query_param = "size"
    max_page_size = 200
    def get_paginated_response(self, data):
        return Response(OrderedDict([
                    ("count", self.page.paginator.count),
                    ("page", self.page.number),
                    ("number_of_pages", self.page.paginator.num_pages),
                    ("result", data),
                    ("totalElements", self.page.paginator.count),
                    ("totalPages", self.page.paginator.num_pages),
                    ("size", self.get_page_size(self.request)),
                    ("number", max(self.page.number - 1, 0)),
               ]))
