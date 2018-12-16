__version__ = "0.1.0"

import sys

from fstringify.api import fstringify_dir, fstringify_file, fstringify
from fstringify.transform import fstringify_code
from fstringify.process import fstringify_code_by_line


def main():
    if len(sys.argv) == 1:
        print("fstringify", __version__)
        sys.exit(0)

    src_path = sys.argv[1]

    fstringify(src_path)


if __name__ == "__main__":
    main()
