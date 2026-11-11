"""Bounded external research. Responses are untrusted text and have no tool access."""

import http.client
import ipaddress
import json
import re
import socket
import ssl
from html.parser import HTMLParser
from time import monotonic
from urllib.parse import SplitResult, urlsplit

from pydantic import BaseModel, Field, ValidationError

from packages.domain.design import DomainError

MAX_BYTES = 256_000


def public_url(value: str) -> SplitResult:
    """Accept ordinary HTTPS domain URLs without credentials or alternate ports."""
    try:
        url = urlsplit(value)
        host = url.hostname or ""
        if (
            len(value) > 2048
            or url.scheme != "https"
            or url.netloc.lower() not in (host, host + ":443")
            or not re.fullmatch(
                r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{1,62}", host
            )
            or "\\" in value
            or any(ord(char) <= 32 or ord(char) >= 127 for char in value)
        ):
            raise ValueError
        return url
    except ValueError as exc:
        raise DomainError("unsafe_source_url", 422) from exc


class PinnedHTTPS(http.client.HTTPSConnection):
    """Connect to the inspected IP while validating TLS against the original hostname."""

    def __init__(self, host: str, address: str) -> None:
        super().__init__(host, timeout=4)
        self.address = address

    def connect(self) -> None:
        connection = socket.create_connection((self.address, 443), timeout=4)
        try:
            self.sock = ssl.create_default_context().wrap_socket(
                connection, server_hostname=self.host
            )
        except BaseException:
            connection.close()
            raise


def read_public_source(
    host: str,
    path: str,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[str, bytes]:
    """Block private DNS answers, redirects, compression and oversized responses."""
    deadline = monotonic() + 8
    try:
        answers = socket.getaddrinfo(host, 443, family=socket.AF_INET, type=socket.SOCK_STREAM)
        addresses = [ipaddress.ip_address(str(answer[4][0])) for answer in answers]
        if not addresses or any(not ip.is_global or ip.is_multicast for ip in addresses):
            raise DomainError("unsafe_source_address", 422)
        connection = PinnedHTTPS(host, str(addresses[0]))
        try:
            connection.request(
                method,
                path,
                body=body,
                headers={
                    "Accept-Encoding": "identity",
                    "User-Agent": "AtelierOS Research/1.0",
                    **(headers or {}),
                },
            )
            with connection.getresponse() as response:
                if 300 <= response.status < 400:
                    raise DomainError("source_redirect_blocked", 422)
                if response.status != 200:
                    raise DomainError("research_upstream_unavailable", 502)
                if response.getheader("Content-Encoding", "identity").lower() != "identity":
                    raise DomainError("unsupported_source_encoding", 422)
                mime = response.headers.get_content_type()
                if mime not in ("text/plain", "text/html", "application/json"):
                    raise DomainError("unsupported_source_type", 422)
                if int(response.getheader("Content-Length", "0")) > MAX_BYTES:
                    raise DomainError("source_too_large", 422)
                content = bytearray()
                while True:
                    if monotonic() >= deadline:
                        raise DomainError("research_upstream_timeout", 504)
                    chunk = response.read1(8192)
                    if not chunk:
                        return mime, bytes(content)
                    content.extend(chunk)
                    if len(content) > MAX_BYTES:
                        raise DomainError("source_too_large", 422)
        finally:
            connection.close()
    except (OSError, http.client.HTTPException, ValueError) as exc:
        raise DomainError("research_upstream_unavailable", 502) from exc


class VisibleText(HTMLParser):
    """Extract text only and omit script, style and template data."""

    ignored = frozenset({"script", "style", "template", "noscript"})

    def __init__(self) -> None:
        super().__init__()
        self.hidden: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.ignored:
            self.hidden.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.hidden and self.hidden[-1] == tag:
            self.hidden.pop()

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def capture(url: str, allowed_hosts: list[str]) -> str:
    target = public_url(url)
    host = target.hostname or ""
    if host not in allowed_hosts:
        raise DomainError("source_host_not_allowed", 422)
    path = target.path or "/"
    if target.query:
        path += "?" + target.query
    mime, raw = read_public_source(host, path)
    value = raw.decode("utf-8", errors="replace")
    if mime == "text/html":
        parser = VisibleText()
        parser.feed(value)
        parser.close()
        value = " ".join(parser.parts)
    elif mime != "text/plain":
        raise DomainError("unsupported_source_type", 422)
    excerpt = " ".join(value.replace("\x00", "").split())[:4000]
    if not excerpt:
        raise DomainError("empty_source", 422)
    return excerpt


class SearchHit(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: str
    published_date: str | None = None


class SearchResponse(BaseModel):
    results: list[SearchHit] = Field(max_length=20)


def search(query: str, limit: int, period: str | None, secret: str) -> list[SearchHit]:
    payload = {
        "query": query,
        "max_results": limit,
        "search_depth": "basic",
        "include_raw_content": False,
        "include_images": False,
        "include_answer": False,
        "auto_parameters": False,
        "include_published_date": True,
    }
    if period:
        payload["time_range"] = period
    mime, raw = read_public_source(
        "api.tavily.com",
        "/search",
        "POST",
        json.dumps(payload).encode(),
        {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
    )
    if mime != "application/json":
        raise DomainError("invalid_search_response", 502)
    try:
        hits = SearchResponse.model_validate_json(raw).results
    except ValidationError as exc:
        raise DomainError("invalid_search_response", 502) from exc
    unique: dict[str, SearchHit] = {}
    for hit in hits:
        try:
            url = public_url(hit.url).geturl().split("#", 1)[0]
        except DomainError:
            continue
        unique.setdefault(url, hit.model_copy(update={"url": url}))
    return list(unique.values())[:limit]
