from __future__ import annotations

from django.conf import settings


def portfolio_demo_username() -> str:
    return str(
        getattr(settings, "PORTFOLIO_DEMO_USERNAME", "portfolio-demo")
        or "portfolio-demo"
    ).strip()


def is_portfolio_demo_user(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False

    username = str(getattr(user, "username", "") or "").strip()
    expected = portfolio_demo_username()

    return bool(
        username
        and expected
        and username.casefold() == expected.casefold()
    )
