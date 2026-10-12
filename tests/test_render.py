import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import render


class RefreshTests(unittest.TestCase):
    def test_bio_conversion(self):
        with patch.object(render, 'fetch', return_value='const biography = {"Web": ` JC at <a href=\'https://example.com\'>Aalto</a>. <br> Second paragraph. `};'):
            self.assertEqual(render.website_bio('https://example.com/bio.js'), 'JC at [Aalto](https://example.com).\n\nSecond paragraph.')
        with patch.object(render, 'fetch', return_value='const biography = {};'):
            with self.assertRaises(ValueError):
                render.website_bio('https://example.com/bio.js')

    def test_transfer_dedup_and_failure_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            info = {'bio_source': 'https://example.com/bio.js',
                    'pub': ['Old/Project', 'HINTLab/Project'], 'preprint': [], 'edu': [], 'misc': [],
                    'exclude_repos': ['HINTLab/.github']}
            (root/'info.json').write_text(json.dumps(info))
            (root/'template.md').write_text((Path(render.__file__).parent/'template.md').read_text())
            with patch.object(render, 'website_bio', return_value='Current bio'), \
                 patch.object(render, 'parse_repo', return_value=render.Repo('HINTLab/Project', 'Existing', 5, 2, 0)):
                output = render.main(root/'info.json', root/'template.md', root/'README.md')
            self.assertEqual(output.count('* [HINTLab/Project]'), 1)
            self.assertNotIn('HINTLab/.github', output)
            self.assertIn('Total Stars: 5. Total Forks: 2.', output)
            self.assertIn('<details>\n<summary>Total Stars:', output)
            self.assertNotIn('<details open', output)
            self.assertIn('Refreshed by GitHub Actions on ', output)
            self.assertIn('### Research', output)
            self.assertNotIn('### Publications', output)
            self.assertLess(output.index('</summary>'), output.index('* [HINTLab/Project]'))
            self.assertLess(output.index('* [HINTLab/Project]'), output.index('</details>'))
            previous = (root/'README.md').read_text()
            with patch.object(render, 'website_bio', side_effect=ValueError('source failed')):
                with self.assertRaises(ValueError):
                    render.main(root/'info.json', root/'template.md', root/'README.md')
            self.assertEqual((root/'README.md').read_text(), previous)


if __name__ == '__main__':
    unittest.main()
