import os
import sys
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

if __name__ == '__main__':
    setup(
        name = "leela",
        version = read('VERSION'),
        author = "Fabregas",
        author_email = "kksstt@gmail.com",
        description = ("Leela web framework."),
        license = "APACHE V2",
        url = "",
        packages= find_packages('.'),
        package_dir={'leela': 'leela'},
        scripts=['./bin/leela', './bin/leela-worker'],
        long_description=read('README.md'),
        install_requires=[
            'aiohttp',
            'asyncio_mongo'
        ],
    )

