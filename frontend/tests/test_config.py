import unittest
from backend.config import Settings
from backend.vault.models import StageStatus

class TestConfig(unittest.TestCase):
    def test_settings_load(self):
        s = Settings(telegram_allowed_users_raw="111,222")
        self.assertEqual(s.daily_budget_usd, 5.0)
        self.assertEqual(s.allowed_user_ids, [111, 222])
        self.assertIn("sqlite", s.effective_database_url)
        self.assertEqual(s.gemini_model, "gemini-3.7-flash")
        self.assertEqual(s.scheduler_tick_minutes, 5)

    def test_settings_custom(self):
        s = Settings(daily_budget_usd=15.0, gemini_model="gemini-3.7-flash")
        self.assertEqual(s.daily_budget_usd, 15.0)
        self.assertEqual(s.gemini_model, "gemini-3.7-flash")

    def test_empty_telegram_allowed_users(self):
        s = Settings(telegram_allowed_users_raw="")
        self.assertEqual(s.allowed_user_ids, [])

    def test_effective_db_url(self):
        s = Settings(database_url="postgresql+asyncpg://user:pass@localhost/db")
        self.assertIn("postgresql", s.effective_database_url)

    def test_stage_definitions(self):
        self.assertEqual(len(list(StageStatus)), 10)

if __name__ == "__main__":
    unittest.main()
