
	#@bash -c "PYTHONPATH=. poetry run python fstringify/__init__.py ../haizhongwen"
	#@bash -c "PYTHONPATH=. poetry run python fstringify/__init__.py ../flask"
	#@bash -c "PYTHONPATH=. poetry run python fstringify/__init__.py ../django"
	#@bash -c "PYTHONPATH=. poetry run python fstringify/__init__.py --help"


test:
	@bash -c "PYTHONPATH=. poetry run python tests/test_fstringify.py"

citest:
	@bash -c "PYTHONPATH=. python tests/test_fstringify.py"

deploy: pip install twine wheel
	git tag $$(python setup.py -V)
	git push --tags
	python setup.py bdist_wheel
	python setup.py sdist
	echo 'pypi.org Username: '
	@read username && twine upload dist/* -u $$username;


run:
	@bash -c "PYTHONPATH=. poetry run python fstringify/__init__.py /home/jack/code/django/docs/_ext/djangodocs.py --verbose"
