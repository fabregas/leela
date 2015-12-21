import os
import sys
from setuptools import setup, find_packages

def getver():
    code = open(
        os.path.join(os.path.dirname(__file__), 'leela/__init__.py')).read()
    exec(code)
    return locals()['__version__']


if __name__ == '__main__':
    setup(
        name = "leela",
        version = getver(),
        author = "Kostiantyn Andrusenko",
        author_email = "kksstt@gmail.com",
        description = ("Leela web framework."),
        license = "http://www.apache.org/licenses/LICENSE-2.0",
        url = "https://github.com/fabregas/leela",
        download_url= "https://github.com/fabregas/leela/tarball/%s"%getver(),
        packages= find_packages('.'),
        package_dir={'leela': 'leela'},
        scripts=['./bin/leela', './bin/leela-worker'],
        classifiers = [],
        keywords = ["web", "asyncio"],
        install_requires=[
            'PyYAML',
            'aiohttp'],
    )

