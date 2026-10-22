"""The package preserves upstream same-host origin protection by default."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
class CorsOriginsTest(unittest.TestCase):
    def test_webui_does_not_override_upstream_origin_policy(self):
        manifest = (ROOT / 'lzc-manifest.yml').read_text()
        self.assertNotIn('- CORS_ORIGINS=', manifest)
        self.assertNotIn('Allow custom domains through reverse proxies', manifest)
    def test_default_and_explicit_allowlist_are_documented(self):
        readme = (ROOT / 'README.md').read_text()
        self.assertNotIn('CORS_ORIGINS=*', readme)
        self.assertIn('同主机来源校验', readme)
        self.assertIn('精确的来源白名单', readme)
if __name__ == '__main__':
    unittest.main()
