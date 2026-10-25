#!/usr/bin/env python3
"""Client for the Knowledge Engine research service used by the deep-research skill.

The script is deliberately standard-library only so the skill can be copied into
any repository and run with Python 3.11+ without installing the project. It
reads ``RESEARCH_BASE_URL`` and ``RESEARCH_TOKEN`` from the environment or the
nearest ``.env`` file, submits a research job, polls it, saves the rendered
article and source records, and verifies the citation structure.

Commands:
    health   Probe the service and readiness checks.
    wiki     Query the compiled wiki before starting a live run.
    page     Read one compiled wiki page.
    status   Read one job record.
    run      Submit, poll, optionally save, and verify.
    save     Recover a submitted job by task id.
    verify   Check a saved note without touching the network.

Exit codes:
    0 success, 2 usage/config, 3 API/HTTP, 4 verification, 5 timeout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

VERSION = "1.0"
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_API = 3
EXIT_VERIFY = 4
EXIT_TIMEOUT = 5

DEFAULT_POLL_SECONDS = 5.0
DEFAULT_WAIT_SECONDS = 960.0
DEFAULT_HTTP_TIMEOUT = 120.0
MAX_RETRY_WAIT = 60.0
RETRY_ATTEMPTS = 3

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
THREAD_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MARKER_RE = re.compile(r"\[\^([^\]\n]+)\]")
DEFINITION_RE = re.compile(r"(?m)^\[\^([^\]\n]+)\]:")
HEADING_RE = re.compile(r"(?m)^#{1,6}\s+.*$")
UNCERTAINTY_RE = re.compile(r"(?im)^#{1,6}\s+.*(limitation|uncertaint|caveat|open question).*$")
USER_AGENT = "knowledge-engine-deep-research/1.0"


class SkillError(Exception):
    """Base error carrying a stable code and process exit code."""

    code = "error"
    exit_code = 1

    def __init__(self, message: str, *, details: Any = None) -> None:
        """Initialize the error.

        Args:
            message: Human-readable, already-redacted message.
            details: Optional machine-readable context.
        """
        super().__init__(message)
        self.message = message
        self.details = details


class UsageError(SkillError):
    """Invalid arguments or missing configuration."""

    code = "usage"
    exit_code = EXIT_USAGE


class ApiError(SkillError):
    """The service returned an error or could not be reached."""

    code = "api"
    exit_code = EXIT_API


class VerificationError(SkillError):
    """A saved note failed structural or citation verification."""

    code = "verification"
    exit_code = EXIT_VERIFY


class WaitTimeout(SkillError):
    """A submitted job did not reach a terminal state in time."""

    code = "timeout"
    exit_code = EXIT_TIMEOUT


@dataclass(frozen=True)
class Config:
    """Resolved service configuration.

    Attributes:
        base_url: Normalized service URL without a trailing slash.
        token: Bearer token, excluded from repr on purpose.
        env_file: The ``.env`` file that was read, when one was used.
    """

    base_url: str
    token: str | None = field(repr=False)
    env_file: Path | None = None
    project_root: Path = field(default_factory=Path.cwd)


@dataclass(frozen=True)
class HttpResponse:
    """Minimal HTTP response used by the pluggable transport.

    Attributes:
        status: HTTP status code.
        headers: Response headers.
        body: Raw response body.
    """

    status: int
    headers: Mapping[str, str]
    body: bytes


@dataclass(frozen=True)
class SaveReport:
    """Result of saving and verifying one completed run.

    Attributes:
        job: The completed job record.
        directory: Output directory.
        article: Path to ``article.md``.
        sources_file: Path to ``sources.json``.
        run_file: Path to ``run.json``.
        verification: Verification report.
    """

    job: dict[str, Any]
    directory: Path
    article: Path
    sources_file: Path
    run_file: Path
    verification: VerificationReport

    def to_dict(self) -> dict[str, Any]:
        """Render the report as JSON-safe data.

        Returns:
            dict[str, Any]: Report fields plus verification.
        """
        return {
            "ok": self.verification.ok,
            "task_id": self.job.get("task_id"),
            "thread_id": self.job.get("thread_id"),
            "query": self.job.get("query"),
            "workflow": self.job.get("workflow"),
            "status": self.job.get("status"),
            "sources_count": self.verification.sources,
            "output_dir": str(self.directory),
            "article": str(self.article),
            "sources": str(self.sources_file),
            "run": str(self.run_file),
            "verification": self.verification.to_dict(),
        }


@dataclass(frozen=True)
class VerificationReport:
    """Structural verification of one saved note.

    Attributes:
        ok: Hard checks passed.
        strict_ok: Hard checks and advisory checks passed.
        sources: Source-record count.
        markers: Citation-marker count in the article.
        definitions: Footnote-definition count in the article.
        missing_definitions: Markers without a definition.
        unknown_source_ids: Citations not present in ``sources.json``.
        unused_definitions: Definitions not referenced by a marker.
        uncited_paragraphs: Prose paragraphs of 25+ words without a citation.
        missing_uncertainty_section: No limitations/uncertainty heading found.
        warnings: Advisory findings.
        errors: Hard findings.
    """

    ok: bool
    strict_ok: bool
    sources: int
    markers: int
    definitions: int
    missing_definitions: list[str]
    unknown_source_ids: list[str]
    unused_definitions: list[str]
    uncited_paragraphs: list[dict[str, Any]]
    missing_uncertainty_section: bool
    warnings: list[str]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Render the report as JSON-safe data.

        Returns:
            dict[str, Any]: Report fields.
        """
        return {
            "ok": self.ok,
            "strict_ok": self.strict_ok,
            "sources": self.sources,
            "markers": self.markers,
            "definitions": self.definitions,
            "missing_definitions": list(self.missing_definitions),
            "unknown_source_ids": list(self.unknown_source_ids),
            "unused_definitions": list(self.unused_definitions),
            "uncited_paragraphs": list(self.uncited_paragraphs),
            "missing_uncertainty_section": self.missing_uncertainty_section,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


Transport = Callable[[str, str, Mapping[str, str], bytes | None, float], HttpResponse]
Sleeper = Callable[[float], None]


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a small dotenv file without executing or expanding anything.

    Args:
        path: File to read.

    Returns:
        dict[str, str]: Parsed keys and values.

    Raises:
        UsageError: When the file cannot be read.
    """
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise UsageError(f"cannot read env file {path}: {exc.strerror}") from None
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def discover_env_file(start: Path) -> Path | None:
    """Find the nearest ``.env`` walking up from ``start``.

    Args:
        start: Directory to start from.

    Returns:
        Path | None: The first readable-looking ``.env``, or None.
    """
    current = start.resolve()
    for directory in (current, *current.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
    return None


def normalize_base_url(value: str) -> str:
    """Validate and normalize the service base URL.

    Args:
        value: Raw URL.

    Returns:
        str: URL without a trailing slash.

    Raises:
        UsageError: When the URL is missing, non-HTTP, or contains credentials.
    """
    text = value.strip()
    if not text:
        raise UsageError("RESEARCH_BASE_URL is required (for example http://127.0.0.1:8000)")
    parsed = urllib.parse.urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise UsageError("RESEARCH_BASE_URL must be an absolute http(s) URL")
    if parsed.username or parsed.password:
        raise UsageError("RESEARCH_BASE_URL must not contain credentials; use RESEARCH_TOKEN")
    if parsed.query or parsed.fragment:
        raise UsageError("RESEARCH_BASE_URL must not contain a query or fragment")
    return text.rstrip("/")


def is_loopback(base_url: str) -> bool:
    """Return True when the URL host is a loopback interface.

    Args:
        base_url: Normalized service URL.

    Returns:
        bool: Whether the host is localhost/127.0.0.1/::1.
    """
    host = urllib.parse.urlparse(base_url).hostname or ""
    return host.lower() in LOOPBACK_HOSTS


def resolve_project_root(args: argparse.Namespace) -> Path:
    """Resolve the project root used for the default ``docs/research`` output.

    Args:
        args: Parsed command arguments.

    Returns:
        Path: Directory containing the explicit or discovered ``.env``, or cwd.
    """
    if args.env_file:
        return Path(args.env_file).expanduser().resolve().parent
    env_file = discover_env_file(Path.cwd())
    return env_file.parent if env_file is not None else Path.cwd()


def load_config(args: argparse.Namespace, *, require_token: bool) -> Config:
    """Resolve configuration from CLI flags, environment, and ``.env``.

    Args:
        args: Parsed command arguments.
        require_token: Reject a missing token for data routes.

    Returns:
        Config: Resolved configuration.

    Raises:
        UsageError: When required configuration is missing or unsafe.
    """
    project_root = resolve_project_root(args)
    env_file = Path(args.env_file).expanduser() if args.env_file else discover_env_file(Path.cwd())
    file_values = parse_env_file(env_file) if env_file is not None else {}
    raw_base = args.base_url or os.environ.get("RESEARCH_BASE_URL") or file_values.get("RESEARCH_BASE_URL")
    raw_token = os.environ.get("RESEARCH_TOKEN") or file_values.get("RESEARCH_TOKEN")
    base_url = normalize_base_url(raw_base or "")
    if args.anonymous:
        if not is_loopback(base_url):
            raise UsageError("--anonymous is allowed only for loopback URLs; use a token otherwise")
        token = None
    else:
        token = raw_token.strip() if raw_token else None
    if require_token and not token and not args.anonymous:
        raise UsageError("RESEARCH_TOKEN is required for data routes; set it in the environment or .env")
    return Config(
        base_url=base_url,
        token=token,
        env_file=env_file,
        project_root=project_root,
    )


def safe_url(url: str) -> str:
    """Strip query and fragment before putting a URL in an error message.

    Args:
        url: Full request URL.

    Returns:
        str: URL without query or fragment.
    """
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def redact(text: str, token: str | None) -> str:
    """Remove bearer credentials from a message.

    Args:
        text: Message that may contain a token.
        token: Token to redact, when present.

    Returns:
        str: Redacted message.
    """
    if not token:
        return text
    redacted = text.replace(f"Bearer {token}", "Bearer ***")
    if len(token) >= 8:
        redacted = redacted.replace(token, "***")
    return redacted


def _extract_detail(body: bytes) -> str:
    """Extract a short error detail from a response body.

    Args:
        body: Raw response body.

    Returns:
        str: Detail text, truncated to 1000 characters.
    """
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        return ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text[:1000]
    detail = payload.get("detail") if isinstance(payload, dict) else payload
    if isinstance(detail, list):
        return "; ".join(str(item) for item in detail)[:1000]
    return str(detail)[:1000]


def _parse_retry_after(headers: Mapping[str, str]) -> float | None:
    """Read a Retry-After header as seconds.

    Args:
        headers: Response headers.

    Returns:
        float | None: Delay in seconds, or None when absent/unsupported.
    """
    value = next((item for key, item in headers.items() if key.lower() == "retry-after"), None)
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def default_transport(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: bytes | None,
    timeout: float,
) -> HttpResponse:
    """Perform one HTTP request using urllib.

    Args:
        method: HTTP method.
        url: Absolute URL.
        headers: Request headers.
        body: Optional request body.
        timeout: Per-request timeout in seconds.

    Returns:
        HttpResponse: Status, headers, and body.

    Raises:
        ApiError: When the request cannot be made.
    """
    request = urllib.request.Request(url, data=body, headers=dict(headers), method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return HttpResponse(response.status, dict(response.headers), response.read())
    except urllib.error.HTTPError as exc:
        return HttpResponse(exc.code, dict(exc.headers or {}), exc.read())
    except urllib.error.URLError as exc:
        raise ApiError(f"network error contacting {safe_url(url)}: {exc.reason}") from None
    except (TimeoutError, OSError) as exc:
        raise ApiError(f"network error contacting {safe_url(url)}: {exc}") from None


class ApiClient:
    """Thin, retrying client for the Knowledge Engine HTTP surface."""

    def __init__(
        self,
        config: Config,
        *,
        transport: Transport = default_transport,
        sleeper: Sleeper = time.sleep,
        http_timeout: float = DEFAULT_HTTP_TIMEOUT,
        max_retry_wait: float = MAX_RETRY_WAIT,
    ) -> None:
        """Initialize the client.

        Args:
            config: Resolved configuration.
            transport: Request function, injectable for tests.
            sleeper: Sleep function, injectable for tests.
            http_timeout: Per-request timeout.
            max_retry_wait: Longest Retry-After the client will honor.
        """
        self.config = config
        self.transport = transport
        self.sleeper = sleeper
        self.http_timeout = http_timeout
        self.max_retry_wait = max_retry_wait

    def _error_for(self, response: HttpResponse, method: str) -> ApiError:
        """Build a redacted, actionable error from an HTTP response.

        Args:
            response: Error response.
            method: Request method.

        Returns:
            ApiError: The error to raise.
        """
        detail = _extract_detail(response.body)
        suffix = f": {detail}" if detail else ""
        if response.status == 401:
            message = "401 unauthorized: RESEARCH_TOKEN is missing, invalid, or lacks write access"
        elif response.status == 403:
            message = "403 forbidden: this token cannot perform that operation"
        elif response.status == 404:
            message = f"404 not found{suffix}"
        elif response.status == 409:
            message = f"409 conflict: the job is not ready yet{suffix}"
        elif response.status == 422:
            message = f"422 validation failed{suffix}"
        elif response.status == 429:
            message = f"429 rate limited{suffix}"
        elif response.status == 503:
            message = (
                "503 service unavailable: the service may have no auth configured "
                "(do not use anonymous in production) or may still be starting"
            )
        elif response.status >= 500:
            message = f"{response.status} service error{suffix}"
            if method == "POST":
                message += (
                    "; the request may have been accepted. Do not resubmit blindly; "
                    "ask the operator to check the queue"
                )
        else:
            message = f"HTTP {response.status}{suffix}"
        retry_after = _parse_retry_after(response.headers)
        if retry_after is not None:
            message += f" (Retry-After: {retry_after:.0f}s)"
        return ApiError(
            redact(message, self.config.token),
            details={"status": response.status, "detail": redact(detail, self.config.token)},
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        auth: bool = True,
        retry: bool = True,
    ) -> HttpResponse:
        """Send a request, retrying only what is safe to retry.

        Args:
            method: HTTP method.
            path: Path beginning with ``/``.
            body: Optional JSON body.
            auth: Attach the bearer token.
            retry: Allow safe retries.

        Returns:
            HttpResponse: Successful response.

        Raises:
            ApiError: When the final response is an error.
        """
        url = f"{self.config.base_url}{path}"
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/markdown;q=0.9, */*;q=0.8",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        if auth and self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"
        attempts = RETRY_ATTEMPTS if retry else 1
        for attempt in range(1, attempts + 1):
            response = self.transport(method, url, headers, body, self.http_timeout)
            if response.status < 400:
                return response
            retryable = response.status in {429, 502, 503, 504}
            if method == "POST":
                retryable = response.status == 429
            if not retryable or attempt >= attempts:
                raise self._error_for(response, method)
            delay = _parse_retry_after(response.headers)
            if delay is None:
                delay = float(2 ** (attempt - 1))
            if delay > self.max_retry_wait:
                raise ApiError(
                    f"HTTP {response.status} asks for a {delay:.0f}s wait, above the "
                    f"--max-retry-wait limit; stop and retry later",
                    details={"status": response.status, "retry_after": delay},
                )
            self.sleeper(delay)
        raise ApiError("request attempts exhausted")

    def json_request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        auth: bool = True,
        retry: bool = True,
    ) -> Any:
        """Send a request and decode a JSON response.

        Args:
            method: HTTP method.
            path: Request path.
            body: Optional JSON object.
            auth: Attach the bearer token.
            retry: Allow safe retries.

        Returns:
            Any: Decoded JSON value.

        Raises:
            ApiError: When the response is not valid JSON.
        """
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        response = self._request(method, path, body=encoded, auth=auth, retry=retry)
        try:
            return json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(f"service returned invalid JSON: {exc}") from None

    def text_request(self, path: str, *, auth: bool = True) -> str:
        """Send a GET request and decode a Markdown/text response.

        Args:
            path: Request path.
            auth: Attach the bearer token.

        Returns:
            str: Decoded response text.
        """
        response = self._request("GET", path, auth=auth)
        return response.body.decode("utf-8", errors="replace")

    def health(self) -> dict[str, Any]:
        """Read the unauthenticated liveness document.

        Returns:
            dict[str, Any]: Health payload.

        Raises:
            ApiError: When the payload is not an object.
        """
        payload = self.json_request("GET", "/health", auth=False)
        if not isinstance(payload, dict):
            raise ApiError("service returned an invalid health payload")
        return payload

    def readiness(self) -> dict[str, Any]:
        """Read the unauthenticated readiness document.

        Returns:
            dict[str, Any]: Readiness payload.

        Raises:
            ApiError: When the payload is not an object.
        """
        payload = self.json_request("GET", "/readiness", auth=False)
        if not isinstance(payload, dict):
            raise ApiError("service returned an invalid readiness payload")
        return payload

    def submit(
        self,
        query: str,
        workflow: str,
        thread_id: str,
        settings: dict[str, Any],
    ) -> str:
        """Submit a research job.

        Args:
            query: Research question.
            workflow: Workflow name.
            thread_id: Caller-supplied thread id.
            settings: Per-run overrides.

        Returns:
            str: Server task id.

        Raises:
            ApiError: When the service does not return a task id.
        """
        body: dict[str, Any] = {"query": query, "workflow": workflow, "thread_id": thread_id}
        if settings:
            body["settings"] = settings
        payload = self.json_request("POST", "/research", body=body)
        if not isinstance(payload, dict) or not isinstance(payload.get("task_id"), str):
            raise ApiError("service did not return a task_id")
        return payload["task_id"]

    def job(self, task_id: str) -> dict[str, Any]:
        """Read a job record.

        Args:
            task_id: Server task id.

        Returns:
            dict[str, Any]: Job record.

        Raises:
            ApiError: When the payload is not an object.
        """
        payload = self.json_request("GET", f"/result/{urllib.parse.quote(task_id, safe='')}")
        if not isinstance(payload, dict):
            raise ApiError("service returned an invalid job record")
        return payload

    def artifact(self, task_id: str) -> dict[str, Any]:
        """Read the rendered artifact and its embedded sources as JSON.

        Args:
            task_id: Server task id.

        Returns:
            dict[str, Any]: Artifact payload.

        Raises:
            ApiError: When the payload is not an object.
        """
        quoted = urllib.parse.quote(task_id, safe="")
        payload = self.json_request("GET", f"/result/{quoted}/artifact?format=json")
        if not isinstance(payload, dict):
            raise ApiError("service returned an invalid artifact payload")
        return payload

    def sources(self, task_id: str) -> dict[str, Any]:
        """Read the persisted source records.

        Args:
            task_id: Server task id.

        Returns:
            dict[str, Any]: Sources payload.

        Raises:
            ApiError: When the payload is not an object.
        """
        quoted = urllib.parse.quote(task_id, safe="")
        payload = self.json_request("GET", f"/result/{quoted}/sources")
        if not isinstance(payload, dict):
            raise ApiError("service returned an invalid sources payload")
        return payload

    def wiki_query(self, query: str, limit: int) -> dict[str, Any]:
        """Query the compiled wiki.

        Args:
            query: Query text.
            limit: Maximum hits.

        Returns:
            dict[str, Any]: Query payload.

        Raises:
            ApiError: When the payload is not an object.
        """
        params = urllib.parse.urlencode({"q": query, "limit": limit})
        payload = self.json_request("GET", f"/wiki/query?{params}")
        if not isinstance(payload, dict):
            raise ApiError("service returned an invalid wiki payload")
        return payload

    def wiki_page(self, slug: str) -> str:
        """Read one compiled wiki page.

        Args:
            slug: Kebab-case page slug.

        Returns:
            str: Markdown page.
        """
        return self.text_request(f"/wiki/page/{urllib.parse.quote(slug, safe='-')}")


def generate_thread_id() -> str:
    """Generate a traceable, service-safe thread id.

    Returns:
        str: Thread id matching the service's allowed pattern.
    """
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"dr-{stamp}-{os.urandom(4).hex()}"


def validate_thread_id(value: str) -> str:
    """Validate a caller-supplied thread id.

    Args:
        value: Thread id.

    Returns:
        str: The same id.

    Raises:
        UsageError: When the id is unsafe.
    """
    if not THREAD_ID_RE.fullmatch(value):
        raise UsageError("thread id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    return value


def normalize_query(value: str, *, max_length: int = 4000) -> str:
    """Trim and validate a research query.

    Args:
        value: Raw query.
        max_length: Maximum accepted length.

    Returns:
        str: Trimmed query.

    Raises:
        UsageError: When the query is blank or too long.
    """
    text = value.strip()
    if not text:
        raise UsageError("query must not be blank")
    if len(text) > max_length:
        raise UsageError(f"query is too long ({len(text)} > {max_length})")
    return text


def build_settings(args: argparse.Namespace) -> dict[str, Any]:
    """Build and validate the service's per-run settings.

    Args:
        args: Parsed command arguments.

    Returns:
        dict[str, Any]: Settings payload, possibly empty.

    Raises:
        UsageError: When a value is outside the service contract or a deep run
            is not explicitly approved.
    """
    settings: dict[str, Any] = {}
    if args.max_depth is not None:
        if not 0 <= args.max_depth <= 3:
            raise UsageError("--max-depth must be between 0 and 3")
        settings["max_depth"] = args.max_depth
    if args.max_subqueries is not None:
        if not 1 <= args.max_subqueries <= 7:
            raise UsageError("--max-subqueries must be between 1 and 7")
        settings["max_subqueries"] = args.max_subqueries
    if args.max_iterations is not None:
        if not 0 <= args.max_iterations <= 2:
            raise UsageError("--max-iterations must be between 0 and 2")
        settings["max_iterations"] = args.max_iterations
    if args.max_wiki_pages is not None:
        if not 1 <= args.max_wiki_pages <= 20:
            raise UsageError("--max-wiki-pages must be between 1 and 20")
        settings["max_wiki_pages"] = args.max_wiki_pages
    if args.thesis is not None:
        thesis = args.thesis.strip()
        if thesis:
            if len(thesis) > 300:
                raise UsageError("--thesis must be at most 300 characters")
            settings["thesis"] = thesis
    if args.wiki_extract:
        settings["wiki_extract"] = True
    if args.wiki_save_answers:
        settings["wiki_save_answers"] = True
    if args.approve_deep and args.workflow != "deep":
        raise UsageError("--approve-deep is valid only with --workflow deep")
    if args.workflow == "deep":
        if not args.approve_deep:
            raise UsageError(
                "deep research requires explicit approval; pass --approve-deep "
                "and caps (for example --max-depth 2 --max-subqueries 5)"
            )
        settings.setdefault("max_depth", 2)
        settings.setdefault("max_subqueries", 5)
    return settings


def slugify(value: str, *, max_length: int = 60) -> str:
    """Convert a query into a readable directory slug.

    Args:
        value: Query text.
        max_length: Maximum slug length.

    Returns:
        str: Lowercase ASCII slug, or ``research`` when empty.
    """
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    if len(normalized) > max_length:
        cut = normalized[:max_length]
        if "-" in cut:
            cut = cut.rsplit("-", 1)[0]
        normalized = cut.strip("-")
    return normalized or "research"


def default_output_dir(
    query: str,
    *,
    today: date | None = None,
    project_root: Path | None = None,
) -> Path:
    """Return the default saved-note directory for a query.

    Args:
        query: Research question.
        today: Date override, useful in tests.
        project_root: Repository root containing ``.env``; defaults to cwd.

    Returns:
        Path: ``<project_root>/docs/research/<date>-<slug>``.
    """
    day = (today or date.today()).isoformat()
    root = project_root if project_root is not None else Path.cwd()
    return root / "docs" / "research" / f"{day}-{slugify(query)}"


def output_dir_for(query: str, out: str | None, *, project_root: Path) -> Path:
    """Resolve an explicit output directory or the default one.

    Args:
        query: Research question.
        out: Optional user-supplied directory, relative to cwd.
        project_root: Repository root for the default directory.

    Returns:
        Path: Output directory.
    """
    return Path(out).expanduser() if out else default_output_dir(query, project_root=project_root)


def check_output_dir(path: Path, force: bool) -> None:
    """Reject an existing non-empty output directory unless forced.

    Args:
        path: Intended output directory.
        force: Allow overwriting.

    Raises:
        UsageError: When the path is a file or a non-empty directory.
    """
    if not path.exists():
        return
    if not path.is_dir():
        raise UsageError(f"output path is not a directory: {path}")
    if not force and any(path.iterdir()):
        raise UsageError(
            f"output directory is not empty: {path}; pass --out to choose another "
            "directory or --force only with explicit approval"
        )


def prepare_output_dir(path: Path, force: bool) -> None:
    """Create the output directory and re-check it for races.

    Args:
        path: Intended output directory.
        force: Allow overwriting.

    Raises:
        UsageError: When a conflicting directory appears.
    """
    path.mkdir(parents=True, exist_ok=True)
    if not force and any(path.iterdir()):
        raise UsageError(f"output directory is not empty: {path}")


def write_text_atomic(path: Path, text: str) -> None:
    """Write UTF-8 text through a temporary sibling file.

    Args:
        path: Destination file.
        text: Content to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def write_json(path: Path, payload: Any) -> None:
    """Write a pretty JSON document atomically.

    Args:
        path: Destination file.
        payload: JSON-safe data.
    """
    write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def strip_frontmatter(article: str) -> str:
    """Remove YAML frontmatter from a rendered article.

    Args:
        article: Full Markdown.

    Returns:
        str: Body without leading frontmatter.
    """
    match = re.match(r"\A---\r?\n.*?\r?\n---\r?\n", article, re.DOTALL)
    return article[match.end() :] if match else article


def _source_records(payload: Any) -> list[dict[str, Any]]:
    """Extract a source list from a service payload.

    Args:
        payload: ``/sources`` or artifact JSON.

    Returns:
        list[dict[str, Any]]: Source records.

    Raises:
        ApiError: When the payload has no usable source list.
    """
    if isinstance(payload, dict):
        payload = payload.get("sources")
    if not isinstance(payload, list):
        raise ApiError("service returned an invalid source list")
    records = [item for item in payload if isinstance(item, dict)]
    if len(records) != len(payload):
        raise ApiError("service returned a source list with non-object entries")
    return records


def _known_source_ids(sources: list[dict[str, Any]]) -> set[str]:
    """Collect citation identifiers from source records.

    Args:
        sources: Source records.

    Returns:
        set[str]: Canonical ids and DOIs.
    """
    known: set[str] = set()
    for source in sources:
        source_id = source.get("id")
        if isinstance(source_id, str) and source_id.strip():
            known.add(source_id.strip())
        doi = source.get("doi")
        if isinstance(doi, str) and doi.strip():
            known.add(doi.strip())
    return known


def _uncited_paragraphs(body: str) -> list[dict[str, Any]]:
    """Find prose paragraphs without a citation marker.

    Args:
        body: Article body without frontmatter.

    Returns:
        list[dict[str, Any]]: Word count and preview for each finding.
    """
    findings: list[dict[str, Any]] = []
    current_heading = ""
    for block in re.split(r"\n\s*\n", body):
        text = block.strip()
        if not text:
            continue
        if text.startswith("#"):
            current_heading = text.lstrip("#").strip().lower()
            continue
        if any(
            word in current_heading
            for word in (
                "limitation",
                "uncertain",
                "scope",
                "method",
                "reference",
                "source",
                "bibliograph",
                "appendix",
            )
        ):
            continue
        if text.startswith(("```", "|", "[^")):
            continue
        words = len(re.findall(r"\b[\w'-]+\b", text))
        if words >= 25 and not MARKER_RE.search(text):
            findings.append({"words": words, "preview": re.sub(r"\s+", " ", text)[:120]})
    return findings


def verify_path(path: Path, *, strict: bool) -> VerificationReport:
    """Verify a saved note without using the network.

    Args:
        path: Output directory.
        strict: Treat advisory findings as failures.

    Returns:
        VerificationReport: Hard and advisory findings.
    """
    directory = Path(path).expanduser()
    errors: list[str] = []
    warnings: list[str] = []
    article_path = directory / "article.md"
    sources_path = directory / "sources.json"
    run_path = directory / "run.json"

    article = article_path.read_text(encoding="utf-8") if article_path.is_file() else ""
    if not article.strip():
        errors.append(f"{article_path} is missing or empty")

    sources: list[dict[str, Any]] = []
    if not sources_path.is_file():
        errors.append(f"{sources_path} is missing")
    else:
        try:
            raw_sources = json.loads(sources_path.read_text(encoding="utf-8"))
            sources = _source_records(raw_sources)
        except (OSError, json.JSONDecodeError, ApiError) as exc:
            errors.append(f"{sources_path} is invalid: {exc}")
    if not sources:
        errors.append("no source records")

    bad_sources = [
        index
        for index, source in enumerate(sources)
        if not isinstance(source.get("id"), str)
        or not source["id"].strip()
        or not isinstance(source.get("title"), str)
        or not source["title"].strip()
    ]
    if bad_sources:
        errors.append(f"source records missing id/title at indexes {bad_sources}")

    if run_path.is_file():
        try:
            run = json.loads(run_path.read_text(encoding="utf-8"))
            if isinstance(run, dict) and run.get("status") not in {None, "done"}:
                errors.append(f"run.json status is {run.get('status')!r}, not 'done'")
            if isinstance(run, dict) and isinstance(run.get("sources_count"), int):
                if run["sources_count"] != len(sources):
                    warnings.append(
                        f"run.json sources_count={run['sources_count']} but sources.json has {len(sources)}"
                    )
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{run_path} is invalid: {exc}")
    else:
        warnings.append(f"{run_path} is missing; provenance is incomplete")

    body = strip_frontmatter(article)
    definitions = set(DEFINITION_RE.findall(body))
    body_for_markers = re.sub(
        r"(?m)^\[\^[^\]\n]+\]:[^\n]*(?:\n[ \t]+\S[^\n]*)*\n?",
        "",
        body,
    )
    markers = set(MARKER_RE.findall(body_for_markers))
    known = _known_source_ids(sources)
    missing_definitions = sorted(markers - definitions)
    unknown = sorted({item for item in markers | definitions if item not in known})
    unused = sorted(definitions - markers)
    uncited = _uncited_paragraphs(body)
    missing_uncertainty = UNCERTAINTY_RE.search(body) is None

    if not markers:
        errors.append("article has no citation markers")
    if not definitions:
        errors.append("article has no footnote definitions")
    if missing_definitions:
        errors.append(f"citation markers without definitions: {missing_definitions}")
    if unknown:
        errors.append(f"citations not present in sources.json: {unknown}")
    if unused:
        warnings.append(f"footnote definitions not referenced in the body: {unused}")
    if uncited:
        warnings.append(f"{len(uncited)} prose paragraph(s) of 25+ words have no citation")
    if missing_uncertainty:
        warnings.append("no limitations/uncertainty section found")

    ok = not errors
    strict_ok = ok and not warnings
    return VerificationReport(
        ok=ok,
        strict_ok=strict_ok,
        sources=len(sources),
        markers=len(markers),
        definitions=len(definitions),
        missing_definitions=missing_definitions,
        unknown_source_ids=unknown,
        unused_definitions=unused,
        uncited_paragraphs=uncited,
        missing_uncertainty_section=missing_uncertainty,
        warnings=warnings,
        errors=errors,
    )


def _job_source_count(job: Mapping[str, Any]) -> int:
    """Read the source count from a job's result summary.

    Args:
        job: Job record.

    Returns:
        int: Source count, or 0 when the summary is absent.
    """
    result = job.get("result")
    if not isinstance(result, dict):
        return 0
    sources = result.get("sources")
    if isinstance(sources, int):
        return sources
    if isinstance(sources, list):
        return len(sources)
    return 0


def wait_for_job(
    client: ApiClient,
    task_id: str,
    *,
    wait_timeout: float,
    poll_interval: float,
) -> dict[str, Any]:
    """Poll a job until it is done or fails.

    Args:
        client: API client.
        task_id: Server task id.
        wait_timeout: Maximum seconds to wait.
        poll_interval: Seconds between polls.

    Returns:
        dict[str, Any]: Completed job record.

    Raises:
        ApiError: When the job fails or returns an unknown status.
        WaitTimeout: When the deadline passes first.
    """
    deadline = time.monotonic() + wait_timeout
    while True:
        job = client.job(task_id)
        status = job.get("status")
        if status == "done":
            return job
        if status == "error":
            error = job.get("error") or "unknown error"
            raise ApiError(f"job {task_id} failed: {error}")
        if status not in {"queued", "running"}:
            raise ApiError(f"job {task_id} returned unknown status {status!r}")
        if time.monotonic() >= deadline:
            raise WaitTimeout(
                f"job {task_id} is still {status} after {wait_timeout:.0f}s; recover with: save --task-id {task_id}"
            )
        client.sleeper(poll_interval)


def save_result(
    client: ApiClient,
    job: dict[str, Any],
    *,
    out: str | None,
    force: bool,
    strict: bool,
) -> SaveReport:
    """Fetch and save a completed run, then verify the saved files.

    Args:
        client: API client.
        job: Completed job record.
        out: Optional output directory.
        force: Allow overwriting a non-empty directory.
        strict: Treat advisory verification findings as failures.

    Returns:
        SaveReport: Saved paths and verification.

    Raises:
        ApiError: When the artifact or sources cannot be fetched.
        VerificationError: When hard or strict verification fails.
    """
    task_id = job.get("task_id")
    query = job.get("query")
    if not isinstance(task_id, str) or not task_id:
        raise ApiError("job record has no task_id")
    if not isinstance(query, str) or not query.strip():
        raise ApiError("job record has no query")
    directory = output_dir_for(query, out, project_root=client.config.project_root)
    check_output_dir(directory, force)

    artifact = client.artifact(task_id)
    article = artifact.get("article")
    if not isinstance(article, str):
        raise ApiError("artifact payload has no article text")
    sources = _source_records(client.sources(task_id))

    prepare_output_dir(directory, force)
    article_path = directory / "article.md"
    sources_path = directory / "sources.json"
    run_path = directory / "run.json"
    write_text_atomic(article_path, article)
    write_json(sources_path, sources)

    run_document: dict[str, Any] = {
        "schema_version": 1,
        "client_version": VERSION,
        "task_id": task_id,
        "thread_id": job.get("thread_id"),
        "query": query,
        "workflow": job.get("workflow"),
        "status": job.get("status"),
        "settings": job.get("settings"),
        "sources_count": len(sources),
        "saved_at": datetime.now(UTC).isoformat(),
        "base_url": client.config.base_url,
        "artifact_sha256": hashlib.sha256(article.encode("utf-8")).hexdigest(),
    }
    write_json(run_path, run_document)
    verification = verify_path(directory, strict=strict)
    run_document["verification"] = verification.to_dict()
    write_json(run_path, run_document)

    report = SaveReport(
        job=job,
        directory=directory,
        article=article_path,
        sources_file=sources_path,
        run_file=run_path,
        verification=verification,
    )
    if not verification.ok:
        raise VerificationError(
            f"verification failed for {directory}; see {run_path}",
            details=verification.to_dict(),
        )
    if strict and not verification.strict_ok:
        raise VerificationError(
            f"strict verification failed for {directory}; see {run_path}",
            details=verification.to_dict(),
        )
    return report


def build_client(args: argparse.Namespace, *, require_token: bool = True) -> ApiClient:
    """Build a client from parsed arguments.

    Args:
        args: Parsed arguments.
        require_token: Reject a missing token for data routes.

    Returns:
        ApiClient: Configured client.
    """
    config = load_config(args, require_token=require_token)
    return ApiClient(
        config,
        http_timeout=args.http_timeout,
        max_retry_wait=args.max_retry_wait,
    )


def configure_console() -> None:
    """Best-effort UTF-8 console configuration for Windows terminals."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


def emit_json(payload: Any) -> None:
    """Print a JSON document.

    Args:
        payload: JSON-safe data.
    """
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def emit_verification(report: VerificationReport) -> None:
    """Print a human-readable verification summary.

    Args:
        report: Verification report.
    """
    state = "ok" if report.ok else "FAILED"
    strict = "strict-ok" if report.strict_ok else "strict-failed"
    print(f"verification: {state} ({strict})")
    print(f"sources: {report.sources}")
    print(f"citations: {report.markers} markers / {report.definitions} definitions")
    for error in report.errors:
        print(f"error: {error}")
    for warning in report.warnings:
        print(f"warning: {warning}")


def cmd_health(args: argparse.Namespace) -> int:
    """Probe liveness and readiness.

    Args:
        args: Parsed arguments.

    Returns:
        int: Process exit code.
    """
    client = build_client(args, require_token=False)
    health = client.health()
    readiness = client.readiness()
    if health.get("status") != "ok":
        raise ApiError("service health is not ok")
    payload = {
        "ok": True,
        "base_url": client.config.base_url,
        "health": health,
        "readiness": readiness,
    }
    if args.json:
        emit_json(payload)
    else:
        print(f"base_url: {client.config.base_url}")
        print(f"health: {health.get('status', 'unknown')}")
        print(f"readiness: {'ok' if readiness.get('ok') else 'degraded'}")
        checks = readiness.get("checks")
        if isinstance(checks, dict):
            for name, value in checks.items():
                print(f"  {name}: {'ok' if value else 'false'}")
    return EXIT_OK


def cmd_wiki(args: argparse.Namespace) -> int:
    """Query the compiled wiki.

    Args:
        args: Parsed arguments.

    Returns:
        int: Process exit code.
    """
    query = normalize_query(args.query, max_length=2000)
    if not 1 <= args.limit <= 20:
        raise UsageError("--limit must be between 1 and 20")
    client = build_client(args)
    payload = client.wiki_query(query, args.limit)
    hits = payload.get("hits")
    if not isinstance(hits, list):
        raise ApiError("service returned an invalid wiki hit list")
    result = {"ok": True, "query": query, "hits": hits}
    if args.json:
        emit_json(result)
    elif not hits:
        print("no wiki hits")
    else:
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            print(f"- {hit.get('slug', '?')} ({hit.get('score', 0)}): {hit.get('title', '')}")
            summary = hit.get("summary")
            if summary:
                print(f"  {summary}")
    return EXIT_OK


def cmd_page(args: argparse.Namespace) -> int:
    """Read one compiled wiki page.

    Args:
        args: Parsed arguments.

    Returns:
        int: Process exit code.
    """
    slug = args.slug.strip()
    if not slug:
        raise UsageError("--slug must not be blank")
    client = build_client(args)
    markdown = client.wiki_page(slug)
    if args.json:
        emit_json({"ok": True, "slug": slug, "markdown": markdown})
    else:
        print(markdown)
    return EXIT_OK


def cmd_status(args: argparse.Namespace) -> int:
    """Read one job record.

    Args:
        args: Parsed arguments.

    Returns:
        int: Process exit code.
    """
    client = build_client(args)
    job = client.job(args.task_id)
    if args.json:
        emit_json({"ok": True, "job": job})
    else:
        print(f"task: {job.get('task_id')}")
        print(f"status: {job.get('status')}")
        print(f"thread: {job.get('thread_id')}")
        print(f"workflow: {job.get('workflow')}")
        print(f"query: {job.get('query')}")
        if job.get("error"):
            print(f"error: {job['error']}")
    return EXIT_OK


def cmd_run(args: argparse.Namespace) -> int:
    """Submit, poll, save, and verify a research run.

    Args:
        args: Parsed arguments.

    Returns:
        int: Process exit code.
    """
    query = normalize_query(args.query)
    settings = build_settings(args)
    thread_id = validate_thread_id(args.thread_id or generate_thread_id())
    if not 0.1 <= args.poll_interval <= 60:
        raise UsageError("--poll-interval must be between 0.1 and 60 seconds")
    if args.wait_timeout <= 0:
        raise UsageError("--wait-timeout must be positive")
    if not args.wait and (args.save or args.strict or args.out or args.force):
        raise UsageError("--save/--strict/--out/--force require a waiting run")
    if args.save and not args.wait:
        raise UsageError("--save requires --wait")
    if args.strict and not args.save:
        raise UsageError("--strict requires --save")
    if args.out and not args.save:
        raise UsageError("--out requires --save")
    if args.force and not args.save:
        raise UsageError("--force requires --save")

    output_dir = output_dir_for(query, args.out, project_root=resolve_project_root(args)) if args.save else None
    if output_dir is not None:
        check_output_dir(output_dir, args.force)

    client = build_client(args)
    try:
        task_id = client.submit(query, args.workflow, thread_id, settings)
    except ApiError as exc:
        details = exc.details if isinstance(exc.details, dict) else {}
        raise ApiError(
            f"{exc} (thread_id={thread_id})",
            details={**details, "thread_id": thread_id},
        ) from None

    if not args.wait:
        result = {
            "ok": True,
            "task_id": task_id,
            "thread_id": thread_id,
            "query": query,
            "workflow": args.workflow,
            "status": "queued",
            "saved": False,
        }
        if args.json:
            emit_json(result)
        else:
            print(f"task_id: {task_id}")
            print(f"thread_id: {thread_id}")
            print("status: queued (not waiting; use save --task-id later)")
        return EXIT_OK

    job = wait_for_job(
        client,
        task_id,
        wait_timeout=args.wait_timeout,
        poll_interval=args.poll_interval,
    )
    if not args.save:
        result = {
            "ok": True,
            "task_id": task_id,
            "thread_id": thread_id,
            "query": query,
            "workflow": args.workflow,
            "status": job.get("status"),
            "sources_count": _job_source_count(job),
            "saved": False,
        }
        if args.json:
            emit_json(result)
        else:
            print(f"task_id: {task_id}")
            print(f"status: {job.get('status')}")
            print(f"sources: {_job_source_count(job)}")
            print("saved: no (re-run with --save or use save --task-id)")
        return EXIT_OK

    report = save_result(
        client,
        job,
        out=args.out,
        force=args.force,
        strict=args.strict,
    )
    if args.json:
        emit_json(report.to_dict())
    else:
        print(f"task_id: {report.job.get('task_id')}")
        print(f"thread_id: {report.job.get('thread_id')}")
        print(f"status: {report.job.get('status')}")
        print(f"saved: {report.directory}")
        print(f"article: {report.article}")
        print(f"sources: {report.sources}")
        emit_verification(report.verification)
    return EXIT_OK if report.verification.strict_ok or not args.strict else EXIT_VERIFY


def cmd_save(args: argparse.Namespace) -> int:
    """Recover a submitted job by task id and save it.

    Args:
        args: Parsed arguments.

    Returns:
        int: Process exit code.
    """
    if not 0.1 <= args.poll_interval <= 60:
        raise UsageError("--poll-interval must be between 0.1 and 60 seconds")
    if args.wait_timeout <= 0:
        raise UsageError("--wait-timeout must be positive")
    client = build_client(args)
    job = client.job(args.task_id)
    if job.get("status") != "done":
        job = wait_for_job(
            client,
            args.task_id,
            wait_timeout=args.wait_timeout,
            poll_interval=args.poll_interval,
        )
    report = save_result(
        client,
        job,
        out=args.out,
        force=args.force,
        strict=args.strict,
    )
    if args.json:
        emit_json(report.to_dict())
    else:
        print(f"task_id: {report.job.get('task_id')}")
        print(f"saved: {report.directory}")
        print(f"article: {report.article}")
        print(f"sources: {report.sources}")
        emit_verification(report.verification)
    return EXIT_OK if report.verification.strict_ok or not args.strict else EXIT_VERIFY


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify a saved note without touching the network.

    Args:
        args: Parsed arguments.

    Returns:
        int: Process exit code.
    """
    report = verify_path(Path(args.path), strict=args.strict)
    if args.json:
        payload = report.to_dict()
        payload["ok"] = report.ok and (report.strict_ok or not args.strict)
        emit_json(payload)
    else:
        print(f"path: {args.path}")
        emit_verification(report)
    return EXIT_OK if report.ok and (report.strict_ok or not args.strict) else EXIT_VERIFY


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--base-url", help="Knowledge Engine base URL; defaults to RESEARCH_BASE_URL")
    common.add_argument("--env-file", help="explicit .env path; otherwise search upward from cwd")
    common.add_argument(
        "--anonymous",
        action="store_true",
        help="omit the bearer token; loopback URLs only (local development)",
    )
    common.add_argument(
        "--http-timeout",
        type=float,
        default=DEFAULT_HTTP_TIMEOUT,
        help=f"per-request timeout in seconds (default {DEFAULT_HTTP_TIMEOUT:.0f})",
    )
    common.add_argument(
        "--max-retry-wait",
        type=float,
        default=MAX_RETRY_WAIT,
        help=f"longest Retry-After to honor (default {MAX_RETRY_WAIT:.0f}s)",
    )
    common.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    parser = argparse.ArgumentParser(
        prog="deep-research",
        description="Cited research through the Knowledge Engine HTTP service.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  research.py health --json\n"
            '  research.py wiki --query "retrieval augmented generation" --json\n'
            '  research.py run --query "state of the art in RAG" --workflow research --save --json\n'
            "  research.py save --task-id <id> --json\n"
            "  research.py verify --path docs/research/2026-10-25-rag --strict --json\n"
        ),
    )
    parser.add_argument("--version", action="version", version=f"deep-research {VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health", parents=[common], help="probe health and readiness")
    health.set_defaults(func=cmd_health)

    wiki = subparsers.add_parser("wiki", parents=[common], help="query the compiled wiki")
    wiki.add_argument("--query", required=True, help="wiki query")
    wiki.add_argument("--limit", type=int, default=3, help="maximum hits (1-20)")
    wiki.set_defaults(func=cmd_wiki)

    page = subparsers.add_parser("page", parents=[common], help="read one wiki page")
    page.add_argument("--slug", required=True, help="kebab-case page slug")
    page.set_defaults(func=cmd_page)

    status = subparsers.add_parser("status", parents=[common], help="read a job record")
    status.add_argument("--task-id", required=True, help="server task id")
    status.set_defaults(func=cmd_status)

    run = subparsers.add_parser("run", parents=[common], help="submit and optionally save a run")
    run.add_argument("--query", required=True, help="research question")
    run.add_argument(
        "--workflow",
        choices=("research", "qa", "summary", "deep"),
        default="research",
        help="workflow to run (default research)",
    )
    run.add_argument("--thread-id", help="optional stable thread id")
    run.add_argument("--max-depth", type=int, help="deep decompose depth (0-3)")
    run.add_argument("--max-subqueries", type=int, help="deep fan-out cap (1-7)")
    run.add_argument("--max-iterations", type=int, help="judge loop cap (0-2)")
    run.add_argument("--max-wiki-pages", type=int, help="wiki page cap (1-20)")
    run.add_argument("--thesis", help="optional thesis to file (max 300 chars)")
    run.add_argument("--wiki-extract", action="store_true", help="enable wiki concept extraction")
    run.add_argument("--wiki-save-answers", action="store_true", help="file the answer in the wiki")
    run.add_argument("--approve-deep", action="store_true", help="explicit approval for a deep run")
    run.add_argument("--no-wait", dest="wait", action="store_false", help="return after submission")
    run.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_SECONDS, help="seconds between polls")
    run.add_argument("--wait-timeout", type=float, default=DEFAULT_WAIT_SECONDS, help="maximum seconds to wait")
    run.add_argument("--save", action="store_true", help="write the note and verify it")
    run.add_argument("--out", help="output directory (default docs/research/<date>-<slug>)")
    run.add_argument("--force", action="store_true", help="overwrite a non-empty output directory")
    run.add_argument("--strict", action="store_true", help="fail on advisory verification findings")
    run.set_defaults(func=cmd_run, wait=True)

    save = subparsers.add_parser("save", parents=[common], help="recover and save a submitted job")
    save.add_argument("--task-id", required=True, help="server task id")
    save.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_SECONDS, help="seconds between polls")
    save.add_argument("--wait-timeout", type=float, default=DEFAULT_WAIT_SECONDS, help="maximum seconds to wait")
    save.add_argument("--out", help="output directory (default docs/research/<date>-<slug>)")
    save.add_argument("--force", action="store_true", help="overwrite a non-empty output directory")
    save.add_argument("--strict", action="store_true", help="fail on advisory verification findings")
    save.set_defaults(func=cmd_save)

    verify = subparsers.add_parser("verify", parents=[common], help="verify a saved note offline")
    verify.add_argument("--path", required=True, help="saved note directory")
    verify.add_argument("--strict", action="store_true", help="fail on advisory findings")
    verify.set_defaults(func=cmd_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Arguments to parse; defaults to ``sys.argv``.

    Returns:
        int: Process exit code.
    """
    configure_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SkillError as exc:
        payload = {
            "ok": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        }
        if getattr(args, "json", False):
            print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        else:
            print(f"error: {exc.message}", file=sys.stderr)
        return exc.exit_code
    except OSError as exc:
        payload = {
            "ok": False,
            "error": {
                "code": "io",
                "message": f"I/O error: {exc}",
                "details": None,
            },
        }
        if getattr(args, "json", False):
            print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        else:
            print(f"error: I/O error: {exc}", file=sys.stderr)
        return EXIT_API
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
