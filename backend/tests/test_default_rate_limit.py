from app.main import app, limiter


def test_every_route_has_a_default_ceiling():
    assert limiter._default_limits, "write routes without their own @limiter.limit must still be bounded"
    assert any(m.cls.__name__ == "SlowAPIMiddleware" for m in app.user_middleware)
