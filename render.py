#!/usr/bin/env python3
"""Refresh the profile from the website bio and public GitHub repositories."""

import datetime
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request
from collections import namedtuple

Repo = namedtuple('Repo', ['name', 'description', 'stars', 'forks', 'open_issues'])
API = 'https://api.github.com/'


def fetch(url):
    headers = {'User-Agent': 'duducheng-profile-refresh'}
    # Only GitHub API requests receive the optional token; the website does not.
    if url.startswith(API) and os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    request = urllib.request.Request(url, headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode('utf-8')
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def fetch_json(route):
    return json.loads(fetch(API + route))


def parse_repo(repo_name):
    data = fetch_json('repos/' + repo_name)
    if data['private']:
        raise ValueError('Refusing to include private repository: ' + repo_name)
    return Repo(data['full_name'], data['description'] or '',
                data['stargazers_count'], data['forks_count'], data['open_issues_count'])


def website_bio(url):
    source = fetch(url)
    match = re.search(r'[\"\']Web[\"\']\s*:\s*`([^`]*)`', source, re.MULTILINE)
    if not match or not match.group(1).strip():
        raise ValueError('Website Web biography missing; README was not changed')
    bio = re.sub(r'<a\s+href=[\"\']([^\"\']+)[\"\']>(.*?)</a>',
                 r'[\2](\1)', match.group(1).strip(), flags=re.DOTALL)
    bio = re.sub(r'<br\s*/?>', '\n\n', bio)
    bio = re.sub(r'</?(?:u|b|strong|em)>', '', bio)
    return '\n\n'.join(' '.join(part.split()) for part in bio.split('\n\n') if part.strip())


def repo_to_line(repo):
    description = ' '.join((repo.description or repo.name.split('/')[-1]).split())
    return (f'* [{repo.name}](https://github.com/{repo.name}): {description} '
            f'![stars: {repo.stars}](https://img.shields.io/github/stars/{repo.name}) '
            f'![forks: {repo.forks}](https://img.shields.io/github/forks/{repo.name})')


def main(info_path='info.json', template_path='template.md', output_path='README.md', write_summary=True):
    info = json.loads(Path(info_path).read_text())
    template = Path(template_path).read_text()
    bio = website_bio(info['bio_source'])
    sections = {key: list(info[key]) for key in ('pub', 'preprint', 'edu', 'misc')}
    excluded = {name.lower() for name in info.get('exclude_repos', [])}
    # Resolving through the API follows transfers and writes canonical owner/name.
    resolved = {}
    seen = set()
    for section, names in sections.items():
        canonical = []
        for name in names:
            repo = parse_repo(name)
            key = repo.name.lower()
            if key not in seen and key not in excluded:
                canonical.append(repo.name)
                resolved[repo.name] = repo
                seen.add(key)
        sections[section] = canonical
    headers = {'pub': '### Research', 'preprint': '### Preprints / Challenges / Technical Reports',
               'edu': '### Educational', 'misc': '## Misc.'}
    blocks = {}
    total_stars = total_forks = 0
    for section, names in sections.items():
        lines = []
        for name in names:
            repo = resolved[name]
            repo = repo._replace(description=info.get('description_overrides', {}).get(name, repo.description))
            lines.append(repo_to_line(repo))
            total_stars += repo.stars
            total_forks += repo.forks
            print(f'{name}: {repo.stars} stars, {repo.forks} forks')
        blocks[section] = headers[section] + '\n\n' + '\n'.join(lines) if lines else ''
    output = re.sub(r'\n{3,}', '\n\n', template.format(bio=bio, **blocks)).rstrip()
    if write_summary:
        output += (f'\n\nTotal Stars: {total_stars}. Total Forks: {total_forks}. '
                   f'Updated on {datetime.datetime.now(datetime.timezone.utc):%B %d, %Y}.')
    # All sources must succeed before replacing the previous README.
    if output_path is not None:
        Path(output_path).write_text(output + '\n')
    return output


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    main(root / 'info.json', root / 'template.md', root / 'README.md')
