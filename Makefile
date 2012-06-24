test install build develop:
	python setup.py $@

upload:
	python setup.py sdist upload

docs::
	$(MAKE) -C ./docs html
