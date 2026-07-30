import unittest

from girp.storage import SQLiteCache


class AiSettingsStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = SQLiteCache(":memory:")

    def test_returns_none_when_nothing_saved(self) -> None:
        self.assertIsNone(self.cache.get_ai_settings())

    def test_round_trips_provider_and_key(self) -> None:
        self.cache.save_ai_settings("anthropic", "sk-ant-abc123")
        settings = self.cache.get_ai_settings()
        self.assertEqual(settings["provider"], "anthropic")
        self.assertEqual(settings["api_key"], "sk-ant-abc123")
        self.assertIsNone(settings["model"])
        self.assertIn("updated_at", settings)

    def test_round_trips_optional_model(self) -> None:
        self.cache.save_ai_settings("openai", "sk-openai-abc", model="gpt-4o-mini")
        settings = self.cache.get_ai_settings()
        self.assertEqual(settings["model"], "gpt-4o-mini")

    def test_saving_again_overwrites_previous_settings(self) -> None:
        self.cache.save_ai_settings("anthropic", "key-one")
        self.cache.save_ai_settings("gemini", "key-two")
        settings = self.cache.get_ai_settings()
        self.assertEqual(settings["provider"], "gemini")
        self.assertEqual(settings["api_key"], "key-two")

    def test_delete_removes_settings_and_reports_true(self) -> None:
        self.cache.save_ai_settings("anthropic", "key-one")
        deleted = self.cache.delete_ai_settings()
        self.assertTrue(deleted)
        self.assertIsNone(self.cache.get_ai_settings())

    def test_delete_reports_false_when_nothing_to_delete(self) -> None:
        self.assertFalse(self.cache.delete_ai_settings())


if __name__ == "__main__":
    unittest.main()
