
	#@bash -c "PYTHONPATH=. poetry run python fstringify/__init__.py ../haizhongwen"
	#@bash -c "PYTHONPATH=. poetry run python fstringify/__init__.py ../flask"
	#@bash -c "PYTHONPATH=. poetry run python fstringify/__init__.py ../django"
	#@bash -c "PYTHONPATH=. poetry run python fstringify/__init__.py --help"


test:
	@bash -c "PYTHONPATH=. poetry run python tests/test_fstringify.py"

citest:
	@bash -c "PYTHONPATH=. python tests/test_fstringify.py"
	
install-dev:
	pip install -r requirements-dev.txt

deploy:
	pip install twine wheel
	git tag $$(python setup.py -V)
	git push --tags
	python setup.py bdist_wheel
	python setup.py sdist
	echo 'pypi.org Username: '
	@read username && twine upload dist/* -u $$username;

clean:
	@bash -c "rm -rf build/"
	@bash -c "rm -rf dist/"
	@bash -c "rm -rf fstringify.egg-info"

redeploy:
	python setup.py bdist_wheel
	python setup.py sdist
	echo 'pypi.org Username: '
	@read username && twine upload dist/* -u $$username;


run:
	@bash -c "PYTHONPATH=. poetry run python fstringify/__init__.py /home/jack/code/django/docs/_ext/djangodocs.py --verbose"
