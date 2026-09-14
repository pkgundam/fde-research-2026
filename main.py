"""FDE roadmap pipeline CLI."""
import argparse
import sys


def main(argv=None):
    p = argparse.ArgumentParser(prog="fde-roadmap")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("discover", "collect", "prepare", "validate", "aggregate", "render"):
        sp = sub.add_parser(name)
        sp.add_argument("--refresh", action="store_true", help="re-hit sources (never default)")
        sp.add_argument("--fixture", action="store_true", help="render: use fixture data")
        sp.add_argument("--limit", type=int, default=None, help="prepare: only first N postings")
    args = p.parse_args(argv)
    print(f"{args.cmd}: not implemented yet", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
