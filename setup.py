#!/usr/bin/env python3

from setuptools import find_packages, setup


ptr_params = {
    "entry_point_module": "vand/main",
    "test_suite": "vand.tests.base",
    "test_suite_timeout": 300,
    "required_coverage": {
        "vand/main.py": 45,
        "vand/li3.py": 30,
    },
    "run_black": True,
    "run_flake8": True,
    "run_mypy": True,
    "run_usort": True,
}


setup(
    name="vand",
    version="2022.1.29",
    description=("Daemon for all your Van Life needs ..."),
    packages=find_packages(),
    url="http://github.com/cooperlees/vanD/",
    author="Cooper Lees",
    author_email="me@cooperlees.com",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Development Status :: 3 - Alpha",
    ],
    entry_points={"console_scripts": ["vanD = vand.main:main"]},
    install_requires=["aiohttp", "aioprometheus[aiohttp]", "bleak", "click"],
    test_require=["ptr"],
    python_requires=">=3.9",
    test_suite=ptr_params["test_suite"],
)
