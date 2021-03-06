#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import os
import sys
sys.path.append("..")
sys.path.append(os.path.join(sys.path[0], '..'))

from twisted.internet import reactor, protocol, defer, task

import elock

def print_cb(name):
    def f(val):
        print name, `val`
    return f

def worker(e):
    l=[]
    l.append(e.lock("test").addCallback(
        print_cb("Acquired lock: test")).addErrback(
        print_cb("Failed to acquire lock")))
    l.append(e.stats().addCallback(
        print_cb("Stats")).addErrback(
        print_cb("Failed to get stats")))
    l.append(e.unlock("test").addCallback(
        print_cb("Released lock: test")).addErrback(
        print_cb("Failed to release lock")))
    l.append(e.unlock("not_locked").addCallback(
        print_cb("Released lock: not_locked")).addErrback(
        print_cb("Failed to release lock not_locked")))
    l.append(e.unlock_all().addCallback(
        print_cb("Released all locks")).addErrback(
        print_cb("Failed to release all locks")))
    return defer.DeferredList(l)

d=protocol.ClientCreator(reactor, elock.ELock).connectTCP(sys.argv[1], 11400)
d.addCallback(worker).addBoth(lambda x: reactor.stop())

reactor.run()

