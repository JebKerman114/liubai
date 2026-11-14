import json
import tempfile
import unittest
from pathlib import Path

from liubai.storage import Store, validate


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.store = Store(self.directory)

    def test_unicode_tasks_and_notes_survive_restart(self):
        self.assertIsNone(self.store.add_task("  "))
        task = self.store.add_task("  整理今天的思绪  ")
        task["done"] = True
        note = self.store.add_note()
        note.update(title="周末灵感", body="第一行\n第二行 ✓\n🪴", color=2)
        self.store.data["settings"]["pinned"] = False
        self.store.save()
        restored = Store(self.directory)
        self.assertEqual(restored.data, self.store.data)
        self.assertEqual(restored.data["tasks"][0]["text"], "整理今天的思绪")

    def test_recovers_previous_valid_revision_and_preserves_damaged_file(self):
        self.store.add_task("第一版")
        self.store.save()
        self.store.add_task("第二版")
        self.store.save()
        self.store.path.write_text("{ broken", encoding="utf-8")
        recovered = Store(self.directory)
        self.assertTrue(recovered.warning)
        self.assertEqual(len(recovered.data["tasks"]), 1)
        self.assertEqual(len(list(self.directory.glob("data.damaged-*.json"))), 1)
        recovered.save()
        self.assertEqual(Store(self.directory).data, recovered.data)
        self.assertEqual(Store.read(recovered.backup)["tasks"][0]["text"], "第一版")

    def test_rejects_bad_records_before_overwriting_saved_data(self):
        note = self.store.add_note()
        self.store.save()
        before = self.store.path.read_bytes()
        note["color"] = 12
        with self.assertRaises(ValueError):
            self.store.save()
        self.assertEqual(self.store.path.read_bytes(), before)
        note["color"] = 0
        note["updated"] = "broken date"
        with self.assertRaises(ValueError):
            validate(self.store.data)

    def test_no_backup_does_not_silently_reset_corrupt_data(self):
        self.store.path.write_text("not JSON", encoding="utf-8")
        with self.assertRaises(ValueError):
            Store(self.directory)
        self.assertEqual(self.store.path.read_text(), "not JSON")

    def test_duplicate_ids_are_rejected(self):
        task = self.store.add_task("一件小事")
        self.store.data["tasks"].append(dict(task))
        with self.assertRaises(ValueError):
            self.store.save()


if __name__ == "__main__":
    unittest.main()
