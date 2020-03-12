from setuptools import setup
from fakemod._version import __version__

with open('README.md', 'rb') as fid:
    LONG_DESCRIPTION = fid.read().decode('utf8')

setup(
    name='fakemod',
    version=__version__,
    author='Roger D. Serwy',
    author_email='roger.serwy@gmail.com',
    license="BSD License",
    keywords="reload module",
    url="http://github.com/serwy/fakemod",
    packages=['fakemod'],
    description='Reloadable Modules and Namespace Packages',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    platforms=["Windows", "Linux", "Solaris", "Mac OS-X", "Unix"],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
    ],
)
