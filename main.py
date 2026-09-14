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
    if args.cmd == "discover":
        from sources import discover
        res = discover.run(refresh=args.refresh)
        print({k: len(v) for k, v in res.items()})
        return 0
    if args.cmd == "collect":
        from sources import collect
        collect.run(refresh=args.refresh)
        return 0
    if args.cmd == "prepare":
        from extract import prepare
        prepare.run(limit=args.limit)
        return 0
    if args.cmd == "validate":
        from extract import validate
        validate.run()
        return 0
    if args.cmd == "render":
        from render import render as r
        r.run(fixture=args.fixture)
        return 0
    print(f"{args.cmd}: not implemented yet", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
