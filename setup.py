import os
import sys
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

if __name__ == '__main__':
    setup(
        name = "leela",
        version = read('VERSION'),
        author = "Kostiantyn Andrusenko",
        author_email = "kksstt@gmail.com",
        description = ("Leela web framework."),
        license = "http://www.apache.org/licenses/LICENSE-2.0",
        url = "https://github.com/fabregas/leela",
        download_url= "https://github.com/fabregas/leela/tarball/%s"%read('VERSION'),
        packages= find_packages('.'),
        package_dir={'leela': 'leela'},
        scripts=['./bin/leela', './bin/leela-worker'],
        classifiers = [],
        keywords = ["web", "asyncio"],
        install_requires=[
            'PyYAML',
            'aiohttp',
            'asyncio_mongo'
        ],
    )

