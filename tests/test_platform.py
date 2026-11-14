import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from liubai import platform as desktop
from liubai.storage import data_directory


class PlatformTests(unittest.TestCase):
    def test_windows_data_uses_local_appdata(self):
        with patch("liubai.storage.sys.platform", "win32"), patch.dict(os.environ, {"LOCALAPPDATA": "/isolated/local"}):
            self.assertEqual(data_directory(), Path("/isolated/local/Liubai"))

    def test_linux_xdg_data_location(self):
        with patch("liubai.storage.sys.platform", "linux"), patch.dict(os.environ, {"XDG_DATA_HOME": "/isolated/share"}):
            self.assertEqual(data_directory(), Path("/isolated/share/liubai"))

    def test_appimage_login_startup_keeps_outer_image_path(self):
        with tempfile.TemporaryDirectory() as directory:
            image = str(Path(directory) / "A path with spaces" / "留白.AppImage")
            with patch("liubai.platform.sys.platform", "linux"), patch.dict(os.environ, {"APPIMAGE": image, "XDG_CONFIG_HOME": directory}):
                desktop.set_autostart(True)
                self.assertTrue(desktop.autostart_enabled())
                content = desktop.autostart_path().read_text(encoding="utf-8")
                self.assertIn(f'Exec={desktop.desktop_quote(image)} "--background"', content)
                self.assertNotIn("/tmp/.mount", content)
                desktop.set_autostart(False)
                self.assertFalse(desktop.autostart_enabled())


if __name__ == "__main__":
    unittest.main()
