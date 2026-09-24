from marketradar.federation import Source


def test_source_repr_does_not_expose_authorization_credentials():
    secret = "Bearer SUPER_SECRET_TOKEN_123"
    source = Source(
        "private-api",
        "https://api.example.com",
        access_scope="authorized",
        allow_hosts=("api.example.com",),
        headers=(("Authorization", secret),),
    )
    rendered = repr(source)
    assert "SUPER_SECRET_TOKEN_123" not in rendered
    assert "Authorization" not in rendered
    assert "api.example.com" in rendered
