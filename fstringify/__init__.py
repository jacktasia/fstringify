__version__ = "0.1.0"

import ast

import json
import pprint
import re

import astor

MOD_KEY_PATTERN = re.compile("(%\([^)]+\)s)")
MOD_KEY_NAME_PATTERN = re.compile("%\(([^)]+)\)s")


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
    if isinstance(node.right, (ast.Name, ast.Attribute)):
        return handle_from_mod_generic_name(node)

    elif isinstance(node.right, ast.Tuple):
        return handle_from_mod_tuple(node)

    elif isinstance(node.right, ast.Dict):
        print("~~~~ Dict mod strings don't make sense to f-strings")
        return node

    raise RuntimeError("Unexpected fstringify error")


class FstringifyTransformer(ast.NodeTransformer):
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
            and isinstance(node.right, (ast.Tuple, ast.Name, ast.Dict, ast.Attribute))
        )

        if do_change:
            return handle_from_mod(node)

        return node


def fstringify_node(node):
    return FstringifyTransformer().visit(node)


def fstringify_code(code):
    tree = ast.parse(code)
    converted = fstringify_node(tree)
    new_code = astor.to_source(converted)
    return new_code


def fstringify_file(fn):
    with open(fn) as f:
        new_code = fstringify_code(f.read())

    with open(fn + ".fs", "w") as f:
        f.write(new_code)


def pp_code_ast(code):
    """Pretty print code's AST to stdout.

    Args:
        code (str): The code you want the ast for.

    Returns nothing print AST representation to stdout
    """
    tree = ast.parse(code)
    converted = fstringify_node(tree)
    pp_ast(converted)


def main():
    print("fstringify", __version__)


if __name__ == "__main__":
    main()
