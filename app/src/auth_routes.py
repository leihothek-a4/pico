import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request

from flask import Blueprint, redirect, render_template, request, session, url_for

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
GITHUB_ALLOWED_USERS = {
    u.strip().lower()
    for u in os.environ.get("GITHUB_ALLOWED_USERS", "").split(",")
    if u.strip()
}

auth_bp = Blueprint("auth", __name__)


def register_auth_guard(app):
    @app.before_request
    def require_github_login():
        if request.blueprint == "api":
            return None
        if request.endpoint and request.endpoint.startswith("auth."):
            return None
        if session.get("github_user") in GITHUB_ALLOWED_USERS:
            return None
        return redirect(url_for("auth.login", next=request.url))


@auth_bp.route("/login")
def login():
    if session.get("github_user") in GITHUB_ALLOWED_USERS:
        return redirect(request.args.get("next") or url_for("mainpage"))

    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET or not GITHUB_ALLOWED_USERS:
        return render_template("login.html", config_error=True), 503

    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    session["login_next"] = request.args.get("next") or url_for("mainpage")

    params = urllib.parse.urlencode(
        {
            "client_id": GITHUB_CLIENT_ID,
            "redirect_uri": url_for("auth.callback", _external=True),
            "scope": "read:user",
            "state": state,
        }
    )
    return redirect(f"https://github.com/login/oauth/authorize?{params}")


@auth_bp.route("/auth/callback")
def callback():
    if request.args.get("state") != session.pop("oauth_state", None):
        return render_template("login.html", error="Invalid login state."), 400

    code = request.args.get("code")
    if not code:
        return render_template("login.html", error="GitHub did not return a code."), 400

    try:
        token = _exchange_code(code)
        login = _fetch_github_login(token)
    except (urllib.error.HTTPError, RuntimeError, urllib.error.URLError):
        return render_template("login.html", error="Could not verify with GitHub."), 502

    if login.lower() not in GITHUB_ALLOWED_USERS:
        session.clear()
        return render_template("login.html", denied=True, github_user=login), 403

    session["github_user"] = login.lower()
    return redirect(session.pop("login_next", url_for("mainpage")))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


def _exchange_code(code: str) -> str:
    body = urllib.parse.urlencode(
        {
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": url_for("auth.callback", _external=True),
        }
    ).encode()
    req = urllib.request.Request(
        "https://github.com/login/oauth/access_token",
        data=body,
        headers={"Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    token = data.get("access_token")
    if not token:
        raise RuntimeError("no access_token in GitHub response")
    return token


def _fetch_github_login(token: str) -> str:
    req = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    login = data.get("login")
    if not login:
        raise RuntimeError("no login in GitHub user response")
    return login
