from twisted.protocols import basic
from twisted.internet import defer, protocol
from twisted.python import log
from StringIO import StringIO

# Stolen from memcached protocol
try:
    from collections import deque
except ImportError:
    class deque(list):
        def popleft(self):
            return self.pop(0)

class Command(object):

    def __init__(self, command, **kwargs):
        self.command = command
        self._deferred = defer.Deferred()
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return "<Command: %s>" % self.command

    def success(self, value):
        self._deferred.callback(value)

    def fail(self, status, msg):
        # XXX:  Need proper exception classes used here.
        self._deferred.errback(Exception(msg))

class ELock(basic.LineReceiver):
    """The elock protocol."""

    def __init__(self):
        self._current = deque()

    def __cmd(self, command, full_command, *args, **kwargs):
        self.sendLine(full_command)
        cmdObj = Command(command, **kwargs)
        self._current.append(cmdObj)
        return cmdObj._deferred

    def lock(self, name, timeout=None):
        """Acquire a lock."""
        cmd="lock " + name
        if timeout:
            cmd += " " + timeout
        return self.__cmd('lock', cmd)

    def unlock(self, name):
        "Release a lock"
        return self.__cmd('unlock', "unlock " + name)

    def __is_success(self, status):
        return status == 200

    def lineReceived(self, line):
        status, msg = line.split(' ', 1)
        status=int(status)
        cmd = self._current.popleft()
        if self.__is_success(status):
            cmd.success(msg)
        else:
            cmd.fail(status, msg)
