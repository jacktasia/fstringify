import io
import token
import tokenize

from fstringify.utils import get_indent, get_lines
from fstringify.transform import fstringify_code
from fstringify.format import force_double_quote_fstring


def skip_line(raw_line):
    punt = False
    try:
        g = tokenize.tokenize(io.BytesIO(raw_line.encode("utf-8")).readline)
        found_bin_op = False
        found_paren = False
        for toknum, tokval, _, _, _ in g:
            # print(toknum, tokval)
            if toknum == 53 and tokval == "%":
                found_bin_op = True
            elif found_bin_op and toknum == 53 and tokval == "(":
                found_paren = True
            elif found_bin_op and not found_paren and toknum == 1 and tokval == "if":
                punt = True
            elif found_bin_op and toknum == 53 and tokval == ":":
                punt = False
    except tokenize.TokenError:
        pass

    return punt


def usable_chunk(fn):
    """use tokenizer to make a fancier
        `"s%" not in contents`
    """
    f = io.BytesIO(fn.encode("utf-8"))

    try:
        g = tokenize.tokenize(f.readline)
        last_toknum = None
        last_tokval = None
        for toknum, tokval, _, _, _ in g:
            if (
                toknum == 53
                and tokval == "%"
                and last_toknum == 3
                and "\\n" not in last_tokval
            ):
                return True

            last_toknum = toknum
            last_tokval = tokval
    except tokenize.TokenError:
        pass

    return False


def get_chunk(code):
    g = tokenize.tokenize(io.BytesIO(code.encode("utf-8")).readline)
    chunk = []
    END_CHECK = 58  # token.N_TOKENS in 3.7
    for item in g:
        toknum, tokval, start, end, content = item

        tok_type = token.tok_name[toknum]
        if toknum in (token.NEWLINE, token.DEDENT):
            if chunk:
                chunk.append(item)
                yield chunk
                chunk = []
        else:
            if not chunk and toknum == END_CHECK:  # token.N_TOKENS in 3.7
                continue

            chunk.append(item)


def get_str_bin_op_lines(code):
    for chunk in get_chunk(code):
        start = chunk[0][2][0]  # first line -> 2 idx is start -> is line
        end = chunk[-1][3][0]  # last line -> 3 idx is end -> is line

        last_toknum = None
        last_tokval = None
        found = False
        for toknum, tokval, *rest in chunk:
            if (
                toknum == 53
                and tokval == "%"
                and last_toknum == 3
                and "\\n" not in last_tokval
                and "\n" not in last_tokval
                and "%%" not in last_tokval
            ):
                found = True
            # punt if this happens
            elif found and toknum == 53 and tokval == ":":
                found = False  # punt on this (see django_noop7 test)
                break

            if not (toknum in (56, 58) and tokval == "\n"):  # 3.7 is 56...
                last_toknum = toknum
                last_tokval = tokval

        if found:
            yield (start, end)


def no_skipping(code):
    raw_code_lines = code.split("\n")
    no_skip_range = []
    scopes_by_idx = {}
    for positions in get_str_bin_op_lines(code):
        # for start, end in positions:
        if not positions:
            continue
        start, end = positions
        start_idx = start - 1
        raw_scope = raw_code_lines[start_idx:end]
        if not raw_scope:
            continue

        for line in raw_scope:
            if line:
                indent = get_indent(line)
                break

        strip_scope = map(lambda x: x.strip(), raw_scope)
        scopes_by_idx[start_idx] = dict(
            raw_scope=raw_scope,
            strip_scope=strip_scope,
            indent=indent,
        )
        no_skip_range += list(range(start_idx, end))
    return no_skip_range, scopes_by_idx


def rebuild_transformed_lines(code, indent):
    code_line_parts = code.strip().split("\n")
    code_block = ""
    for idx, cline in enumerate(code_line_parts):
        code_line_strip = cline.lstrip()  # if change_add else cline
        if idx == 0:
            code_block = indent + code_line_strip
        else:
            if (
                code_block.endswith(",")
                or code_block.endswith("else")
                or code_block.endswith("for")
                or code_block.endswith("in")
                or code_block.endswith("not")
            ):
                code_block += " "

            code_block += cline.strip()

    return code_block


def fstringify_code_by_line(code, stats=False, debug=False):
    raw_code_lines = code.split("\n")
    no_skip_range, scopes_by_idx = no_skipping(code)

    result_lines = []
    for line_idx, raw_line in enumerate(raw_code_lines):
        lineno = line_idx + 1

        if line_idx not in no_skip_range:
            result_lines.append(raw_line)
            continue

        if line_idx not in scopes_by_idx:
            continue

        scoped = scopes_by_idx[line_idx]
        code_line, meta = fstringify_code(
            "\n".join(scoped["strip_scope"]), include_meta=True, debug=debug
        )

        if not meta["changed"]:
            if debug:
                print("~~~~NOT CHANGED", scoped["raw_scope"], "meta", meta)
            result_lines += scoped["raw_scope"]
            continue

        code_line = force_double_quote_fstring(code_line)
        code_line_parts = code_line.strip().split("\n")

        indie = ""
        indent = scoped["indent"]
        indie = rebuild_transformed_lines(code_line, scoped["indent"])

        result_lines.append(indie)

    final_code = "\n".join(result_lines)
    return final_code


def skip_file(fn):
    """use tokenizer to make a fancier
        `"s%" not in contents`
    """
    # fn = io.BytesIO(fn.encode("utf-8")).readline
    with open(fn, "rb") as f:
        try:
            g = tokenize.tokenize(f.readline)
            for toknum, tokval, _, _, _ in g:
                if toknum == 53 and tokval == "%":
                    return False
        except tokenize.TokenError:
            pass

        return True
