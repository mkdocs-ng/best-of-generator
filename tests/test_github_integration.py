from datetime import datetime

import pytest

from best_of.integrations import github_integration


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload


SINCE = datetime(2026, 8, 1)


def test_null_repository_is_a_failure(monkeypatch):
    # GraphQL answers 200 with errors and a null repository when the query fails.
    response = FakeResponse(
        payload={"data": {"repository": None}, "errors": [{"message": "boom"}]}
    )
    monkeypatch.setattr(github_integration.requests, "post", lambda *a, **k: response)
    assert (
        github_integration.request_metadata_from_github_api("t", "a/b", SINCE) is None
    )


def test_graphql_rate_limit_raises(monkeypatch):
    response = FakeResponse(
        payload={"errors": [{"type": "RATE_LIMITED", "message": "slow down"}]},
        headers={"retry-after": "7"},
    )
    monkeypatch.setattr(github_integration.requests, "post", lambda *a, **k: response)
    with pytest.raises(github_integration.GitHubRateLimitError) as info:
        github_integration.request_metadata_from_github_api("t", "a/b", SINCE)
    assert info.value.retry_after == 7


def test_timestamp_has_explicit_utc_offset(monkeypatch):
    seen = {}

    def fake_post(url, json, headers, timeout):
        seen.update(json["variables"])
        return FakeResponse(payload={"data": {"repository": {"name": "b"}}})

    monkeypatch.setattr(github_integration.requests, "post", fake_post)
    info = github_integration.request_metadata_from_github_api("t", "a/b", SINCE)
    assert info.name == "b"
    assert seen["since_recent_activity"] == "2026-08-01T00:00:00Z"


def test_rest_fallback_fills_project_info(monkeypatch):
    monkeypatch.setenv("GITHUB_API_KEY", "t")
    monkeypatch.setattr(
        github_integration.requests,
        "post",
        lambda *a, **k: FakeResponse(payload={"data": {"repository": None}}),
    )

    def fake_get(url, headers=None, timeout=None):
        if url == "https://api.github.com/repos/a/b":
            return FakeResponse(
                payload={
                    "name": "b",
                    "full_name": "a/b",
                    "description": "A plugin for things.",
                    "html_url": "https://github.com/a/b",
                    "created_at": "2020-01-01T00:00:00Z",
                    "pushed_at": "2026-10-01T00:00:00Z",
                    "license": {"spdx_id": "MIT"},
                    "stargazers_count": 120,
                    "forks_count": 12,
                    "subscribers_count": 3,
                    "default_branch": "main",
                }
            )
        if "/commits?" in url and "since=" in url:
            return FakeResponse(payload=[{}], headers={})
        if "/commits?" in url:
            link = '<https://api.github.com/repositories/1/commits?per_page=1&page=345>; rel="last"'
            return FakeResponse(payload=[{}], headers={"Link": link})
        if url.endswith("/releases?per_page=100"):
            return FakeResponse(
                payload=[
                    {
                        "published_at": "2026-09-01T00:00:00Z",
                        "tag_name": "v1.2.3",
                        "draft": False,
                        "prerelease": False,
                        "assets": [],
                    }
                ]
            )
        # contributors and dependents pages
        return FakeResponse(status_code=404)

    monkeypatch.setattr(github_integration.requests, "get", fake_get)

    project = github_integration.Dict(github_id="a/b", name="b")
    github_integration.update_via_github_api(project)

    assert project.github_url == "https://github.com/a/b"
    assert project.homepage == "https://github.com/a/b"
    assert project.star_count == 120
    assert project.fork_count == 12
    assert project.license == "MIT"
    assert project.commit_count == 345
    assert project.recent_commit_count == 1
    assert project.latest_stable_release_number == "1.2.3"
    assert project.release_count == 1


def test_graphql_star_count(monkeypatch):
    monkeypatch.setenv("GITHUB_API_KEY", "t")
    monkeypatch.setattr(
        github_integration.requests,
        "post",
        lambda *a, **k: FakeResponse(
            payload={
                "data": {
                    "repository": {
                        "url": "https://github.com/a/b",
                        "stargazerCount": 42,
                    }
                }
            }
        ),
    )
    monkeypatch.setattr(
        github_integration.requests,
        "get",
        lambda *a, **k: FakeResponse(status_code=404),
    )
    project = github_integration.Dict(github_id="a/b", name="b")
    github_integration.update_via_github_api(project)
    assert project.star_count == 42
    assert project.homepage == "https://github.com/a/b"
