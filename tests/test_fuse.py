"""Test the fuse bits"""

import logging
import multiprocessing
import os
import pathlib
import sys
import threading

import llfuse
import pytest
from fuse_tar import TarFS

from util import cleanup, fuse_test_marker, umount, wait_for_mount, sha1sum

pytestmark = fuse_test_marker()

items = [
    ('tarfile1.tar', '513.txt', 514,
     'dde18dafb16622dee24c63e54531c65d8675afef'),
    ('tarfile1.tar', '10241.txt', 10242,
     '9340f4c0e495862b8d9a62a44e604896a047713a'),
    ('tarfile1.tar', 'dir1/file1.txt', 10,
     '8dfd2dbf199f4a18c121532c261de6e7dbc5bd31'),
    ('tarfile1.tar', 'dir1/file2.txt', 10,
     '2ae5b479319444ab14e493acd1c60c46e10a564e'),
]


@pytest.fixture
def testfs(request, tmpdir):
  """Does the multiprocessing handling so that the filesystem
  can be mounted and tested against simultaneously"""

  tar_filename = items[request.param][0]
  directory_path = str(pathlib.Path(__file__).parent.absolute())
  tar_fullpath = f"{directory_path}/{tar_filename}"
  tmp_dir = tmpdir

  # We can't use forkserver because we have to make sure
  # that the server inherits the per-test stdout/stderr file
  # descriptors.
  if hasattr(multiprocessing, 'get_context'):
    mp = multiprocessing.get_context('fork')
  else:
    # Older versions only support *fork* anyway
    mp = multiprocessing
  if threading.active_count() != 1:
    raise RuntimeError("Multi-threaded test running is not supported")

  mnt_dir = str(tmp_dir)
  with mp.Manager() as mgr:
    cross_process = mgr.Namespace()
    mount_process = mp.Process(target=run_fs,
                               args=(mnt_dir, cross_process, tar_fullpath))

    mount_process.start()
    try:
      wait_for_mount(mount_process, mnt_dir)
      yield (mnt_dir, cross_process, items[request.param])
    except:
      cleanup(mnt_dir)
      raise
    else:
      umount(mount_process, mnt_dir)


@pytest.mark.parametrize('testfs', [0, 1, 2, 3],
                         ids=[
                             'tarfile1.tar-513.txt', 'tarfile1.tar-10241.txt',
                             'tarfile1.tar-dir1/file1.txt',
                             'tarfile1.tar--dir1/file2.txt'
                         ],
                         indirect=True)
def test_correct_read_file_contents(testfs):
  """Test that we correctly read the contents of a file"""

  (mnt_dir, _, things) = testfs
  (_, member_filename, expected_size, expected_sha1) = things
  print(f"{mnt_dir=}")
  path = os.path.join(mnt_dir, member_filename)
  print(f"{path=}")

  observed_size = os.stat(path).st_size
  assert observed_size == expected_size, \
    f"Expected file size to be {expected_size} bytes but is actually {observed_size} bytes for file '{member_filename}'"

  f = open(path, mode='r', encoding='utf-8')
  data = f.read()
  f.close()

  observed_read_size = len(data)
  assert observed_read_size == expected_size, \
    f"Expected file size when reading contents to be {expected_size} bytes but is actually {observed_read_size} bytes for file '{member_filename}'"

  observed_sha1 = sha1sum(data.encode('ascii'))
  assert observed_sha1 == expected_sha1, \
    f"Expected file to has sha1 of {expected_sha1} but is actually {observed_sha1} for file '{member_filename}'"


class Fs(TarFS):
  """Wrapper around TarFS so we can capture the multiprocessing process"""
  def __init__(self, tarname: str, cross_process):
    super(Fs, self).__init__(tarname)
    self.status = cross_process
    self.status.lookup_called = False


def run_fs(mountpoint: str, cross_process, path_to_tar: str):
  """Run the Filesystem"""
  # Logging (note that we run in a new process, so we can't
  # rely on direct log capture and instead print to stdout)

  os.makedirs(mountpoint, exist_ok=True)
  root_logger = logging.getLogger()
  formatter = logging.Formatter(
      '%(asctime)s.%(msecs)03d %(levelname)s '
      '%(funcName)s(%(threadName)s): %(message)s',
      datefmt="%M:%S")
  handler = logging.StreamHandler(sys.stdout)
  handler.setLevel(logging.DEBUG)
  handler.setFormatter(formatter)
  root_logger.addHandler(handler)
  root_logger.setLevel(logging.DEBUG)

  tarfs = Fs(path_to_tar, cross_process)
  fuse_options = set(llfuse.default_options)
  fuse_options.add('fsname=fuse_tar')
  fuse_options.add('ro')
  fuse_options.add('debug')
  llfuse.init(tarfs, mountpoint, fuse_options)
  try:
    llfuse.main(workers=1)
  finally:
    llfuse.close()
