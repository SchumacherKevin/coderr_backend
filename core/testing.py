"""Test helpers shared by several apps."""
from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext


class QueryCountMixin:
    """Assert that a GET request does not run one query per row (N+1)."""

    def count_queries(self, url):
        """Request the URL and return the number of database queries."""
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return len(context)

    def assert_queries_constant(self, url, create_more_rows):
        """The query count must not grow when more rows are listed."""
        expected = self.count_queries(url)
        create_more_rows()
        with self.assertNumQueries(expected):
            self.client.get(url)


class AdminQueryCountMixin(QueryCountMixin):
    """Same check for admin change lists, logged in as a superuser."""

    def login_as_admin(self):
        """Create a superuser and log the test client in."""
        admin = User.objects.create_superuser('admin', password='Secret123!')
        self.client.force_login(admin)
