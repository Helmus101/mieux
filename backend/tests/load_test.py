"""Load test for 100 concurrent users.

Run locally with:
    cd backend
    python -m pip install locust
    locust -f tests/load_test.py --host=http://127.0.0.1:8010

Then open http://localhost:8089 and set users=100, spawn rate=10, run time=5m
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__) + "/..")
os.environ["DATABASE_URL"] = "sqlite:///./foodiq.db"

from locust import HttpUser, task, between, TaskSet
import secrets


class ScannerTasks(TaskSet):
    """Simulates typical user interactions: scan, search alternatives, view products."""

    def on_start(self):
        """Generate a unique session ID for this user."""
        self.session_id = secrets.token_hex(16)
        self.headers = {"X-Session-Id": self.session_id}

    @task(3)
    def scan_product(self):
        """Most common: scan a barcode and view the product."""
        # Common product barcodes in France
        barcodes = [
            "3017620425035",  # Nutella
            "4006381333912",  # Lindt chocolate
            "7622210449283",  # Nescafé
            "4008459000065",  # Knoppers
        ]
        barcode = barcodes[hash(self.session_id) % len(barcodes)]
        self.client.get(f"/v1/products/{barcode}", headers=self.headers, name="/v1/products/{barcode}")

    @task(2)
    def find_alternatives(self):
        """Search for alternatives to a product."""
        self.client.post(
            "/v1/products/3017620425035/alternatives",
            json={
                "category_mode": "same",
                "priorities": ["overall"],
                "strict_additives": True,
                "chains": [],
                "location": None,
                "nearby_only": False,
                "sort_by": "quality",
                "limit": 20,
            },
            headers=self.headers,
            name="/v1/products/{barcode}/alternatives"
        )

    @task(1)
    def log_visit(self):
        """Log a page visit."""
        self.client.post(
            "/v1/usage/visit",
            json={"surface": "app"},
            headers=self.headers,
            name="/v1/usage/visit"
        )

    @task(1)
    def check_health(self):
        """Check API health."""
        self.client.get("/v1/health", name="/v1/health")


class ScannerUser(HttpUser):
    """Simulates a Mieux user actively scanning products."""
    tasks = [ScannerTasks]
    wait_time = between(2, 5)  # Wait 2-5 seconds between tasks
