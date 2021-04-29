#!/usr/bin/env python3
"""
fuse_tar.py

Copyright © 2020 Marek Lukaszuk <m.lukaszuk@gmail.com>

A simple read-only Fuse filesystem based on a compressed (or not) Tar archive
This work may be distributed under the terms of the GNU LGPL.
"""

__version__ = "1.0.1"
__author__ = "m.lukaszuk@gmail.com"

# http://pythonhosted.org/llfuse/example.html
# https://github.com/python-llfuse/python-llfuse

import sys
import errno
import logging
import os
import stat
import time
from typing import Any, Iterator, Tuple, Optional
from distutils.version import LooseVersion

import tarfile

try:
  import faulthandler
except (ModuleNotFoundError, ImportError):
  pass
else:
  faulthandler.enable()

# works with version llfuse +1.3
try:
  import llfuse  # type: ignore
except (ModuleNotFoundError, ImportError):
  print("please install llfuse python module, version +1.3.0"+\
      "possible command: python3 -m pip install llfuse")
  sys.exit(1)

# Check llfuse version is >= 1.3.0
llfuse_version = LooseVersion(llfuse.__version__)
llfuse_minimum_version = LooseVersion("1.3.0")
assert llfuse_version >= llfuse_minimum_version, \
  f"fuse_tar requires llfuse>=1.3.0 but you have llfuse=={llfuse.__version__}"

log = logging.getLogger(__name__)


def _get_tarfile_mode(filename: str) -> str:
  if filename.lower().endswith("gz"):
    return "r:gz"
  elif filename.lower().endswith("bz2"):
    return "r:bz2"
  elif filename.lower().endswith("xz"):
    return "r:xz"
  return "r"


# TarFS {{{
class TarFS(llfuse.Operations):  # type: ignore
  """
  Read Only FuseFS backedup by compressed (or not) Tar archive
  """
  def __init__(self, tarname: str) -> None:  # {{{
    """
    """
    super(TarFS, self).__init__()

    tarmode = _get_tarfile_mode(tarname)
    self.tar = tarfile.open(tarname, mode=tarmode)

    # size used later in statfs syscall for df
    self.whole_size: int = os.stat(tarname).st_size

    # inodes numbers are indexes from tar.getnames() + 1
    self.delta: int = llfuse.ROOT_INODE + 1

    # max inode value, if we get something higher we don't need to check anything
    self.max_inode: int = len(self.tar.getnames()) + self.delta

  # }}}

  def getattr(
      self,
      inode: int,
      ctx: llfuse.RequestContext = None  # pylint: disable=unused-argument
  ) -> llfuse.EntryAttributes:  # {{{
    """
    get inode attributes
    """
    entry = llfuse.EntryAttributes()

    stamp: float
    # root inode attributes
    if inode == llfuse.ROOT_INODE:
      entry.st_mode = (stat.S_IFDIR | 0o755)
      entry.st_size = 0
      stamp = int(time.time() * 1e9)

    # parameters for inodes inside the tar file
    elif inode < self.max_inode:
      tar_inode = self.tar.getmembers()[inode - self.delta]

      # setting proper mode based on the type of the inode
      entry.st_mode = 0
      if tar_inode.isdir():
        entry.st_mode = stat.S_IFDIR
      elif tar_inode.isreg():
        entry.st_mode = stat.S_IFREG
      elif tar_inode.islnk():
        entry.st_mode = stat.S_IFLNK
      elif tar_inode.issym():
        entry.st_mode = stat.S_IFLNK
      elif tar_inode.isfifo():
        entry.st_mode = stat.S_IFIFO
      elif tar_inode.ischr():
        entry.st_mode = stat.S_IFCHR
      entry.st_mode |= tar_inode.mode

      # inode size
      entry.st_size = tar_inode.size

      # we will use mtime for atime and ctime also
      stamp = (tar_inode.mtime * 1e9)
    else:
      raise llfuse.FUSEError(errno.ENOENT)

    entry.st_atime_ns = stamp
    entry.st_ctime_ns = stamp
    entry.st_mtime_ns = stamp
    entry.st_gid = os.getgid()
    entry.st_uid = os.getuid()
    entry.st_ino = inode

    # because this is read-only FS we can set timeouts to large values
    entry.attr_timeout = 3600
    entry.entry_timeout = 3600

    return entry

  # }}}

  def lookup(
      self,
      parent_inode: int,
      name: bytes,
      ctx: llfuse.RequestContext = None  # pylint: disable=unused-argument
  ) -> llfuse.EntryAttributes:  # {{{
    """
    lookup inode / idx number
    """

    # parent_inode needs to be lower then max_inode
    assert parent_inode < self.max_inode

    # special case of '.' inode
    if name == b'.':
      return self.getattr(parent_inode)

    # special case of '..' inode
    idx = parent_inode - self.delta
    if name == b'..':
      # we get the name of the folder above
      p_path = os.path.split(self.tar.getnames()[idx])[0]
      # knowing the name we find the index for it in the list
      idx = self.tar.getnames().index(p_path)
      # index + delta is our inode number
      return self.getattr(idx + self.delta)

    # special case of ROOT inode
    if parent_inode == llfuse.ROOT_INODE:
      prefix = ""

    else:
      prefix = self.tar.getnames()[idx]

    idx = 0
    for fname in self.tar.getnames():
      if os.path.split(fname)[0] == prefix and\
          name == os.path.basename(fname).encode('utf-8'):
        return self.getattr(idx + self.delta)
      idx += 1
    raise llfuse.FUSEError(errno.ENOENT)

  # }}}

  def opendir(self, inode: int, ctx: llfuse.RequestContext) -> int:  # {{{ pylint: disable=unused-argument
    """
    open/enter dir
    """

    if inode == llfuse.ROOT_INODE:
      return inode

    if inode < self.max_inode:
      idx = inode - self.delta
      if self.tar.getmembers()[idx].isdir():
        return inode

    raise llfuse.FUSEError(errno.ENOENT)

  # }}}

  def readdir(self, inode: int,
              off: int) -> Iterator[Tuple[bytes, Any, int]]:  # {{{
    """
    list/read dir
    """
    if inode == llfuse.ROOT_INODE:
      prefix = ""
    else:
      idx = inode - self.delta
      prefix = self.tar.getnames()[idx]

    idx = 1
    for fname in self.tar.getnames():
      if os.path.split(fname)[0] == prefix:
        if idx > off:
          yield (os.path.basename(fname).encode('utf-8'),
                 self.getattr(idx - 1 + self.delta), idx)
      idx += 1

  # }}}

  def open(self, inode: int, flags: int, ctx: llfuse.RequestContext) -> int:  # {{{ pylint: disable=unused-argument,no-self-use
    """
    open file
    """
    return inode

  # }}}

  def read(self, fhandle: int, off: int, size: int) -> Any:  # {{{
    """
    read file
    """
    idx: int = fhandle - self.delta
    fname: Any = self.tar.extractfile(self.tar.getnames()[idx])
    fname.seek(off)
    return fname.read(size)

  # }}}

  def statfs(self, ctx: llfuse.RequestContext) -> llfuse.StatvfsData:  # {{{ pylint: disable=unused-argument
    """
    to make output of df nicer
    man 2 statvfs
    """
    stfs = llfuse.StatvfsData()
    stfs.f_bavail = 0
    stfs.f_bfree = 0
    stfs.f_blocks = self.whole_size
    stfs.f_bsize = 4096
    stfs.f_favail = 0
    stfs.f_ffree = 0
    stfs.f_files = self.max_inode
    stfs.f_frsize = 1

    return stfs

  # }}}


