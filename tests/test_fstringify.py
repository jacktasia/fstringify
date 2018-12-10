import difflib
import os
import json
import unittest


from fstringify import (
    __version__,
    main,
    fstringify_code,
    pp_code_ast,
    fstringify_file,
    fstringify_code_by_line,
    get_indent,
)

from fstringify.utils import force_double_quote_fstring

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

    def test_version(self):
        self.assertEqual(__version__, "0.1.0")

    def test_mod_dict_name(self):
        code = """
        d = {"k": "blah"}
        b = "1+%(k)s" % d
        """
        expected = """
        d = {"k": "blah"}
        b = f"1+{d['k']}"
        """
        result = fstringify_code_by_line(code)
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


if __name__ == "__main__":
    unittest.main()
