import os
import sys
import time

import astor

from fstringify.process import skip_file, fstringify_code_by_line


def fstringify_file(fn):
    if skip_file(fn):
        return False

    with open(fn) as f:
        contents = f.read()

    new_code = fstringify_code_by_line(contents)

    if new_code == contents:
        return False

    with open(fn, "w") as f:
        f.write(new_code)

    return True


def fstringify_dir(in_dir):
    use_dir = os.path.abspath(in_dir)
    print("use_dir", use_dir)
    if not os.path.exists(use_dir):
        print(f"`{in_dir}` not found")
        sys.exit(1)

    files = astor.code_to_ast.find_py_files(use_dir)
    change_count = 0
    start_time = time.time()
    for f in files:
        file_path = os.path.join(f[0], f[1])
        changed = fstringify_file(file_path)
        if changed:
            change_count += 1
        status = "yes" if changed else "no"
        # TODO: only if `verbose` is set
        print(f"fstringifying {file_path}...{status}")

    total_time = round(time.time() - start_time, 3)

    # TODO: not if `quiet` is set
    file_s = "s" if change_count != 1 else ""
    print(f"\nfstringified {change_count} file{file_s} in {total_time}s")
