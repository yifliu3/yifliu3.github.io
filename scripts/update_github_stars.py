#!/usr/bin/env python3
"""Generate static GitHub star counts for repository links on the homepage."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import json
import os


ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "index.html"
OUTPUT_PATH = ROOT / "data" / "github-stars.json"


class RepositoryLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.repositories = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return

        values = dict(attrs)
        classes = values.get("class", "").split()
        if "resource-link" not in classes or values.get("data-no-stars") == "true":
            return

        parsed = urlparse(values.get("href", ""))
        if parsed.netloc.lower() != "github.com":
            return

        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            return

        repository = f"{parts[0]}/{parts[1].removesuffix('.git')}"
        if repository not in self.repositories:
            self.repositories.append(repository)


def homepage_repositories():
    parser = RepositoryLinkParser()
    parser.feed(HTML_PATH.read_text(encoding="utf-8"))
    return parser.repositories


def fetch_star_count(repository, token=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "yifliu3.github.io-star-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        f"https://api.github.com/repos/{repository}",
        headers=headers,
    )
    with urlopen(request, timeout=20) as response:
        data = json.load(response)
    return int(data["stargazers_count"])


def main():
    repositories = homepage_repositories()
    if not repositories:
        raise RuntimeError("No GitHub repository links found in index.html")

    token = os.environ.get("GITHUB_TOKEN")
    stars = {
        repository: fetch_star_count(repository, token)
        for repository in repositories
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(stars, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
