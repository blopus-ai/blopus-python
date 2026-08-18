"""Command-line interface for Blopus — the web-search layer for AI agents.

Quick start:
    blopus login          # paste your API key once (saved to ~/.config/blopus)
    blopus search "spacex latest" --freshness pd

The key is resolved in this order: --api-key  >  $BLOPUS_API_KEY  >  saved login.
"""
# PYTHON_ARGCOMPLETE_OK
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from typing import List, Optional

from . import _common as C
from ._version import __version__
from .client import Blopus
from .exceptions import AuthError, BlopusError
from .mcp import mcp_config
from .models import BatchFetchResponse

ENV_API_KEY = C.ENV_API_KEY
SIGNUP_URL = "https://blopus.ai"
DOCS_URL = "https://blopus.ai/docs/"

_DESCRIPTION = """\
Blopus — the web-search layer for AI agents. Search a fresh, independent web
index and fetch page content, right from your shell or your code.
"""

_SETUP_STEPS = f"""\
Set up your API key (one time):

  1. Create a key:  sign in at {SIGNUP_URL}  ->  Dashboard  ->  API keys  ->  Create key
     (it looks like  blp_live_xxxxxxxxxxxx)

  2. Save it:       blopus login
     ...paste the key when prompted. That's it — it's stored in
     ~/.config/blopus/credentials.json (owner-only) and used automatically.

  3. Use it:        blopus search "spacex latest news" --freshness pd

  Prefer environment variables or CI?  export {ENV_API_KEY}="blp_live_..."
  Prefer one-off?                       blopus search "..." --api-key blp_live_...
"""

_EPILOG = f"""\
{_SETUP_STEPS}
Common commands:
  blopus login                                      save your API key (recommended)
  blopus whoami                                     show which key is active
  blopus search "who won the game" --freshness pd   search the live web
  blopus search "what did the Fed announce" --news-only    events only (see search --help)
  blopus search "openai" --include-domains reuters.com,ft.com
  blopus search "langchain" --json                  raw JSON for scripts
  blopus fetch https://example.com/article          read one indexed page
  blopus fetch URL1 URL2 URL3                        batch fetch (billed per URL)
  blopus mcp-config                                 MCP config for Claude/Cursor/etc.

Tab-completion (optional):
  pip install argcomplete && eval "$(register-python-argcomplete blopus)"
  (add that eval line to ~/.zshrc or ~/.bashrc to keep it)

Docs: {DOCS_URL}
"""


