from django.test import TestCase
from django.conf import settings


class SettingsConfigurationTests(TestCase):
    def test_timezone_is_utc(self):
        self.assertEqual(settings.TIME_ZONE, "UTC")

    def test_default_auto_field(self):
        self.assertEqual(settings.DEFAULT_AUTO_FIELD, "django.db.models.BigAutoField")

    def test_debug_and_cookie_security_consistency(self):
        import os
        env_debug = os.environ.get("DEBUG", "True").lower() == "true"
        if not env_debug:
            self.assertTrue(settings.SESSION_COOKIE_SECURE)
            self.assertTrue(settings.CSRF_COOKIE_SECURE)
            self.assertEqual(
                settings.SECURE_PROXY_SSL_HEADER,
                ('HTTP_X_FORWARDED_PROTO', 'https')
            )
            self.assertIn("whitenoise", settings.STORAGES["staticfiles"]["BACKEND"].lower())
