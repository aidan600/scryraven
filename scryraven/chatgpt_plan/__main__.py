"""Explicit setup for the existing approved ChatGPT-plan sign-in flow."""
from __future__ import annotations

import argparse
import json

from .auth import Auth
from .http import MODELS, PlanError


def main(argv=None, *, auth=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("accounts", help="List local labels; no inference")
    sign_in = commands.add_parser("sign-in", help="Sign in through the system browser; no inference")
    sign_in.add_argument("--account", required=True)
    sign_in.add_argument("--consent", action="store_true")
    models = commands.add_parser("models", help="Inspect the selected account's model catalog; no inference")
    models.add_argument("--account", required=True)
    args = parser.parse_args(argv)
    auth = auth if auth is not None else Auth()
    if args.command == "accounts":
        result = {"accounts": auth.accounts()}
    elif args.command == "sign-in":
        result = auth.sign_in(args.account, consent=args.consent)
    else:
        row = auth.access(args.account, timeout=30)
        body = auth.http.json("GET", MODELS, timeout=30,
                              headers={"Authorization": "Bearer " + row["access_token"]})
        values = body.get("models")
        if not isinstance(values, list):
            raise PlanError("malformed_model_response", reason="invalid_model_catalog")
        result = {"account": args.account, "models": [
            {"slug": value["slug"], "display_name": value["display_name"]}
            for value in values if isinstance(value, dict) and value.get("visibility") == "list"
            and isinstance(value.get("slug"), str) and isinstance(value.get("display_name"), str)]}
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    try:
        main()
    except PlanError as error:
        print(json.dumps({"error": error.diagnostic, "fallback": False}))
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        raise SystemExit(130) from None
