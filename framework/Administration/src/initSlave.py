#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       initSlave.py
#       
#       Copyright 2012 dominique hunziker <dominique.hunziker@gmail.com>
#       
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#       
#       

# twisted specific imports
from twisted.python import log
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.defer import Deferred, DeferredList

# Python specific imports
import os, sys

# Custom imports
import settings
from Comm.UIDClient import UIDClientFactory

class LoggerProtocol(ProcessProtocol):
    """ Simple ProcessProtocol which forwards the stdout of the subprocesses to the
        stdout of this process in a orderly fashion.
    """
    _STOP_ESCALATION = [ ( 'INT',    5),
                         ('TERM',    1),
                         ('KILL', None) ]
    
    def __init__(self, termDeferred):
        """ Initialize the LoggerProtocol.
        """
        self._buff = ''
        self._termDeferred = termDeferred
        self._escalation = 0
        self._stopCall = None
 
    def outReceived(self, data):
        """ Callback which is called by twisted when new data has arrived from subprocess.
        """
        self._buff += data
        lines = [line for line in self._buff.split('\n')]
        self._buff = lines[-1]
        
        for line in lines[:-1]:
            log.msg(line)
 
    def processEnded(self, reason):
        """ Callback which is called by twisted when the subprocess has ended.
        """
        if reason.value.exitCode != 0:
            log.msg(reason)
            
        self._escalation = -1
        
        if self._stopCall:
            self._stopCall.cancel()
        
        self._termDeferred.callback()
    
    def terminate(self, reactor):
        """ Method which is used to terminate the underlying process.
        """
        if self._escalation != -1:
            escalation = self._STOP_ESCALATION[self._escalation]
            self.transport.signalProcess(escalation[0])
            
            if escalation[1]:
                self._escalation += 1
                reactor.callLater(self.terminate, escalation[1], reactor)

def main(reactor):
    log.startLogging(sys.stdout)
    
    deferred = Deferred()
    
    containerDeferred = Deferred()
    containerProtocol = LoggerProtocol(containerDeferred)
    satelliteDeferred = Deferred()
    satelliteProtocol = LoggerProtocol(satelliteDeferred)
    termDeferreds = DeferredList([containerDeferred, satelliteDeferred])
    
    def callback(suffix):
        cmd = [ os.path.join(settings.ROOT_DIR, 'framework/Administration/src/Container.py'),
                suffix ]
        reactor.spawnProcess(containerProtocol, cmd[0], cmd, env=os.environ) # uid=0, gid=0
        
        cmd = [ os.path.join(settings.ROOT_DIR, 'framework/Administration/src/Satellite.py'),
                suffix,
                settings.IP_MASTER ]
        reactor.spawnProcess(satelliteProtocol, cmd[0], cmd, env=os.environ, uid=1000, gid=1000)
    
    def errback(errMsg):
        log.msg(errMsg)
        print errMsg
        reactor.stop()
    
    deferred.addCallbacks(callback, errback)
    
    reactor.connectTCP(settings.IP_MASTER, settings.PORT_UID, UIDClientFactory(deferred))
    
    def shutdown():
        containerProtocol.terminate(reactor)
        satelliteProtocol.terminate(reactor)
        return termDeferreds
    
    reactor.addSystemEventTrigger('before', 'shutdown', shutdown)
    
    reactor.run()

if __name__ == '__main__':
    from twisted.internet import reactor
    main(reactor)
