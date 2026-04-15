from __future__ import annotations

from types import SimpleNamespace


def test_verify_supabase_token_falls_back_to_auth_api_for_asymmetric_tokens(monkeypatch):
    import app.core.supabase_auth as supabase_auth

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b'{"id":"22222222-2222-2222-2222-222222222222","email":"fallback@example.com"}'

    def _fake_decode(token, *args, **kwargs):
        if kwargs.get("options", {}).get("verify_signature") is False:
            return {"aud": "authenticated", "sub": "placeholder"}
        raise AssertionError("Local JWT verification should not run for RS256 tokens in this test")

    monkeypatch.setattr(
        supabase_auth,
        "get_settings",
        lambda: SimpleNamespace(
            supabase_url="https://example.supabase.co",
            supabase_anon_key="anon-key",
            supabase_service_role_key="",
            supabase_jwt_secret="jwt-secret",
        ),
    )
    monkeypatch.setattr(supabase_auth.jwt, "decode", _fake_decode)
    monkeypatch.setattr(supabase_auth.jwt, "get_unverified_header", lambda _token: {"alg": "RS256"})
    monkeypatch.setattr(supabase_auth.request, "urlopen", lambda _req, timeout=10: _Response())

    payload = supabase_auth.verify_supabase_token("supabase-token")

    assert payload["sub"] == "22222222-2222-2222-2222-222222222222"
    assert payload["email"] == "fallback@example.com"
