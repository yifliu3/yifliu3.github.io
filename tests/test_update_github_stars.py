from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update_github_stars.py"
SPEC = importlib.util.spec_from_file_location("update_github_stars", SCRIPT)
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)


class StarUpdaterTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.html = root / "index.html"
        self.output = root / "data" / "github-stars.json"
        self.html.write_text(
            '<a class="resource-link" href="https://github.com/team/project">Code</a>'
            '<a class="resource-link" href="https://github.com/team/other">Code</a>',
            encoding="utf-8",
        )
        paths = patch.multiple(updater, HTML_PATH=self.html, OUTPUT_PATH=self.output)
        paths.start()
        self.addCleanup(paths.stop)

    def test_only_enabled_repository_links_are_collected_once(self):
        parser = updater.RepositoryLinkParser()
        parser.feed(
            '<a class="resource-link" href="https://github.com/team/project.git">Code</a>'
            '<a class="resource-link" href="https://github.com/team/project/tree/main">Code</a>'
            '<a class="resource-link" href="https://github.com/team/hidden" data-no-stars="true">Code</a>'
            '<a href="https://github.com/team/profile">Profile</a>'
            '<a class="resource-link" href="https://example.com/team/project">Page</a>'
        )
        self.assertEqual(parser.repositories, ["team/project"])

    def test_success_replaces_old_repositories_and_records_refresh_time(self):
        self.output.parent.mkdir()
        self.output.write_text('{"team/removed": 50}', encoding="utf-8")
        before = datetime.now(timezone.utc).replace(microsecond=0)
        with patch.object(updater, "fetch_star_count", side_effect=[0, 560]):
            updater.main()
        data = json.loads(self.output.read_text(encoding="utf-8"))
        refreshed = datetime.fromisoformat(data.pop("_updated_at"))
        self.assertEqual(data, {"team/project": 0, "team/other": 560})
        self.assertGreaterEqual(refreshed, before)
        self.assertLessEqual(refreshed, datetime.now(timezone.utc))

    def test_partial_api_failure_does_not_overwrite_last_good_snapshot(self):
        self.output.parent.mkdir()
        previous = '{"team/project": 10, "team/other": 20}\n'
        self.output.write_text(previous, encoding="utf-8")
        failure = HTTPError("https://api.github.com", 403, "rate limit", {}, None)
        with patch.object(updater, "fetch_star_count", side_effect=[11, failure]):
            with self.assertRaises(HTTPError):
                updater.main()
        self.assertEqual(self.output.read_text(encoding="utf-8"), previous)

    def test_github_response_must_contain_nonnegative_integer_count(self):
        for invalid in (-1, True, "560", 1.5, None):
            with self.subTest(count=invalid):
                response = io.BytesIO(json.dumps({"stargazers_count": invalid}).encode())
                with patch.object(updater, "urlopen", return_value=response):
                    with self.assertRaises(ValueError):
                        updater.fetch_star_count("team/project")
        response = io.BytesIO(b'{"stargazers_count": 0}')
        with patch.object(updater, "urlopen", return_value=response):
            self.assertEqual(updater.fetch_star_count("team/project"), 0)


if __name__ == "__main__":
    unittest.main()
