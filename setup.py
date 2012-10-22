from setuptools import setup

version = "0.4.7"

setup(
    name="configure",
    version=version,
    description="configuration toolkit based on YAML",
    author="Andrey Popp",
    author_email="8mayday@gmail.com",
    py_modules=["configure"],
    test_suite="tests",
    install_requires=["pyyaml"],
    zip_safe=False)
