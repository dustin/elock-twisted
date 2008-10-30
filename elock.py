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

class ResourceLocked(Exception): pass

class NotLocked(Exception): pass

class NotResumable(Exception): pass

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
        exceptions={
            ('lock', 409): ResourceLocked,
            ('unlock', 403): NotLocked}
        e=exceptions.get((self.command, status), Exception)
        print "Adding exception", e(msg)
        self._deferred.errback(e(msg))

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

    def stats(self):
        "Get the stats."
        return self.__cmd('stats', 'stats', stats={}, inProgress=False)

    def __is_success(self, status):
        return status == 200

    def __read_status(self, line):
        status, msg = line.split(' ', 1)
        return int(status), msg


    def __received_stat(self, cmd, line):
        if cmd.inProgress:
            if line == 'END':
                self._current.popleft()
                cmd.success(cmd.stats)
            else:
                s, k, v = line.split(' ', 2)
                cmd.stats[k] = v
        else:
            status, msg = self.__read_status(line)
            if self.__is_success(status):
                cmd.inProgress = True
            else:
                self._current.popleft()
                cmd.fail(status, msg)

    def lineReceived(self, line):
        cmd = self._current[0]
        if cmd.command == 'stats':
            self.__received_stat(cmd, line)
        else:
            self._current.popleft()
            status, msg = self.__read_status(line)
            if self.__is_success(status):
                cmd.success(msg)
            else:
                cmd.fail(status, msg)
