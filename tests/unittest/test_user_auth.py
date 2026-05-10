"""Tests for app.core.firestore_handler.User – Auth class with mocked requests."""

from unittest.mock import MagicMock, patch

from app.core.firestore_handler.User import Auth
from requests import HTTPError


def _make_auth(api_key="test-key"):
    mock_req = MagicMock()
    return Auth(api_key, mock_req), mock_req


def _ok_response(data):
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    resp.status_code = 200
    resp.text = ""
    return resp


def _error_response(status_code=400, text="API key not valid"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.raise_for_status.side_effect = HTTPError(text)
    return resp


# ── Auth.__init__ ──────────────────────────────────────────────────────────


def test_auth_init():
    auth, _ = _make_auth("my-key")
    assert auth.api_key == "my-key"
    assert auth.current_user is None


# ── sign_in_with_email_and_password ────────────────────────────────────────


def test_sign_in_with_email_and_password():
    # Auth.sign_in_with_email_and_password uses the module-level requests.post
    with patch("app.core.firestore_handler.User.requests") as mock_req:
        user_data = {"idToken": "tok", "localId": "uid123"}
        mock_req.post.return_value = _ok_response(user_data)

        auth = Auth("key", mock_req)
        result = auth.sign_in_with_email_and_password("user@example.com", "pw")

    assert result["idToken"] == "tok"
    assert auth.current_user == user_data


def test_sign_in_sets_current_user():
    with patch("app.core.firestore_handler.User.requests") as mock_req:
        mock_req.post.return_value = _ok_response({"idToken": "t", "localId": "u"})
        auth = Auth("key", mock_req)
        auth.sign_in_with_email_and_password("a@b.com", "pw")
    assert auth.current_user["localId"] == "u"


def test_auth_uses_header_api_key_without_query_param_by_default():
    with patch("app.core.firestore_handler.User.requests") as mock_req:
        mock_req.post.return_value = _ok_response({"idToken": "tok", "localId": "uid"})
        auth = Auth("header-key", mock_req)

        auth.sign_in_with_email_and_password("user@example.com", "pw")

    post_call = mock_req.post.call_args_list[0]
    call_kwargs = post_call.kwargs
    call_url = call_kwargs.get("url", post_call.args[0])
    assert "?key=" not in call_url
    headers = call_kwargs["headers"]
    assert headers["X-Goog-Api-Key"] == "header-key"


def test_auth_falls_back_to_query_key_when_header_rejected():
    with patch("app.core.firestore_handler.User.requests") as mock_req:
        mock_req.post.side_effect = [
            _error_response(status_code=400, text="API key missing or invalid"),
            _ok_response({"idToken": "tok", "localId": "uid"}),
        ]
        auth = Auth("fallback-key", mock_req)

        result = auth.sign_in_with_email_and_password("user@example.com", "pw")

    assert result["localId"] == "uid"
    assert mock_req.post.call_count == 2
    first_call_kwargs = mock_req.post.call_args_list[0].kwargs
    second_call_kwargs = mock_req.post.call_args_list[1].kwargs
    first_url = first_call_kwargs.get("url", mock_req.post.call_args_list[0].args[0])
    second_url = second_call_kwargs.get("url", mock_req.post.call_args_list[1].args[0])
    assert "?key=" not in first_url
    assert second_url.endswith("?key=fallback-key")
    assert "X-Goog-Api-Key" in first_call_kwargs["headers"]
    assert "X-Goog-Api-Key" not in second_call_kwargs["headers"]


# ── sign_in_with_custom_token ──────────────────────────────────────────────


def test_sign_in_with_custom_token():
    with patch("app.core.firestore_handler.User.requests") as mock_req:
        mock_req.post.return_value = _ok_response({"idToken": "t2"})
        auth = Auth("key", mock_req)
        result = auth.sign_in_with_custom_token("custom-token")
    assert result["idToken"] == "t2"


# ── refresh ────────────────────────────────────────────────────────────────


def test_refresh():
    with patch("app.core.firestore_handler.User.requests") as mock_req:
        mock_req.post.return_value = _ok_response(
            {"user_id": "u1", "id_token": "new_tok", "refresh_token": "new_ref"}
        )
        auth = Auth("key", mock_req)
        result = auth.refresh("old_refresh_token")
    assert result["userId"] == "u1"
    assert result["idToken"] == "new_tok"
    assert result["refreshToken"] == "new_ref"


# ── get_account_info ──────────────────────────────────────────────────────


def test_get_account_info():
    with patch("app.core.firestore_handler.User.requests") as mock_req:
        mock_req.post.return_value = _ok_response({"users": [{"localId": "u1"}]})
        auth = Auth("key", mock_req)
        result = auth.get_account_info("id_token")
    assert result["users"][0]["localId"] == "u1"


# ── send_email_verification ────────────────────────────────────────────────


def test_send_email_verification():
    with patch("app.core.firestore_handler.User.requests") as mock_req:
        mock_req.post.return_value = _ok_response({"email": "user@example.com"})
        auth = Auth("key", mock_req)
        result = auth.send_email_verification("id_token")
    assert result["email"] == "user@example.com"


# ── send_password_reset_email ──────────────────────────────────────────────


def test_send_password_reset_email():
    with patch("app.core.firestore_handler.User.requests") as mock_req:
        mock_req.post.return_value = _ok_response({"email": "user@example.com"})
        auth = Auth("key", mock_req)
        result = auth.send_password_reset_email("user@example.com")
    assert result["email"] == "user@example.com"


# ── verify_password_reset_code ─────────────────────────────────────────────


def test_verify_password_reset_code():
    with patch("app.core.firestore_handler.User.requests") as mock_req:
        mock_req.post.return_value = _ok_response({"email": "user@example.com"})
        auth = Auth("key", mock_req)
        result = auth.verify_password_reset_code("reset-code", "new-pass")
    assert result["email"] == "user@example.com"


# ── create_user_with_email_and_password ────────────────────────────────────


def test_create_user_with_email_and_password():
    with patch("app.core.firestore_handler.User.requests") as mock_req:
        mock_req.post.return_value = _ok_response({"idToken": "t", "localId": "new_u"})
        auth = Auth("key", mock_req)
        result = auth.create_user_with_email_and_password("new@example.com", "pw123")
    assert result["localId"] == "new_u"
