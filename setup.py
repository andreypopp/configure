from setuptools import setup

version = "0.3.5"

setup(
    name="configure",
    version=version,
    description="configuration toolkit based on YAML",
    author="Andrey Popp",
    author_email="8mayday@gmail.com",
    packages=["configure"],
    test_suite="tests",
    zip_safe=False)
