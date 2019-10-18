import ast
import re
import sys

assert sys.version_info >= (3, 6, 0), "fstringify requires Python 3.6+"
from pathlib import Path
from setuptools import setup

BASE_DIR = Path(__file__).parent


# forked from black's setup.py
def get_long_description():
    """Load README for long description"""
    readme_md = BASE_DIR / "README.rst"
    with open(readme_md, encoding="utf8") as readme_f:
        return readme_f.read()


# forked from black's setup.py
def get_version():
    """Use a regex to pull out the version"""
    fstringify_py = BASE_DIR / "fstringify/__init__.py"
    _version_re = re.compile(r"__version__\s+=\s+(?P<version>.*)")
    with open(fstringify_py, "r", encoding="utf8") as f:
        match = _version_re.search(f.read())
        version = match.group("version") if match is not None else '"unknown"'
    return str(ast.literal_eval(version))


def get_requirements():
    with open("requirements.txt", encoding="utf-8") as fp:
        return fp.read()


VERSION = get_version()

setup(
    name="fstringify",
    packages=["fstringify"],
    version=VERSION,
    description="CLI tool to convert a python project's old style strings to f-strings.",
    author="Jack Angers",
    author_email="jacktasia@gmail.com",
    url="https://github.com/jacktasia/fstringify",
    download_url="https://github.com/jacktasia/fstringify/tarball/" + VERSION,
    keywords=["utility", "strings"],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ],
    license="GNU General Public License v3.0",
    long_description=get_long_description(),
    install_requires=get_requirements(),
    entry_points={"console_scripts": ["fstringify=fstringify:main"]},
)
