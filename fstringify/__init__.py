__version__ = "0.1.14"


import argparse
import sys

from fstringify.api import fstringify_dir, fstringify_file, fstringify
from fstringify.transform import fstringify_code
from fstringify.process import fstringify_code_by_line


def main():
    parser = argparse.ArgumentParser(
        description=f"fstringify {__version__}", add_help=True
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--verbose", action="store_true", help="run with verbose output")
    group.add_argument("--quiet", action="store_true", help="run without output")
    parser.add_argument(
        "--version",
        action="version",
        default=False,
        help="show version and exit",
        version=__version__,
    )
    parser.add_argument("src", action="store", help="source file or directory")

    args = parser.parse_args()

    fstringify(args.src, verbose=args.verbose, quiet=args.quiet)


if __name__ == "__main__":
    main()