# }}}


def _init_logging(debug: bool = False) -> None:  # {{{
  """
  logging handler for fuse
  """
  formatter = logging.Formatter(
      '%(asctime)s.%(msecs)03d %(threadName)s: '
      '[%(name)s] %(message)s',
      datefmt="%Y-%m-%d %H:%M:%S")
  handler = logging.StreamHandler()
  handler.setFormatter(formatter)
  root_logger = logging.getLogger()
  if debug:
    handler.setLevel(logging.DEBUG)
    root_logger.setLevel(logging.DEBUG)
  else:
    handler.setLevel(logging.INFO)
    root_logger.setLevel(logging.INFO)
  root_logger.addHandler(handler)


# }}}


def _getmount_point(
    path_to_tarfile: str,
    mount_path: str,
    create_missing_mount: Optional[bool] = False) -> str:  # {{{
  """Verify if the mount point exists and is correct.

  Args:

    path_to_tarfile (str): Path to tar file to mount.
    mount_path (str): Path to mount tar file.
    create_missing_mount (Optional[bool]): Create missing mount point. Defaults to False.

  Raises:

    Exception: If mount location is invalid.

  Returns:

    str: Mount location.
  """

  mpath = mount_path

  if mpath == "":
    ext: str
    (mpath, ext) = os.path.splitext(path_to_tarfile)
    if ext != "" and mpath != "":
      if not os.path.exists(mpath):
        if create_missing_mount:
          os.mkdir(mpath)
          return mpath
        raise Exception(f"Mount point '{mount_path}' does not exist!")

      if os.path.isdir(mpath):
        return mpath
      raise Exception(f"Mount point '{mount_path}' is not a directory!")

    raise Exception("Please specify a correct mountpoint")
  return mpath


# }}}
