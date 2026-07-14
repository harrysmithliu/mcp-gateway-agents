from frontend.components.evidence import _is_http_url


def test_source_reference_only_becomes_link_for_http_url() -> None:
    assert _is_http_url("https://docs.example.test/policy") is True
    assert _is_http_url("http://localhost:8000/source/doc-1") is True
    assert _is_http_url("data/trading.md") is False
    assert _is_http_url("file:///tmp/trading.md") is False
    assert _is_http_url("javascript:alert(1)") is False
