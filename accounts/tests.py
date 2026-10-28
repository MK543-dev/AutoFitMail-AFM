import secrets

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse


class LoginRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_too_many_failed_logins_are_blocked(self):
        payload = {'username': 'nobody@example.com', 'password': secrets.token_urlsafe(12)}
        for _ in range(10):
            resp = self.client.post(reverse('login'), payload)
            self.assertEqual(resp.status_code, 200)
        resp = self.client.post(reverse('login'), payload)
        self.assertEqual(resp.status_code, 429)


class PrivacyPageTests(TestCase):
    def test_privacy_page_is_public(self):
        resp = self.client.get(reverse('privacy'))
        self.assertEqual(resp.status_code, 200)
