from collections import OrderedDict
from django.conf import settings
from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.response import Response


class StandardPageNumberPagination(PageNumberPagination):
    """
    Standard Page Number pagination with enforced upper limits.
    Allows clients to control page size via ?page_size=X up to max_page_size.
    """
    page_size = getattr(settings, "PAGE_SIZE_DEFAULT", 20)
    page_size_query_param = "page_size"
    max_page_size = getattr(settings, "PAGE_SIZE_MAX", 100)

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("total_pages", self.page.paginator.num_pages),
                    ("current_page", self.page.number),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )


class StandardCursorPagination(CursorPagination):
    """
    High-performance Keyset/Cursor pagination for high-volume append-only streams.
    Does not run COUNT(*) queries; maintains constant query time at arbitrary depth.
    """
    page_size = getattr(settings, "PAGE_SIZE_DEFAULT", 20)
    page_size_query_param = "page_size"
    max_page_size = getattr(settings, "PAGE_SIZE_MAX", 100)
    ordering = "-clicked_at"  # Default cursor ordering key