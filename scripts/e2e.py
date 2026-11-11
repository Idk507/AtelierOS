"""Run isolated real PostgreSQL/API/OIDC/Next.js/Playwright integration.

The tiny OIDC issuer is synthetic test infrastructure, never a production login.
It implements one-use code + PKCE and nonce to exercise the actual web auth path.
"""
from __future__ import annotations

import base64
import argparse
import hashlib
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlencode

import httpx
import jwt
import uvicorn
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from apps.api.config import Settings
from apps.api.main import create_app
from apps.api.manage import provision

ROOT = Path(__file__).resolve().parents[1]


def port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true", help="Open an isolated synthetic studio")
    args = parser.parse_args()
    os.chdir(ROOT)
    url = os.environ.get("ATELIER_TEST_DATABASE_URL", "postgresql+psycopg://atelier_test@127.0.0.1:55439/atelier_test")
    if not (make_url(url).database or "").startswith("atelier_test"):
        raise RuntimeError("E2E requires a disposable atelier_test* database")
    schema = "e2e_" + secrets.token_hex(16)
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    config = Config(str(ROOT / "alembic.ini"))
    web_port, api_port, issuer_port = port(), port(), port()
    web_origin, issuer_origin = f"http://127.0.0.1:{web_port}", f"http://127.0.0.1:{issuer_port}"
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key().public_bytes(serialization.Encoding.PEM,
                                              serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    servers: list[uvicorn.Server] = []
    process = None
    local = ROOT / ".local"
    local.mkdir(exist_ok=True)
    try:
        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
        with Session(engine) as session, session.begin():
            organization_id, _ = provision(session, "design-partner", ["designer", "patternmaker"],
                                             organization_name="Synthetic design studio")
        settings = Settings(database_url=url, jwt_public_key=public, jwt_issuer=issuer_origin,
                            jwt_audience="atelier-api", allowed_hosts=["127.0.0.1"])
        issuer = FastAPI()
        codes: dict[str, dict[str, str]] = {}

        @issuer.get("/authorize")
        def authorize(request: Request):
            params = dict(request.query_params)
            if params.get("client_id") != "atelier-web" or params.get("redirect_uri") != web_origin + "/auth/callback" or params.get("code_challenge_method") != "S256":
                return JSONResponse({"error": "invalid_request"}, 400)
            code = secrets.token_urlsafe(32)
            codes[code] = params
            return RedirectResponse(web_origin + "/auth/callback?" + urlencode({"code": code, "state": params.get("state", "")}))

        @issuer.post("/token")
        async def token(request: Request):
            form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
            params = codes.pop(form.get("code", ""), None)
            challenge = base64.urlsafe_b64encode(hashlib.sha256(form.get("code_verifier", "").encode()).digest()).decode().rstrip("=")
            if params is None or params["code_challenge"] != challenge or form.get("redirect_uri") != web_origin + "/auth/callback":
                return JSONResponse({"error": "invalid_grant"}, 400)
            now = datetime.now(UTC)
            shared = {"sub": "design-partner", "iss": issuer_origin, "iat": now, "nbf": now,
                      "exp": now + timedelta(minutes=30)}
            access = jwt.encode({**shared, "aud": "atelier-api", "organization_id": organization_id,
                                 "principal_type": "human"}, private, algorithm="RS256")
            identity = jwt.encode({**shared, "aud": "atelier-web", "nonce": params["nonce"]}, private, algorithm="RS256")
            return {"access_token": access, "id_token": identity, "token_type": "Bearer"}

        for app, bind_port in [(create_app(settings, engine=engine), api_port), (issuer, issuer_port)]:
            server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=bind_port,
                                                   log_level="warning", access_log=False))
            servers.append(server)
            threading.Thread(target=server.run, daemon=True).start()
        env = {**os.environ, "ATELIER_WEB_ORIGIN": web_origin, "ATELIER_API_BASE_URL": f"http://127.0.0.1:{api_port}",
               "ATELIER_SESSION_KEY": base64.b64encode(secrets.token_bytes(32)).decode(),
               "ATELIER_JWT_PUBLIC_KEY": public, "ATELIER_JWT_ISSUER": issuer_origin,
               "ATELIER_JWT_AUDIENCE": "atelier-api", "ATELIER_OIDC_CLIENT_ID": "atelier-web",
               "ATELIER_OIDC_AUTHORIZATION_ENDPOINT": issuer_origin + "/authorize",
               "ATELIER_OIDC_TOKEN_ENDPOINT": issuer_origin + "/token", "ATELIER_E2E_WEB_ORIGIN": web_origin,
               "NEXT_TELEMETRY_DISABLED": "1", "ATELIER_E2E_ARTIFACT_DIR": str(local / "ui")}
        node = os.environ.get("ATELIER_NODE", r"C:\Program Files\nodejs\node.exe" if os.name == "nt" else "node")
        edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        if edge.exists(): env["ATELIER_E2E_BROWSER"] = str(edge)
        web = ROOT / "apps/web"
        with (local / "next-e2e.log").open("w") as log:
            process = subprocess.Popen([node, str(web / "node_modules/next/dist/bin/next"), "dev",
                "--hostname", "127.0.0.1", "--port", str(web_port)], cwd=web, env=env, stdout=log, stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            deadline = time.monotonic() + 180
            with httpx.Client(timeout=10, trust_env=False) as client:
                while time.monotonic() < deadline:
                    if process.poll() is not None: raise RuntimeError("Next.js exited; see .local/next-e2e.log")
                    try:
                        if client.get(web_origin).status_code == 200: break
                    except httpx.TransportError: pass
                    time.sleep(0.3)
                else: raise RuntimeError("Next.js readiness timed out; see .local/next-e2e.log")
            if args.serve:
                print(f"Synthetic studio running at {web_origin}. Press Ctrl+C to stop.", flush=True)
                try:
                    return process.wait()
                except KeyboardInterrupt:
                    return 0
            result = subprocess.run([node, str(web / "node_modules/@playwright/test/cli.js"), "test"], cwd=web, env=env)
            return result.returncode
    finally:
        if process is not None:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        for server in servers: server.should_exit = True
        time.sleep(0.3)
        engine.dispose()
        if not schema.startswith("e2e_") or len(schema) != 36: raise RuntimeError("Unsafe cleanup target")
        with admin.begin() as conn: conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


if __name__ == "__main__":
    sys.exit(main())
