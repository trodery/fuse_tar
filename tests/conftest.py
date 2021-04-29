import pytest
import time
import gc

# Enable output checks
pytest_plugins = ('pytest_checklogs')


# Register false positives
@pytest.fixture(autouse=True)
def register_false_checklog_pos(reg_output):

  # DeprecationWarnings are unfortunately quite often a result of indirect
  # imports via third party modules, so we can't actually fix them.
  reg_output(r'(Pending)?DeprecationWarning', count=0)

  # Valgrind output
  reg_output(r'^==\d+== Memcheck, a memory error detector$')
  reg_output(
      r'^==\d+== For counts of detected and suppressed errors, rerun with: -v')
  reg_output(r'^==\d+== ERROR SUMMARY: 0 errors from 0 contexts')


def pytest_addoption(parser):
  group = parser.getgroup("general")
  group._addoption("--installed",
                   action="store_true",
                   default=False,
                   help="Test the installed package.")

  group = parser.getgroup("terminal reporting")
  group._addoption(
      "--logdebug",
      action="append",
      metavar='<module>',
      help="Activate debugging output from <module> for tests. Use `all` "
      "to get debug messages from all modules. This option can be "
      "specified multiple times.")


# If a test fails, wait a moment before retrieving the captured
# stdout/stderr. When using a server process, this makes sure that we capture
# any potential output of the server that comes *after* a test has failed. For
# example, if a request handler raises an exception, the server first signals an
# error to FUSE (causing the test to fail), and then logs the exception. Without
# the extra delay, the exception will go into nowhere.
@pytest.mark.hookwrapper
def pytest_pyfunc_call(pyfuncitem):
  outcome = yield
  failed = outcome.excinfo is not None
  if failed:
    time.sleep(1)


# Run gc.collect() at the end of every test, so that we get ResourceWarnings
# as early as possible.
def pytest_runtest_teardown(item, nextitem):
  gc.collect()
