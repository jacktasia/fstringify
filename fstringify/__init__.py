__version__ = "0.1.0"

import ast
import json
import pprint
import re
import os
import sys

import astor

from fstringify.utils import force_double_quote_fstring


MOD_KEY_PATTERN = re.compile("(%\([^)]+\)s)")
MOD_KEY_NAME_PATTERN = re.compile("%\(([^)]+)\)s")
INDENT_PATTERN = re.compile("^(\ +)")


def ast_to_dict(node):
    """Convert an AST node to a dictionary for debugging.

    This is mainly for powering `pp_ast` (pretty printing).

    derived from `jsonify_ast` here:
    https://github.com/maligree/python-ast-explorer/blob/master/parse.py#L7

    Args:
       node (AST): the ast to turn into debug dict


    Returns a dictionary.
    """
    fields = {}
    classname = lambda cls: cls.__class__.__name__
    for k in node._fields:
        v = getattr(node, k)
        if isinstance(v, ast.AST):
            if v._fields:
                fields[k] = ast_to_dict(v)
            else:
                fields[k] = classname(v)

        elif isinstance(v, list):
            fields[k] = []
            for e in v:
                fields[k].append(ast_to_dict(e))

        elif isinstance(v, (str, int, float)):
            fields[k] = v

        elif v is None:
            fields[k] = None

        else:
            fields[k] = str(v)

    return {classname(node): fields}


def pp_ast(node):
    """Pretty print an AST to stdout"""
    print(json.dumps(ast_to_dict(node), indent=2))


def handle_from_mod_dict_name(node):
    """Convert a `BinOp` `%` formatted str with a name representing a Dict on the right to an f-string.

    Takes an ast.BinOp representing `"1. %(key1)s 2. %(key2)s" % mydict`
    and converted it to a ast.JoinedStr representing `f"1. {mydict['key1']} 2. {mydict['key2']}"`

    Args:
       node (ast.BinOp): The node to convert to a f-string

    Returns ast.JoinedStr (f-string)
    """

    format_str = node.left.s
    matches = MOD_KEY_PATTERN.findall(format_str)
    var_keys = []
    for idx, m in enumerate(matches):
        var_key = MOD_KEY_NAME_PATTERN.match(m)
        if not var_key:
            raise ValueError("could not find dict key")
        var_keys.append(var_key[1])

    # build result node
    result_node = ast.JoinedStr()
    result_node.values = []
    var_keys.reverse()
    blocks = MOD_KEY_PATTERN.split(format_str)
    # loop through the blocks of a string to build up dateh JoinStr.values
    for block in blocks:
        # if this block matches a %(arg)s pattern then inject f-string instead
        if MOD_KEY_PATTERN.match(block):
            fv = ast.FormattedValue(
                value=ast.Subscript(
                    value=node.right, slice=ast.Index(value=ast.Str(s=var_keys.pop()))
                ),
                conversion=-1,
                format_spec=None,
            )

            result_node.values.append(fv)
        else:
            # no match means it's just a literal string
            result_node.values.append(ast.Str(s=block))
    return result_node


def handle_from_mod_tuple(node):
    """Convert a `BinOp` `%` formatted str with a tuple on the right to an f-string.

    Takes an ast.BinOp representing `"1. %s 2. %s" % (a, b)`
    and converted it to a ast.JoinedStr representing `f"1. {a} 2. {b}"`

    Args:
       node (ast.BinOp): The node to convert to a f-string

    Returns ast.JoinedStr (f-string)
    """

    format_str = node.left.s
    var_pattern = "(%[a-z])"  # TODO: compile
    matches = re.findall(var_pattern, format_str)

    if len(node.right.elts) != len(matches):
        raise ValueError("string formatting length mismatch")

    str_vars = list(map(lambda x: x, node.right.elts))

    # build result node
    result_node = ast.JoinedStr()
    result_node.values = []
    str_vars.reverse()
    blocks = re.split(var_pattern, format_str)
    for block in blocks:
        if re.match(var_pattern, block):
            fv = ast.FormattedValue(
                value=str_vars.pop(), conversion=-1, format_spec=None
            )
            result_node.values.append(fv)
        else:
            result_node.values.append(ast.Str(s=block))

    return result_node


