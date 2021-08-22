#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import urllib.request
from collections import namedtuple
import datetime

Repo = namedtuple("Repo", ["name", "description",
                           "stars", "forks", "open_issues"])


def parse_repo(repo_name: str) -> Repo:
    print("Parsing {}...".format(repo_name), end=", ")
    api = "https://api.github.com/repos/"
    parsed_json = json.loads(urllib.request.urlopen(api+repo_name).read())
    repo = Repo(name=parsed_json["full_name"],
                description=parsed_json["description"],
                stars=parsed_json["stargazers_count"],
                forks=parsed_json["forks_count"],
                open_issues=parsed_json["open_issues_count"])
    print("Stars:", repo.stars, "Forks:", repo.forks)
    return repo


def repo_to_line(repo: Repo) -> str:
    line_template = "* [{0}](https://github.com/{0}): {1} ![#stars:{2:d}](https://img.shields.io/github/stars/{0}) ![#forks:{3:d}](https://img.shields.io/github/forks/{0})"
    return line_template.format(repo.name, repo.description, repo.stars, repo.forks)


def parse_repo_block(header: str, repo_names: list) -> tuple:
    if repo_names:
        stars = 0
        forks = 0
        lines = []
        for repo_name in repo_names:
            repo = parse_repo(repo_name)
            lines.append(repo_to_line(repo))
            stars += repo.stars
            forks += repo.forks
            if repo.open_issues > 0:
                print("[Warning!] There is open issues: ", repo)
        return (header + "\n" + "\n".join(lines), stars, forks)
    return ("", 0, 0)


def main(info_path: str, template_path: str, output_path: str = None, write_summary: bool = True):
    with open(info_path) as f:
        info = json.load(f)
    with open(template_path) as f:
        template = f.read()

    bio = info["bio"]
    preprint = parse_repo_block("### Preprint / Technical Reports",
                                info["preprint"])
    pub = parse_repo_block("### Publications", info["pub"])
    edu = parse_repo_block("## Educational Projects", info["edu"])
    misc = parse_repo_block("## Misc.", info["misc"])

    output = template.format(bio=bio,
                             preprint=preprint[0],
                             pub=pub[0],
                             edu=edu[0],
                             misc=misc[0])
    # print(output)

    total_stars = sum([preprint[1], pub[1], edu[1], misc[1]])
    total_forks = sum([preprint[2], pub[2], edu[2], misc[2]])
    print("Total Stars: ", total_stars)
    print("Total Forks: ", total_forks)

    if write_summary:
        output += "\n\nTotal Stars: {0:d}. Total Forks: {1:d}. Updated on {2:s}.".format(
            total_stars, total_forks, datetime.date.today().strftime("%B %d, %Y"))

    if output_path is not None:
        with open(output_path, "w") as f:
            f.write(output)


if __name__ == "__main__":
    main("info.json", "template.md", "README.md", write_summary=True)
