__version__ = "0.1.0"

import ast

import json
import pprint
import re

import astor

MOD_KEY_PATTERN = re.compile("(%\([^)]+\)s)")
MOD_KEY_NAME_PATTERN = re.compile("%\(([^)]+)\)s")
INDENT_PATTERN = re.compile("^(\W+)")


def ast_to_dict(node):
    """Convert an AST node to a dictionary for debugging.

    This is mainly for powering `pp_ast` (pretty printing).

    Forked from:
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
        print("~~~~ Dict mod strings don't make sense to f-strings")
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
            and isinstance(
                node.right, (ast.Tuple, ast.Name, ast.Dict, ast.Attribute, ast.Str)
            )
        )

        if do_change:
            self.counter += 1
            self.lineno = node.lineno
            self.col_offset = node.col_offset
            print(
                "lineno",
                node.lineno,
                "coloffset",
                node.col_offset,
                "id",
                node.left.s,
                "node right coloffset",
                node.right.col_offset,
            )
            # pp_ast(node.left)
            # pp_ast(node.right)
            result_node = handle_from_mod(node)
            return result_node

        return node


def fstringify_node(node):
    ft = FstringifyTransformer()
    result = ft.visit(node)
    # print("counter", ft.counter)
    return (result, (ft.counter > 0, ft.lineno, ft.col_offset))
    # return FstringifyTransformer().visit(node)


def fstringify_code(code, include_meta=False):
    tree = ast.parse(code)
    converted, meta = fstringify_node(tree)
    if meta[0]:
        new_code = astor.to_source(converted)
        print("converting..........", code, "->", new_code)
        if include_meta:
            return new_code, meta
        return new_code

    if include_meta:
        return code, (False, -1, -1)
    return code


# def inject_after_indent(line, to_inject):
#     indented = INDENT_PATTERN.match(line)
#     if indented:
#         return indented[0] + to_inject + line.lstrip()

#     return to_inject + line


def get_indent(line):
    indented = INDENT_PATTERN.match(line)
    if indented:
        return indented[0]

    return ""


# def force_double_quote_fstring(code):
#     print("~~~~~~~~~ GOT", code)
#     indented = get_indent(code)
#     strip_code = code.strip()
#     if not strip_code.startswith("f'"):
#         return code

#     if len(strip_code) < 3:
#         return code

#     contents = strip_code[2:-1]
#     if '"' not in contents:
#         return indented + 'f"' + contents + '"'

#     return code


def force_double_quote_fstring(code, meta=None):
    if "f'" in code:
        other = code.find("f'")
        start = meta[2] or other if meta else other
        print("~~~~~~~~start", start, "other", other)
        end = code.rfind("'")
        if start + 1 < end:  # f at the end of the'asdf'
            prefix = code[:start]
            suffix = code[end + 1 :]
            contents = code[start + 2 : end]
            if '"' not in contents:
                return prefix + 'f"' + contents + '"' + suffix

    return code


def fstringify_code_by_line(code):
    result = []
    line = None
    for raw_line in code.split("\n"):
        if line:
            line += "\n" + raw_line
        else:
            line = raw_line

        try:
            # indented = INDENT_PATTERN.match(line)
            indented = get_indent(line)

            code_line, meta = fstringify_code(line.strip(), include_meta=True)
            if meta[0]:
                # meta[2] = meta[2]
                result_line = indented + force_double_quote_fstring(code_line, meta)
                result.append(result_line.rstrip())
                line = None
            else:
                result.append(line)
                line = None
        except SyntaxError as e:
            if line.rstrip().endswith(":"):
                result.append(line)
                line = None
        except Exception as e2:
            # print(e)
            result.append(line)
            line = None

    return "\n".join(result)


def fstringify_file(fn):
    with open(fn) as f:
        new_code = fstringify_code_by_line(f.read())

    # with open(fn + ".fs", "w") as f:
    with open(fn, "w") as f:
        f.write(new_code)


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
    print("fstringify", __version__)


if __name__ == "__main__":
    main()