def handle_from_mod_generic_name(node):
    """Convert a `BinOp` `%` formatted str with a unknown name on the `node.right` to an f-string.

    When `node.right` is a Name since we don't know if it's a single var or a dict so we sniff the string.

    `"val: %(key_name1)s val2: %(key_name2)s" % some_dict`
    Sniffs the left string for Dict style usage and calls: `handle_from_mod_dict_name`

    `"val: %s" % some_var`
    Borrow the core logic by injecting the name into a ast.Tuple

    Args:
       node (ast.BinOp): The node to convert to a f-string

    Returns ast.JoinedStr (f-string)
    """

    has_dict_str_format = MOD_KEY_PATTERN.findall(node.left.s)
    if has_dict_str_format:
        return handle_from_mod_dict_name(node)

    # if it's just a name then pretend it's tuple to use that code
    node.right = ast.Tuple(elts=[node.right])
    return handle_from_mod_tuple(node)


def handle_from_mod(node):
    if isinstance(node.right, (ast.Name, ast.Attribute, ast.Str)):
        return handle_from_mod_generic_name(node)

    elif isinstance(node.right, ast.Tuple):
        return handle_from_mod_tuple(node)

    elif isinstance(node.right, ast.Dict):
        # print("~~~~ Dict mod strings don't make sense to f-strings")
        return node

    raise RuntimeError("unexpected `node.right` class")


class FstringifyTransformer(ast.NodeTransformer):
    def __init__(self):
        super().__init__()
        self.counter = 0
        self.lineno = -1
        self.col_offset = -1

    def visit_BinOp(self, node):
        """Convert `ast.BinOp` to `ast.JoinedStr` f-string

        Currently only if a string literal `ast.Str` is on the left side of the `%`
        and one of `ast.Tuple`, `ast.Name`, `ast.Dict` is on the right

        Args:
            node (ast.BinOp): The node to convert to a f-string

        Returns ast.JoinedStr (f-string)
        """

        do_change = (
            isinstance(node.left, ast.Str)
            and isinstance(node.op, ast.Mod)
            and isinstance(node.right, (ast.Tuple, ast.Name, ast.Attribute, ast.Str))
            # ignore ast.Dict on right
        )

        # bail in these edge cases...
        for ch in ast.walk(node.right):
            # no nested binops!
            if isinstance(ch, ast.BinOp):
                return node
            # f-string expression part cannot include a backslash
            if isinstance(ch, ast.Str) and any(
                map(lambda x: x in ch.s, ("\n", "\t", "\r"))
            ):
                return node

        if do_change:
            self.counter += 1
            self.lineno = node.lineno
            self.col_offset = node.col_offset
            result_node = handle_from_mod(node)
            return result_node

        return node


def fstringify_node(node):
    ft = FstringifyTransformer()
    result = ft.visit(node)
    return (
        result,
        dict(
            changed=ft.counter > 0,
            lineno=ft.lineno,
            col_offset=ft.col_offset,
            skip=True,
        ),
    )


def fstringify_code(code, include_meta=False, debug=False):
    # skip = False
    converted = None
    meta = dict(changed=False, lineno=1, col_offset=0, skip=True)

    code_strip = code.strip()

    if code_strip == "" or code_strip.startswith("#"):
        meta["skip"] = True
        return code, meta if include_meta else code

    try:
        tree = ast.parse(code)
        # if debug:
        #     pp_ast(tree)
        converted, meta = fstringify_node(tree)
    except SyntaxError as e:
        meta["skip"] = code.rstrip().endswith(":")
    except Exception as e2:
        meta["skip"] = False

    if meta["changed"] and converted:
        new_code = astor.to_source(converted)
        if include_meta:
            return new_code, meta
        return new_code

    if include_meta:
        return code, meta
    return code


def get_indent(line):
    indented = INDENT_PATTERN.match(line)
    if indented:
        return indented[0]

    return ""


def trim_list(l):
    last = l.pop()
    l.pop()
    l.append(last)
    return l


def trim_list_until(l, length):
    if len(l) > 1 and length == 1:
        return [l[0]]

    while len(l) > length:
        l = trim_list(l)

    filler = l[-1] if l else ""
    while len(l) < length:
        l.append(filler)
    return l


