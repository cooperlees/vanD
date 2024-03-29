#!/usr/bin/env python3

from setuptools import find_packages, setup


ptr_params = {
    "entry_point_module": "vand/main",
    "test_suite": "vand.tests.base",
    "test_suite_timeout": 300,
    "required_coverage": {
        "vand/main.py": 40,
        "vand/li3.py": 50,
    },
    "run_black": True,
    "run_flake8": True,
    "run_mypy": True,
    "run_usort": True,
}


setup(
    name="vand",
    version="2023.11.18",
    description=("Daemon for all your Van Life needs ..."),
    packages=find_packages(),
    url="http://github.com/cooperlees/vanD/",
    author="Cooper Lees",
    author_email="me@cooperlees.com",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Development Status :: 3 - Alpha",
    ],
    entry_points={"console_scripts": ["vanD = vand.main:main"]},
    install_requires=["aiohttp", "aioprometheus[aiohttp]", "bleak", "bleson", "click"],
    test_require=["ptr"],
    python_requires=">=3.11",
    test_suite=ptr_params["test_suite"],
)
