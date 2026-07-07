import json
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_liveness_check_success(self):
        url = reverse("health_check")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response["Cache-Control"], "no-store, no-cache, must-revalidate, max-age=0")
        
        data = json.loads(response.content)
        self.assertEqual(data, {"status": "ok"})

    def test_readiness_check_success(self):
        url = reverse("readiness_check")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response["Cache-Control"], "no-store, no-cache, must-revalidate, max-age=0")
        
        data = json.loads(response.content)
        self.assertEqual(data, {"status": "ready", "database": "ok"})

    def test_readiness_check_failure(self):
        url = reverse("readiness_check")
        
        # Mock connection cursor execute to raise an OperationalError or similar database exception
        with patch("django.db.connection.cursor") as mock_cursor:
            mock_cursor.side_effect = Exception("Simulated connection timeout")
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response["Content-Type"], "application/json")
            self.assertEqual(response["Cache-Control"], "no-store, no-cache, must-revalidate, max-age=0")
            
            data = json.loads(response.content)
            # Ensure details of exception are NOT exposed
            self.assertEqual(data, {"status": "unavailable", "database": "error"})
            self.assertNotIn("timeout", str(data))
            self.assertNotIn("Exception", str(data))
