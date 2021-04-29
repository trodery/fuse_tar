"""Test fuse_tar"""

# pylint: disable=line-too-long,import-outside-toplevel

import pytest


@pytest.mark.parametrize("filename,expected_mode", [
    ('tarfile1.tar', 'r'),
    ('tarfile1.tar.gz', 'r:gz'),
    ('tarfile1.tar.bz2', 'r:bz2'),
    ('tarfile1.tar.xz', 'r:xz'),
    ('tarfile1.tgz', 'r:gz'),
    ('tarfile1.tbz2', 'r:bz2'),
    ('tarfile1.txz', 'r:xz'),
])
def test_mode_for_filename(filename, expected_mode):
  """Test that we get the proper mode depending upon filename"""

  from fuse_tar import _get_tarfile_mode

  observed_mode = _get_tarfile_mode(filename)

  assert observed_mode == expected_mode, \
    f"Expected mode '{expected_mode}' but got mode '{observed_mode}' for '{filename}'"


@pytest.mark.parametrize(
    "path_to_tarfile,mount_path,create_missing_mount,expected_mount_path", [
        ('/home/user/tarfile1.tar', '/mnt/tarfile1', False, '/mnt/tarfile1'),
    ])
def test_getmount_point_exists(path_to_tarfile, mount_path,
                               create_missing_mount, expected_mount_path):
  """Test getmount_point"""

  from fuse_tar import _getmount_point

  observed_mount_path = _getmount_point(path_to_tarfile, mount_path,
                                        create_missing_mount)

  assert observed_mount_path == expected_mount_path, \
    f"Expected mount path '{expected_mount_path}' but observed mount path '{observed_mount_path}' for '{path_to_tarfile}'"


@pytest.mark.parametrize(
    "path_to_tarfile,mount_path,create_missing_mount,expected_mount_path", [
        ('/home/user/tarfile1.tar', '', False, '/home/user/tarfile1'),
    ])
def test_getmount_point_does_not_exist(path_to_tarfile, mount_path,
                                       create_missing_mount,
                                       expected_mount_path):  # pylint: disable=unused-argument
  """Test getmount_point where mount point does not exist"""

  from fuse_tar import _getmount_point

  with pytest.raises(Exception,
                     match="Mount point '' does not exist!") as exc_info:

    _ = _getmount_point(path_to_tarfile, mount_path, create_missing_mount)

  assert exc_info.type is Exception, f"Unexpected Exception type raised {exc_info.type}"
