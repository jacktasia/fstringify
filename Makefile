

test:
	@bash -c "PYTHONPATH=. poetry run python tests/test_fstringify.py"

run:
	#@bash -c "PYTHONPATH=. poetry run python fstringify/__init__.py ../haizhongwen"
	# @bash -c "PYTHONPATH=. poetry run python fstringify/__init__.py ../flask"
	@bash -c "PYTHONPATH=. poetry run python fstringify/__init__.py ../django"
