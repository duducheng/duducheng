import json
import os
import urllib.error
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

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
            self.assertIn(': Existing ', output)
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
            with patch.object(render, 'website_bio', return_value='New bio'), \
                 patch.object(render, 'parse_repo', side_effect=ValueError('repository source failed')):
                with self.assertRaises(ValueError):
                    render.main(root/'info.json', root/'template.md', root/'README.md')
            self.assertEqual((root/'README.md').read_text(), previous)


    def test_transient_fetch_retry_and_api_token_scope(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'ok'
        transient = urllib.error.HTTPError(render.API + 'repos/HINTLab/Test', 503, 'Unavailable', {}, None)
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}, clear=True), \
             patch.object(render.urllib.request, 'urlopen', side_effect=[transient, response]) as opening, \
             patch.object(render.time, 'sleep') as sleeping:
            self.assertEqual(render.fetch(render.API + 'repos/HINTLab/Test'), 'ok')
            self.assertEqual(opening.call_count, 2)
            self.assertEqual(opening.call_args.args[0].get_header('Authorization'), 'Bearer test-token')
            sleeping.assert_called_once_with(1)
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}, clear=True), \
             patch.object(render.urllib.request, 'urlopen', return_value=response) as opening:
            render.fetch('https://example.com/bio.js')
            self.assertIsNone(opening.call_args.args[0].get_header('Authorization'))

    def test_permanent_fetch_error_is_not_retried(self):
        error = urllib.error.HTTPError('https://example.com/missing', 404, 'Not found', {}, None)
        with patch.object(render.urllib.request, 'urlopen', side_effect=error) as opening, \
             patch.object(render.time, 'sleep') as sleeping:
            with self.assertRaisesRegex(RuntimeError, r'https://example.com/missing.*HTTP 404'):
                render.fetch('https://example.com/missing')
            opening.assert_called_once()
            sleeping.assert_not_called()

    def test_atomic_replace_failure_preserves_readme(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'README.md'
            destination.write_text('Existing README')
            with patch.object(render.os, 'replace', side_effect=OSError('disk error')):
                with self.assertRaises(OSError):
                    render.write_readme(destination, 'New README')
            self.assertEqual(destination.read_text(), 'Existing README')
            self.assertEqual(list(Path(folder).iterdir()), [destination])

    def test_invalid_config_fails_before_network(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'info.json').write_text(json.dumps({'bio_source': 'https://example.com/bio.js', 'pub': 'not a list'}))
            with patch.object(render, 'fetch') as fetching:
                with self.assertRaisesRegex(ValueError, 'pub must be a list'):
                    render.main(root/'info.json', root/'template.md', root/'README.md')
                fetching.assert_not_called()


if __name__ == '__main__':
    unittest.main()
