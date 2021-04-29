# pylint: disable=missing-docstring,exec-used,undefined-variable

from setuptools import setup

__version__ = "1.0.1"

# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
  name='fuse_tar',
  version=__version__,
  description='A simple FuseFS read-only filesystem backed up by a Tar file',
  author='Marek Lukaszuk',
  author_email='m.lukaszuk@gmail.com',
  url='https://github.com/mmmonk/fuse_tar',
  license='GPLv3',
  long_description=long_description,
  long_description_content_type="text/markdown",
  python_requires='>=3.6',
  keywords='fuse tar',
  classifiers=[
    'Development Status :: 5 - Production/Stable',
    'Operating System :: POSIX :: Linux',
    'Intended Audience :: End Users/Desktop',
    'Environment :: Console',
    'Topic :: System :: Filesystems',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
  ],
  install_requires=[
      'llfuse>=1.3.0'
  ],
  tests_requires=[
      'pytest',
      'pytest-cov',
      'pytest-ordering',
      'pytest-pylint',
  ],
  entry_points = {
      'console_scripts': ['fuse_tar=fuse_tar.__main__:main'],
  }
)
