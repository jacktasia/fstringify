# fstringify

[![Build Status](https://travis-ci.org/jacktasia/fstringify.svg)](https://travis-ci.org/jacktasia/fstringify)

[![asciicast](https://asciinema.org/a/CDwLsZtWg3of1xSuAOfjnr6x8.png)](https://asciinema.org/a/CDwLsZtWg3of1xSuAOfjnr6x8)

**This is an alpha release. Do NOT use on uncommitted code!**

`fstringify` is a command line tool to automatically convert a project's Python code from old "%-formatted" strings into Python 3.6+'s "f-strings".

Here's a [complete diff running it against flask](https://github.com/pallets/flask/compare/master...jacktasia:fstringified).


### About

I mainly wanted an excuse to play with the built-in [AST](https://docs.python.org/3/library/tokenize.html) and [tokenze](https://docs.python.org/3/library/tokenize.html) modules. That said, f-strings are really cool. To quote Joanna Jablonski's great [f-string guide](https://realpython.com/python-f-strings/):

> Not only are they more readable, more concise, and less prone to error than other ways of formatting, but they are also faster!

### Installation

`fstringify` can be installed by running `pip install fstringify`.  It requires
Python 3.6.0+ to run and effectively turns the code it runs on into Python 3.6+,
since 3.6 is when "f-strings" were introduced.


### Usage

To run: `fstringify {source_file_or_directory}`


### Command line options
```
usage: fstringify [-h] [--verbose | --quiet] [--version] src

fstringify 0.x.x

positional arguments:
  src         source file or directory

optional arguments:
  -h, --help  show this help message and exit
  --verbose   run with verbose output
  --quiet     run without output
  --version   show version and exit

```

### Other Credits / Dependencies / Links

- [astor](https://github.com/berkerpeksag/astor) is used to turn the transformed AST back into code.
- [black](https://github.com/ambv/black) was a big inspiration, but is only used as a dependency for forcing double quotes when they are used as the input code.
