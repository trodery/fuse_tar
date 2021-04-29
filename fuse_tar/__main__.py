"""Main"""

from argparse import ArgumentParser, Namespace
import llfuse
from . import _init_logging, _getmount_point, TarFS

def _parseargs() -> Namespace:# {{{
  """
  Parse command line
  """

  parser = ArgumentParser(prog="tar_fuse")
  parser.add_argument('tarfile', type=str,
                      help='tarfile to mount')
  parser.add_argument('--mountpoint', type=str,
                      help='Where to mount the file system', default="")
  parser.add_argument('--create-missing-mount', action='store_false', default=False,
                      help='Create mount point if it doesn\'t exist')
  parser.add_argument('--debug', action='store_true', default=False,
                      help='Enable debugging output')
  parser.add_argument('--debug-fuse', action='store_true', default=False,
                      help='Enable FUSE debugging output')
  return parser.parse_args()
# }}}

def main() -> None:# {{{
  """
  main function
  """
  options = _parseargs()
  _init_logging(options.debug)

  mpath = _getmount_point(options.tarfile, options.mountpoint, create_missing_mount=options.create_missing_mount)
  tarfs = TarFS(options.tarfile)
  fuse_options = set(llfuse.default_options)
  fuse_options.add('fsname=fuse_tar')
  fuse_options.add('ro')
  if options.debug_fuse:
    fuse_options.add('debug')
  llfuse.init(tarfs, mpath, fuse_options)
  try:
    llfuse.main()
  except Exception as exc:
    llfuse.close(unmount=False)
    raise exc

  llfuse.close()
# }}}

if __name__ == '__main__':
  main()
