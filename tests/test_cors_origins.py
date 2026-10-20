"""The package explicitly permits custom-domain HTTP/WebSocket origins."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CorsOriginsTest(unittest.TestCase):
    def test_webui_allows_all_origins(self):
        manifest = (ROOT / 'lzc-manifest.yml').read_text()
        webui = manifest.split('\n  hermes-webui:\n', 1)[1]
        environment = webui.split('    environment:\n', 1)[1].split('    binds:', 1)[0]
        self.assertIn('      - CORS_ORIGINS=*\n', environment)
        self.assertEqual(manifest.count('- CORS_ORIGINS='), 1)

    def test_security_tradeoff_is_documented(self):
        readme = (ROOT / 'README.md').read_text()
        self.assertIn('CORS_ORIGINS=*', readme)
        self.assertIn('不取消登录与权限校验', readme)

if __name__ == '__main__':
    unittest.main()