def _csv(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    return [v.strip() for v in value.split(",") if v.strip()]


def _mask(key: str) -> str:
    return f"{key[:12]}...{key[-4:]}" if len(key) > 20 else "(set)"


def _active_key_source():
    """Return (key, source_label) using the same precedence as the SDK."""
    if os.environ.get(ENV_API_KEY):
        return os.environ[ENV_API_KEY], f"environment variable {ENV_API_KEY}"
    saved = C.load_config_key()
    if saved:
        return saved, f"saved login ({C.CONFIG_FILE})"
    return None, None


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def _cmd_login(args: argparse.Namespace) -> int:
    key = args.api_key
    if not key:
        print(f"Paste your Blopus API key (get one at {SIGNUP_URL} -> API keys).")
        try:
            key = getpass.getpass("API key (hidden): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.", file=sys.stderr)
            return 1
    if not key:
        print("No key entered.", file=sys.stderr)
        return 1
    if not key.startswith("blp_"):
        print("Warning: that doesn't look like a Blopus key (expected blp_live_...).",
              file=sys.stderr)

    path = C.save_config_key(key)
    print(f"Saved to {path}  (readable only by you).")

    if args.no_verify:
        print("Skipped verification. Try:  blopus search \"hello\" --count 1")
        return 0
    print("Verifying...", end=" ", flush=True)
    try:
        Blopus(api_key=key).search("blopus setup check", count=1)
        print("OK - your key works. You're all set!")
        return 0
    except AuthError:
        print("FAILED.")
        print("The key was saved but the server rejected it — double-check you "
              "copied the whole key. Re-run `blopus login` to try again.", file=sys.stderr)
        return 1
    except BlopusError as exc:
        # Saved fine; couldn't verify (offline / rate-limited). Not fatal.
        print(f"couldn't verify right now ({exc}). Key is saved; try a search later.")
        return 0


def _cmd_logout(args: argparse.Namespace) -> int:
    if C.clear_config_key():
        print(f"Removed saved key ({C.CONFIG_FILE}).")
    else:
        print("No saved key to remove.")
    return 0


def _cmd_whoami(args: argparse.Namespace) -> int:
    key, source = _active_key_source()
    if key:
        print(f"API key: {_mask(key)}")
        print(f"Source:  {source}")
    else:
        print("No API key configured. Run `blopus login` to set one.")
        return 1
    return 0


def _cmd_setup(args: argparse.Namespace) -> int:
    print(_DESCRIPTION)
    print(_SETUP_STEPS)
    key, source = _active_key_source()
    if key:
        print(f"[ok] Active key: {_mask(key)}  (from {source})")
        print('     Try it:  blopus search "hello world" --count 1')
    else:
        print("[!] No API key yet — run `blopus login` (step 2 above).")
    print(f"\nMCP (Claude Code, Cursor, Cline, ...):  blopus mcp-config")
    print(f"Docs: {DOCS_URL}")
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    client = Blopus(api_key=args.api_key, base_url=args.base_url)
    res = client.search(
        args.query,
        count=args.count,
        freshness=args.freshness,
        news_only=args.news_only,
        include_domains=_csv(args.include_domains),
        exclude_domains=_csv(args.exclude_domains),
        language=args.language,
        offset=args.offset,
        include_excerpt=args.include_excerpt,
        excerpt_chars=args.excerpt_chars,
        start_date=args.start_date,
        end_date=args.end_date,
        recency=args.recency,
        include_content=args.include_content,
        content_chars=args.content_chars,
        min_words=args.min_words,
        include_images=args.include_images,
    )
    if args.json:
        print(json.dumps(res.raw, indent=2, ensure_ascii=False))
    else:
        if not res.results:
            print("No results.")
        for i, r in enumerate(res.results, 1):
            print(f"{i}. {r.title}")
            print(f"   {r.url}")
            if r.content:
                print(f"   {r.content}")
            elif r.snippet:
                print(f"   {r.snippet}")
            # Only when asked for AND actually present -- partial coverage is normal.
            if r.image:
                dims = f" ({r.image_w}x{r.image_h})" if r.image_w and r.image_h else ""
                print(f"   image: {r.image}{dims}")
            print()
        if res.remaining_quota is not None:
            print(f"[remaining quota: {res.remaining_quota}]", file=sys.stderr)
    return 0


def _cmd_fetch(args: argparse.Namespace) -> int:
    client = Blopus(api_key=args.api_key, base_url=args.base_url)
    result = client.fetch(args.urls if len(args.urls) > 1 else args.urls[0])
    if args.json:
        raw = result.raw if not isinstance(result, BatchFetchResponse) else {
            "results": [r.raw for r in result.results],
            "failed_results": [f.raw for f in result.failed_results],
            "count": result.count,
            "remaining_quota": result.remaining_quota,
        }
        print(json.dumps(raw, indent=2, ensure_ascii=False))
        return 0
    if isinstance(result, BatchFetchResponse):
        for r in result.results:
            print(f"# {r.title}\n{r.url}\n{r.content[:2000]}\n")
        if result.failed_results:
            print("Not found:", ", ".join(f.url for f in result.failed_results),
                  file=sys.stderr)
    else:
        print(f"# {result.title}\n{result.url}\n\n{result.content}")
    return 0


def _cmd_mcp_config(args: argparse.Namespace) -> int:
    print(json.dumps(mcp_config(args.api_key), indent=2))
    return 0


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="blopus",
        description=_DESCRIPTION,
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"blopus {__version__}")

    # Shared auth options, attached to each subcommand via a parent parser.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--api-key", default=None, metavar="KEY",
                        help=f"Your blp_live_ key (else $ {ENV_API_KEY} or saved login).")
    common.add_argument("--base-url", default=None,
                        help="Override the API base URL (advanced).")

    sub = p.add_subparsers(dest="command", metavar="<command>",
                           title="commands")

    login = sub.add_parser(
        "login", help="Save your API key so you never pass it again.",
        parents=[common],
        description="Save your API key to ~/.config/blopus/credentials.json (owner-only) "
                    "and verify it works. Paste it when prompted, or pass --api-key.")
    login.add_argument("--no-verify", action="store_true",
                       help="Save without making a test request.")
    login.set_defaults(func=_cmd_login)

    logout = sub.add_parser("logout", help="Remove the saved API key.")
    logout.set_defaults(func=_cmd_logout)

    who = sub.add_parser("whoami", help="Show which API key is active and where it's from.")
    who.set_defaults(func=_cmd_whoami)

    setup = sub.add_parser(
        "setup", help="Show the setup guide and check your key.", parents=[common])
    setup.set_defaults(func=_cmd_setup)

    s = sub.add_parser(
        "search", help="Search the live web.", parents=[common],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Search the live web and print ranked results (or JSON).",
        epilog=(
            'Examples:\n'
            '  # an event -- scope to newsrooms, add a freshness window if breaking\n'
            '  blopus search "what did the Fed announce" --news-only --freshness pd\n'
            '  # documentation -- leave --news-only off\n'
            '  blopus search "kubernetes ingress example"\n'
            '  # wants the announcement AND the changelog -- leave it off\n'
            '  blopus search "what\'s new in Python 3.14"\n'
            '  blopus search "openai funding" --include-domains reuters.com,ft.com\n'
            '  blopus search "rust async" --json\n'))
    s.add_argument("query", help="What to search for.")
    s.add_argument("--count", type=int, default=10, metavar="N",
                   help="Number of results (1-50, default 10).")
    s.add_argument("--freshness", default="all",
                   choices=["pd", "pw", "pm", "p3m", "p1y", "all"],
                   help="Recency: pd=day, pw=week, pm=month, p3m=3mo, p1y=year, all (default).")
    s.add_argument("--news-only", action="store_true",
                   help="Search ONLY sources with a newsroom (newspapers, wires, "
                        "broadcasters, magazines). Use it for events: what happened, who "
                        "announced what, market reaction, election results, earnings news. "
                        "Leave it off for documentation, tutorials, forums or reference "
                        "material, and when a question wants both -- an unscoped search "
                        "returns everything, so omitting it is never wrong.")
    s.add_argument("--include-domains", default=None, metavar="LIST",
                   help="Comma-separated hostnames to allow, e.g. reuters.com,ft.com.")
    s.add_argument("--exclude-domains", default=None, metavar="LIST",
                   help="Comma-separated hostnames to exclude.")
    s.add_argument("--language", default=None, metavar="LANG",
                   help="Restrict to a language code, e.g. en, pt.")
    s.add_argument("--offset", type=int, default=0, metavar="N",
                   help="Skip N results for pagination (0-200).")
    s.add_argument("--include-excerpt", action="store_true",
                   help="Return a longer excerpt per result (skips a separate fetch).")
    s.add_argument("--recency", default=None, choices=["normal", "relaxed", "off"],
                   help="Ranking preference, not a filter. 'off' for timeless questions "
                        "where the best answer may be months old.")
    s.add_argument("--start-date", default=None, metavar="DATE",
                   help="Window start: YYYY-MM-DD or epoch seconds.")
    s.add_argument("--end-date", default=None, metavar="DATE",
                   help="Window end: YYYY-MM-DD or epoch seconds.")
    s.add_argument("--excerpt-chars", type=int, default=None, metavar="N",
                   help="Excerpt length when --include-excerpt is set.")
    s.add_argument("--include-content", action="store_true",
                   help="Return full text inline instead of a snippet. Costs the same as "
                        "the search, so it beats fetching each result separately.")
    s.add_argument("--content-chars", type=int, default=None, metavar="N",
                   help="Cap inline content length per result.")
    s.add_argument("--min-words", type=int, default=None, metavar="N",
                   help="Only return pages with at least N words. Use 120 when you want "
                        "something to READ - it drops tag listings and stub pages. Leave "
                        "off for breaking news, where a two-line wire story is a real answer.")
    s.add_argument("--include-images", action="store_true",
                   help="Include a hero image URL per result. Off by default; coverage is "
                        "partial, so some results will have no image.")
    s.add_argument("--json", action="store_true", help="Emit raw JSON instead of text.")
    s.set_defaults(func=_cmd_search)

    f = sub.add_parser(
        "fetch", help="Fetch indexed content for one or more URLs.",
        parents=[common],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Fetch the stored content of one URL, or a batch (billed per URL found).",
        epilog=(
            'Examples:\n'
            '  blopus fetch https://example.com/article\n'
            '  blopus fetch https://a.com/x https://b.com/y --json\n'))
    f.add_argument("urls", nargs="+", metavar="URL",
                   help="One URL, or several for a batch fetch.")
    f.add_argument("--json", action="store_true", help="Emit raw JSON instead of text.")
    f.set_defaults(func=_cmd_fetch)

    m = sub.add_parser(
        "mcp-config", help="Print MCP server config for Claude Code, Cursor, etc.",
        parents=[common],
        description="Print a ready-to-paste MCP server config using your API key.")
    m.set_defaults(func=_cmd_mcp_config)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    # Optional shell tab-completion (no-op if argcomplete isn't installed).
    try:
        import argcomplete  # type: ignore
        argcomplete.autocomplete(parser)
    except Exception:
        pass
    args = parser.parse_args(argv)
    # No subcommand -> show the guided setup instead of a bare usage error.
    if getattr(args, "command", None) is None:
        args.api_key = None
        return _cmd_setup(args)
    try:
        return args.func(args)
    except BlopusError as exc:
        if getattr(exc, "code", None) == "no_api_key":
            print("No API key found. Run `blopus login` to save one "
                  f"(get a key at {SIGNUP_URL}).", file=sys.stderr)
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
