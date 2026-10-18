"""Command line entry point: `lexishield serve | info`."""

from __future__ import annotations

import argparse
import asyncio
import json
import os


def _serve(args: argparse.Namespace) -> None:
    import uvicorn

    if args.profile:
        os.environ["LEXISHIELD_MODELS__PROFILE"] = args.profile
    from .api.app import create_app
    from .settings import get_settings

    cfg = get_settings()
    host = args.host or cfg.server.host
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit("Refusing to bind a non-loopback address: LexiShield must stay on-device.")
    # access_log off: request paths are harmless, but we keep logs minimal by policy.
    uvicorn.run(create_app(cfg), host=host, port=args.port or cfg.server.port, access_log=False)


def _info(args: argparse.Namespace) -> None:
    if args.profile:
        os.environ["LEXISHIELD_MODELS__PROFILE"] = args.profile
    from .llm.gateway import LLMGateway
    from .settings import get_settings

    cfg = get_settings()
    gw = LLMGateway(cfg)

    async def run() -> dict:
        return {
            "profile": cfg.models.profile,
            "chat_model": gw.chat_model,
            "embed_model": gw.embed_model,
            "ollama_host": cfg.ollama.host,
            "ollama_version": await gw.ollama_version(),
            "installed": [m["name"] for m in await gw.list_models()],
        }

    print(json.dumps(asyncio.run(run()), indent=2))


def main() -> None:
    p = argparse.ArgumentParser(prog="lexishield")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="Run the API on loopback")
    s.add_argument("--profile", choices=["gpu", "cpu"])
    s.add_argument("--host")
    s.add_argument("--port", type=int)
    s.set_defaults(func=_serve)
    i = sub.add_parser("info", help="Show model/runtime configuration")
    i.add_argument("--profile", choices=["gpu", "cpu"])
    i.set_defaults(func=_info)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
