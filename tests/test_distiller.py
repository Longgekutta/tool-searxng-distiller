import unittest
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "hub"))

from token_distiller import TokenDistiller

class TestTokenDistiller(unittest.TestCase):
    def test_strip_html_boilerplate(self):
        raw_html = """
        <html>
            <head><script>alert('noise');</script><style>.ad{color:red}</style></head>
            <body>
                <header><nav><a href='/'>Menu</a></nav></header>
                <main>
                    <h1>Core Architecture</h1>
                    <p>SearXNG provides multi-engine aggregation.</p>
                </main>
                <footer>Copyright 2026</footer>
            </body>
        </html>
        """
        result = TokenDistiller.distill_html(raw_html)
        self.assertIn("Core Architecture", result.cleaned_text)
        self.assertIn("SearXNG provides multi-engine aggregation", result.cleaned_text)
        self.assertNotIn("alert('noise')", result.cleaned_text)
        self.assertNotIn("Copyright 2026", result.cleaned_text)
        self.assertGreater(result.compression_ratio_pct, 50.0)

if __name__ == "__main__":
    unittest.main()
