import os
import unittest


from fstringify import __version__, main, fstringify_code, pp_code_ast


class FstringifyTest(unittest.TestCase):
    def test_version(self):
        self.assertEqual(__version__, "0.1.0")

    def test_mod_dict_name(self):
        code = """d = {"k": "blah"}
b = "1+%(k)s" % d
"""
        expected = """d = {'k': 'blah'}
b = f"1+{d['k']}"
"""

        result = fstringify_code(code)
        self.assertEqual(result, expected)

    def test_mod_var_name(self):
        code = 'b = "1+%s+2" % a'
        expected = "b = f'1+{a}+2'\n"
        result = fstringify_code(code)

        self.assertEqual(result, expected)

    def test_mod_tuple(self):
        code = 'b = "1+%s+2%s3" % (a, b)'
        expected = "b = f'1+{a}+2{b}3'\n"

        result = fstringify_code(code)

        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
