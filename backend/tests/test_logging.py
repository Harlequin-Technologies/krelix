from krelix.logging import redact_secrets


def test_redacts_password() -> None:
    event = {"event": "login", "password": "hunter2"}
    out = redact_secrets(None, "info", event)
    assert out["password"] == "<redacted>"


def test_redacts_case_insensitive_and_nested() -> None:
    event = {
        "event": "request",
        "Authorization": "Bearer abc",
        "headers": {"Set-Cookie": "session=xyz", "X-Trace": "ok"},
        "items": [{"hf_token": "tok_123"}, {"safe": "value"}],
    }
    out = redact_secrets(None, "info", event)
    assert out["Authorization"] == "<redacted>"
    assert out["headers"]["Set-Cookie"] == "<redacted>"
    assert out["headers"]["X-Trace"] == "ok"
    assert out["items"][0]["hf_token"] == "<redacted>"
    assert out["items"][1]["safe"] == "value"


def test_leaves_non_secret_fields_alone() -> None:
    event = {"event": "ping", "duration_ms": 12, "user_id": 7}
    out = redact_secrets(None, "info", event)
    assert out == {"event": "ping", "duration_ms": 12, "user_id": 7}
