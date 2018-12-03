import os
import unittest


from fstringify import __version__, main, fstringify_code, pp_code_ast, fstringify_file


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

    def test_mod_var_name_self(self):
        code = """class Blah:

    def __init__(self):
        self.a = '1'
        self.b = '2'

    def run(self):
        print('a val: %s' % self.a)
        print('a val: %s b val: %s' % (self.a, self.b))
"""
        expected = """class Blah:

    def __init__(self):
        self.a = '1'
        self.b = '2'

    def run(self):
        print(f'a val: {self.a}')
        print(f'a val: {self.a} b val: {self.b}')
"""

        # pp_code_ast(code)
        result = fstringify_code(code)
        self.assertEqual(result, expected)

    # def test_write_file(self):
    #     fn = os.path.join(os.path.dirname(__file__), "example.py")
    #     fstringify_file(fn)


if __name__ == "__main__":
    unittest.main()