def fstringify_code_by_line(code, debug=False):
    result = []
    scope = []
    raw_scope = []
    comments = {}
    use_indented = []
    do_add = False
    change_add = False
    in_doc_string = False
    last_line_strip = ""
    raw_code_lines = code.split("\n")

    for line_idx, raw_line in enumerate(raw_code_lines):
        lineno = line_idx + 1
        indented = get_indent(raw_line)
        raw_line_strip = raw_line.strip()

        if not in_doc_string and last_line_strip.startswith("def "):
            in_doc_string = raw_line_strip.startswith(
                '"""'
            ) or raw_line_strip.startswith("'''")
            if in_doc_string:
                result.append(raw_line)
                last_line_strip = raw_line
                continue

        elif in_doc_string:
            result.append(raw_line)
            if raw_line_strip.endswith("'''") or raw_line_strip.endswith('"""'):
                in_doc_string = False
            last_line_strip = raw_line
            continue

        scope.append(raw_line.strip())
        raw_scope.append(raw_line)

        if raw_line_strip.startswith("#"):
            comments[len(scope) - 1] = raw_line
        else:
            use_indented.append(indented)

        code_line, meta = fstringify_code(
            "\n".join(scope), include_meta=True, debug=debug
        )

        if meta["changed"]:
            code_line = force_double_quote_fstring(code_line)
            change_add = True
            do_add = True
        elif meta["skip"]:
            do_add = True
        elif line_idx == len(raw_code_lines) - 1:
            do_add

        if debug:
            print(
                ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
                f"{lineno}"
                ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
            )
            print("___RAW___")
            print(raw_line)
            print("___META___")
            print("\t", meta)
            print("___INDENT___", "\n\t", len(indented))
            print("___CHANGE___", "\n\t", change_add)
            print("___ADD___   ", "\n\t", do_add)
            if change_add:
                print("___RESULT___")
                print(code_line)

        if do_add:
            if change_add:
                code_line_parts = code_line.strip().split("\n")
            else:
                code_line_parts = raw_scope

            use_indented = trim_list_until(use_indented, len(code_line_parts))

            if change_add:
                for k, v in comments.items():
                    if debug:
                        print("k", k, type(k), "v", v, "comments", comments)

                    # in case the comments are contained within a bin op
                    if k >= len(code_line_parts) or code_line_parts[k] != v:
                        code_line_parts.insert(k, v)
                        use_indented.insert(k, get_indent(v))

            indie = ""
            for idx, cline in enumerate(code_line_parts):
                indent = use_indented[idx] if change_add else ""
                code = cline.lstrip() if change_add else cline
                if idx == 0:
                    indie = indent + code
                else:
                    if indie.endswith(",") or indie.endswith("else"):
                        indie += " "
                    indie += cline.strip()

                if not change_add:
                    result.append(indent + code)

            if change_add:
                result.append(indie)

            if debug:
                print("___INSERTED___")
                if not change_add:
                    print("\n".join(result[: len(code_line_parts) * -1]))
                else:
                    print(indie)

            change_add = False
            comments = {}
            scope = []
            raw_scope = []
            use_indented = []
            do_add = False
        last_line_strip = raw_line_strip

    return "\n".join(result)


def fstringify_file(fn):
    with open(fn) as f:
        contents = f.read()

    if "%" not in contents:
        return False

    new_code = fstringify_code_by_line(contents)

    if new_code == contents:
        return False

    # with open(fn + ".fs", "w") as f:
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

    for f in files:
        file_path = os.path.join(f[0], f[1])
        print("Applying", file_path)
        fstringify_file(file_path)

    return "Done."


def pp_code_ast(code):
    """Pretty print code's AST to stdout.

    Args:
        code (str): The code you want the ast for.

    Returns nothing print AST representation to stdout
    """
    tree = ast.parse(code)
    converted, _ = fstringify_node(tree)
    pp_ast(converted)


def main():
    if len(sys.argv) == 1:
        print("fstringify", __version__)
        sys.exit(0)

    src_path = sys.argv[1]

    fstringify_dir(src_path)


if __name__ == "__main__":
    main()
