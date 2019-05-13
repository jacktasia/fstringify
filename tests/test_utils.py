from fstringify.utils import (
    get_lines,
    get_indent,
)


def test_get_lines():
    code = """
    def write_row(self, xf, row, row_idx):

        attrs = {'r': '%d' % row_idx}
            """

    lines = get_lines(code)
    assert lines == [
        '',
        '    def write_row(self, xf, row, row_idx):',
        '',
        "        attrs = {'r': '%d' % row_idx}"
    ]


def test_get_indent():
    line = "        attrs = {'r': '%d' % row_idx}"
    result = get_indent(line)
    assert result == "        "

