import unittest
import pytest
from httpx import AsyncClient
try:
    from httpx import ASGITransport
    HAS_ASGI_TRANSPORT = True
except ImportError:
    HAS_ASGI_TRANSPORT = False

from backend.vault.repository import Repository, init_db
from backend.vault.models import JobStatus
from dashboard.main import app

def create_async_client():
    if HAS_ASGI_TRANSPORT:
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    return AsyncClient(app=app, base_url="http://test")

class TestVaultRepository(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await init_db()

    async def test_repository_views_aggregation(self):
        """Validates that get_total_views returns an int and accurately aggregates across records."""
        initial_views = await Repository.get_total_views()
        self.assertIsInstance(initial_views, int)
        self.assertGreaterEqual(initial_views, 0)

        job = await Repository.create_job("Test Views Niche")
        await Repository.record_analytics(job_id=job.id, views=12500, likes=1200)

        updated_views = await Repository.get_total_views()
        self.assertEqual(updated_views, initial_views + 12500)

        # Add another record to verify cumulative sum
        await Repository.record_analytics(job_id=job.id, views=7500, likes=800)
        final_views = await Repository.get_total_views()
        self.assertEqual(final_views, initial_views + 20000)

    async def test_repository_jobs_count_aggregation(self):
        """Validates that get_completed_jobs_count and get_active_jobs_count accurately track status."""
        initial_completed = await Repository.get_completed_jobs_count()
        initial_active = await Repository.get_active_jobs_count()
        self.assertIsInstance(initial_completed, int)
        self.assertIsInstance(initial_active, int)

        # Create active job
        job_active = await Repository.create_job("Active Job Niche")
        self.assertEqual(await Repository.get_active_jobs_count(), initial_active + 1)
        self.assertEqual(await Repository.get_completed_jobs_count(), initial_completed)

        # Create completed job
        job_completed = await Repository.create_job("Completed Job Niche")
        await Repository.update_job_status(job_completed.id, JobStatus.COMPLETED)
        self.assertEqual(await Repository.get_completed_jobs_count(), initial_completed + 1)

        # Transition active job to completed
        await Repository.update_job_status(job_active.id, JobStatus.COMPLETED)
        self.assertEqual(await Repository.get_active_jobs_count(), initial_active)
        self.assertEqual(await Repository.get_completed_jobs_count(), initial_completed + 2)

    async def test_vault_api_contract_and_status(self):
        """Validates that GET /api/vault returns HTTP 200 with complete metrics and schema contract."""
        async with create_async_client() as client:
            response = await client.get("/api/vault")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Validate top-level keys
        for key in ["metrics", "styleGuides", "characterBibles", "hookFormulas", "logs"]:
            self.assertIn(key, data)

        metrics = data["metrics"]
        required_metric_fields = [
            "totalSpent",
            "totalTokens",
            "totalRevenue",
            "dailyBudget",
            "activeJobsCount",
            "completedJobsCount",
            "totalViews"
        ]

        for field in required_metric_fields:
            self.assertIn(field, metrics, f"Missing metric field: {field}")
            # Ensure raw numbers (not boolean, not string)
            self.assertNotIsInstance(metrics[field], bool, f"{field} must not be boolean")
            self.assertIsInstance(metrics[field], (int, float), f"{field} must be numeric")

        # Strict integer validation for counts and views
        self.assertIsInstance(metrics["totalViews"], int)
        self.assertIsInstance(metrics["totalTokens"], int)
        self.assertIsInstance(metrics["activeJobsCount"], int)
        self.assertIsInstance(metrics["completedJobsCount"], int)

        # Array validations
        self.assertIsInstance(data["styleGuides"], list)
        self.assertIsInstance(data["characterBibles"], list)
        self.assertIsInstance(data["hookFormulas"], list)
        self.assertIsInstance(data["logs"], list)

    async def test_vault_api_with_populated_extras(self):
        """Validates that style guides, character bibles, hooks, and logs are serialized correctly."""
        await Repository.upsert_style_guide(
            niche="Cybersecurity",
            data={
                "archetype": "Neon Grid Noir",
                "primaryColor": "#050505",
                "accentColor": "#00FFCC",
                "typography": "JetBrains Mono",
                "cutFrequency": "1.5s",
                "music": "Cyber Synthwave"
            }
        )
        await Repository.upsert_character_bible(
            niche="Cybersecurity",
            data={
                "characterName": "The Analyst",
                "persona": "Calm, tactical, analytical",
                "visualDescription": "Dark hoodie, holographic interface"
            }
        )
        await Repository.upsert_hook_formula(
            formula="Every company will be hacked by this method in 2026.",
            virality_score=97.8
        )
        await Repository.log_event("Automated test log event inserted.")

        async with create_async_client() as client:
            response = await client.get("/api/vault")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check style guide presence
        sg_matches = [sg for sg in data["styleGuides"] if sg["niche"] == "Cybersecurity"]
        self.assertGreaterEqual(len(sg_matches), 1)
        sg = sg_matches[0]
        self.assertEqual(sg["archetype"], "Neon Grid Noir")
        self.assertEqual(sg["primaryColor"], "#050505")
        self.assertEqual(sg["accentColor"], "#00FFCC")

        # Check character bible presence
        cb_matches = [cb for cb in data["characterBibles"] if cb["niche"] == "Cybersecurity"]
        self.assertGreaterEqual(len(cb_matches), 1)
        cb = cb_matches[0]
        self.assertEqual(cb["characterName"], "The Analyst")

        # Check hook formula presence
        hf_matches = [hf for hf in data["hookFormulas"] if "Every company will be hacked" in hf["formula"]]
        self.assertGreaterEqual(len(hf_matches), 1)
        self.assertAlmostEqual(hf_matches[0]["score"], 97.8, places=1)

        # Check logs presence
        log_matches = [l for l in data["logs"] if "Automated test log event inserted." in l["message"]]
        self.assertGreaterEqual(len(log_matches), 1)

@pytest.mark.asyncio
async def test_pytest_vault_endpoint():
    """Standalone pytest test for GET /api/vault endpoint."""
    await init_db()
    async with create_async_client() as client:
        response = await client.get("/api/vault")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "totalViews" in data["metrics"]
    assert isinstance(data["metrics"]["totalViews"], int)
    assert isinstance(data["metrics"]["completedJobsCount"], int)
    assert isinstance(data["metrics"]["activeJobsCount"], int)

if __name__ == "__main__":
    unittest.main()
