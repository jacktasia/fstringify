import difflib
import os
import json
import unittest
import tokenize

from fstringify import fstringify_code, fstringify_file, fstringify_code_by_line

from fstringify.utils import get_indent, pp_code_ast
from fstringify.format import force_double_quote_fstring


# TODO: optional argument to inject comments of when found but can't apply


class FstringifyTest(unittest.TestCase):
    def assertCodeEqual(self, result, expected):
        if result != expected:
            df = difflib.unified_diff(expected.split("\n"), result.split("\n"))
            print("\nASSERT CODE EQUAL FAILED DIFF:")
            print("RESULT:")
            print(result)
            print("-------------------------------")
            for line_diff in df:
                if line_diff.strip() == "" or line_diff in ("--- \n", "+++ \n", "\n"):
                    continue
                print(line_diff)
            print("-------------------------------")

        self.assertTrue(result == expected)

    @staticmethod
    def tokenize_debug(code):
        pass
        # print(code)
        # print("---------------------------")
        # print(dump_tokenize(code))
        # print("---------------------------")

        # print(fstringify_code_by_line2(code))

        ###############
        # for x in get_str_bin_op_lines(code):
        #     print(x)
        # for x in get_chunk(code):
        #     if x:
        #         # print(x)
        #         result = tokenize.untokenize(x)

        #         if isinstance(result, bytes):
        #             result = result.decode("utf-8").rstrip()
        #         else:
        #             result = result.lstrip("\n\\")

        #         print(result)
        #         print("~~~~~~~~~~~~~!!!!!!!!!!!!!!", usable_chunk(result))
        # print("---------------------------")

    def test_mod_dict_name(self):
        code = """
        d = {"k": "blah"}
        b = "1+%(k)s" % d
        """
        expected = """
        d = {"k": "blah"}
        b = f"1+{d['k']}"
        """
        result = fstringify_code_by_line(code, debug=True)
        self.assertCodeEqual(result, expected)

    def test_mod_var_name(self):
        code = 'b = "1+%s+2" % a'
        expected = "b = f'1+{a}+2'\n"
        result = fstringify_code(code)
        self.assertCodeEqual(result, expected)

    def test_mod_str_literal(self):
        code = 'b = "1+%s+2" % "a"'
        expected = "b = f\"1+{'a'}+2\"\n"
        result = fstringify_code(code)
        self.assertCodeEqual(result, expected)

    def test_mod_tuple(self):
        code = 'b = "1+%s+2%s3" % (a, b)'
        expected = "b = f'1+{a}+2{b}3'\n"
        result = fstringify_code(code)
        self.assertCodeEqual(result, expected)

    def test_var_name_self(self):
        code = """
class Blah:

    def __init__(self):
        self.a = '1'
        self.b = '2'
        self.d = {'k': 'v'}

    def run(self):
        print('a val: %s' % self.a)
        print('a val: %s b val: %s' % (self.a, self.b))
        print('dk val: %(k)s' % self.d)
        asdf = 1
        print('damnf', 'asdf: %s' % asdf)
        print(
            "--NUMBERS"
            "numbers: %s" % (self.num)
        )
    """

        # self.tokenize_debug(code)
        expected = """
class Blah:

    def __init__(self):
        self.a = '1'
        self.b = '2'
        self.d = {'k': 'v'}

    def run(self):
        print(f"a val: {self.a}")
        print(f"a val: {self.a} b val: {self.b}")
        print(f"dk val: {self.d['k']}")
        asdf = 1
        print('damnf', f"asdf: {asdf}")
        print(f"--NUMBERSnumbers: {self.num}")
    """

        result = fstringify_code_by_line(code, debug=False)

        # print("expected\n", expected, "\nresult\n", result)

        self.assertCodeEqual(result, expected)

    # def test_write_file(self):
    #     # fn = os.path.join(os.path.dirname(__file__), "example.py")
    #     fn = "/home/jack/code/haizhongwen/server/gcs.py"
    #     fstringify_file(fn)

    def test_get_indent(self):
        self.assertCodeEqual("    ", get_indent("    code"))
        self.assertCodeEqual("", get_indent("code"))

    def test_force_double_quote_fstring(self):
        code = "    f'a val: {self.a} b val: {self.b}'"
        expected = '    f"a val: {self.a} b val: {self.b}"'
        self.assertCodeEqual(force_double_quote_fstring(code), expected)

    def test_force_double_quote_fstring_has_double(self):
        code = "f'a val: {self.a} \"b\" val: {self.b}'"
        expected = "f'a val: {self.a} \"b\" val: {self.b}'"
        self.assertCodeEqual(force_double_quote_fstring(code), expected)

    def test_force_double_quote_fstring_edge(self):
        code = "'asdf'"
        expected = "'asdf'"
        self.assertCodeEqual(force_double_quote_fstring(code), expected)

    def test_force_double_quote_fstring_edge2(self):
        code = "print('asdf')"
        expected = "print('asdf')"
        self.assertCodeEqual(force_double_quote_fstring(code), expected)

    # failing...
    def test_force_double_quote_fstring_edge3(self):
        code = "print('damnf', f'asdf: {asdf}')"
        expected = "print('damnf', f\"asdf: {asdf}\")"
        result = force_double_quote_fstring(code)

        self.assertCodeEqual(result, expected)

    def test_force_double_quote_fstring_edge4(self):
        code = "    print('damnf', f'asdf: {asdf}')"
        expected = "    print('damnf', f\"asdf: {asdf}\")"
        result = force_double_quote_fstring(code)

        self.assertCodeEqual(result, expected)

    def test_multi_line_self(self):
        code = """
class Foo:
    def __init__(self):
        self.a = '1'
        sys.exit(
            "Exiting due to receiving %d status code when expecting %d."
            % (r.status_code, expected_status)
        )
"""
        expected = """
class Foo:
    def __init__(self):
        self.a = '1'
        sys.exit(f"Exiting due to receiving {r.status_code} status code when expecting {expected_status}.")
"""

        result = fstringify_code_by_line(code)
        self.assertCodeEqual(result, expected)

    def test_noop(self):
        code = """
def cmd_test():
    # TODO: move this into its own functions
    ensure_hsk_data()
    data = get_quiz_data()
"""

        result = fstringify_code_by_line(code, debug=False)
        self.assertCodeEqual(result, code)

    def test_flask(self):
        code = """
        if view_func is not None:
            old_func = self.view_functions.get(endpoint)
            if old_func is not None and old_func != view_func:
                raise AssertionError('View function mapping is overwriting an '
                                     'existing endpoint function: %s' % endpoint)
            self.view_functions[endpoint] = view_func
"""

        expected = """
        if view_func is not None:
            old_func = self.view_functions.get(endpoint)
            if old_func is not None and old_func != view_func:
                raise AssertionError(f"View function mapping is overwriting an existing endpoint function: {endpoint}")
            self.view_functions[endpoint] = view_func
"""

        result = fstringify_code_by_line(code, debug=False)
        self.assertCodeEqual(result, expected)

    def test_flask2(self):
        code = """
        if isinstance(srcobj, Flask):
            src_info = 'application "%s"' % srcobj.import_name
        elif isinstance(srcobj, Blueprint):
            src_info = 'blueprint "%s" (%s)' % (srcobj.name,
                                                srcobj.import_name)
"""

        expected = """
        if isinstance(srcobj, Flask):
            src_info = f'application "{srcobj.import_name}"'
        elif isinstance(srcobj, Blueprint):
            src_info = f'blueprint "{srcobj.name}" ({srcobj.import_name})'
"""

        result = fstringify_code_by_line(code, debug=False)
        self.assertCodeEqual(result, expected)

    def test_django_noop(self):
        code = '''
def load_handler(path, *args, **kwargs):
    """
    Given a path to a handler, return an instance of that handler.

    E.g.::
        >>> from django.http import HttpRequest
        >>> request = HttpRequest()
        >>> load_handler('django.core.files.uploadhandler.TemporaryFileUploadHandler', request)
        <TemporaryFileUploadHandler object at 0x...>
    """
    return import_string(path)(*args, **kwargs)

'''
        result = fstringify_code_by_line(code, debug=False)
        self.assertCodeEqual(result, code)

    def test_django_noop2(self):
        code = """
    def invalid_block_tag(self, token, command, parse_until=None):
        if parse_until:
            raise self.error(
                token,
                "Invalid block tag on line %d: '%s', expected %s. Did you "
                "forget to register or load this tag?" % (
                    token.lineno,
                    command,
                    get_text_list(["'%s'" % p for p in parse_until], 'or'),
                ),
            )
"""
        result = fstringify_code_by_line(code, debug=False)
        self.assertCodeEqual(result, code)

    def test_django_noop3(self):
        code = """
    def __str__(self):
        token_name = self.token_type.name.capitalize()
        return ('<%s token: "%s...">' %
                (token_name, self.contents[:20].replace('\\n', '')))
"""

        result = fstringify_code_by_line(code, debug=False)
        self.assertCodeEqual(result, code)

    def test_django_noop4(self):
        code = """
        print("this is new line: %s" % "\\n")
"""

        result = fstringify_code_by_line(code, debug=False)
        self.assertCodeEqual(result, code)

    def test_django_noop5(self):
        code = """
        print("this is new line: %s" % "\\\\")
"""

        result = fstringify_code_by_line(code, debug=False)
        self.assertCodeEqual(result, code)

    def test_django_noop6(self):
        code = """
        if invalid_params:
            raise exceptions.FieldError(
                "Invalid field name(s) for model %s: '%s'." % (
                    self.model._meta.object_name,
                    "', '".join(sorted(invalid_params)),
                ))
"""

        result = fstringify_code_by_line(code, debug=False)
        self.assertCodeEqual(result, code)

    def test_django_noop7(self):
        code = """
        # to be join-less and smaller. Refs #21760.
        if remote_field.is_hidden() or len(self.field.foreign_related_fields) == 1:
            query = {'%s__in' % related_field.name: {instance_attr(inst)[0] for inst in instances}}
        else:
            query = {'%s__in' % self.field.related_query_name(): instances}
        queryset = queryset.filter(**query)
"""

        result = fstringify_code_by_line(code, debug=False, stats=True)
        # self.assertEqual(meta["changes"], 0)
        self.assertCodeEqual(result, code)

    def test_django_noop8(self):
        code = """
    hint = "\n\tHINT: %s" % self.hint if self.hint else ''
"""

        result = fstringify_code_by_line(code, debug=False, stats=True)

        self.assertCodeEqual(result, code)

    def test_django_noop9(self):
        code = """
    hint = "HINT: %s" % self.hint if self.hint else ''
"""

        result = fstringify_code_by_line(code, debug=False, stats=True)

        self.assertCodeEqual(result, code)

    def test_django_op_10(self):
        code = """
hint = "HINT: %s" % (self.hint if self.hint else '')
"""
        # pp_code_ast(code)
        result = fstringify_code_by_line(code, debug=False, stats=True)

        self.assertCodeEqual(result, code)


    def test_preceding_line_is_blank(self):
        code = """
def write_row(self, xf, row, row_idx):

    attrs = {'r': '%d' % row_idx}
        """
        expected = """
def write_row(self, xf, row, row_idx):
    attrs = {'r': f"{row_idx}"}
        """
        result = fstringify_code_by_line(code, debug=False, stats=True)

        self.assertCodeEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
