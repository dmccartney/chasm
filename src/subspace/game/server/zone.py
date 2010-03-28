"""
TODO: actually implement game.Zone
This implements a subspace game zone atop the subspace core protocol.
(for now it just sets up the server and responds negatively to every c2s Login)
"""
from subspace.core import server
from subspace.game import c2s_packet, s2c_packet
from time import sleep
from logging import debug, warn
from threading import Thread, Event, Lock
from Queue import Empty

class Zone:
    
    def __init__(self,address):
        # this will contain all registered packet handlers
        # the lock protects this from adds/gets during _receiving_loop 
        self._packet_handlers_lock = Lock()
        self._packet_handlers = {}
        
        self._local_packet_handlers = {
            c2s_packet.Login._id             : self._handle_login,
            #c2s_packet.OtherGreenPickup._id : self._handle_other_green_pickup,
            }
        self.add_packet_handlers(**self._local_packet_handlers)
        
        self._conn = server.Server(address)
        self._shutting_down = Event()
        self._threads = {
            "recv"  : Thread(target=self._receiving_loop,name="Zone:recv")
            }
        self._threads["recv"].start()

    def _receiving_loop(self):
        while not self._shutting_down.is_set():
            try:
                address, raw_packet = self._conn.recv(timeout=1.0)
            except Empty:
                continue
            if raw_packet is None: # core spits out None to signal disconnect
                warn("%s:%d hung up on us" % address)
                continue
            packet_id = raw_packet[0]
            with self._packet_handlers_lock:
                handlers = self._packet_handlers.get(packet_id,[])[:]
                # we make a copy of this packet's handlers so we can unlock
            if len(handlers) < 1:
                warn("unhandled game packet (len=%d) %s" % (len(raw_packet),
                           ' '.join([x.encode("hex") for x in raw_packet])))
            else:
                for hnd in handlers: 
                    hnd(address,raw_packet)

    def add_packet_handlers(self,**new_packet_handlers):
        """
        This permits other classes to register as a handler for a specified 
        game packet.  Internally, it adds all id:func entries from new_handlers
        to the table of packet handlers for type id, contained at key=id in
        self._packet_handlers.
        """
        with self._packet_handlers_lock:
            for id, fn in new_packet_handlers.iteritems():
                self._packet_handlers.setdefault(id,[]).append(fn)
    
    def _handle_login(self,address,raw_packet):
        p = c2s_packet.Login(raw_packet)
        debug("%s is trying to login" % p.name.rstrip('\x00'))
        self._conn.send(address,s2c_packet.LoginResponse(response=2)) # bad pwd
    
    def shutdown(self):
        self._shutting_down.set()
        debug("closing threads")
        for thread_name, thread in self._threads.iteritems():
            thread.join(3.0) # give each thread 3s to join
        self._conn.shutdown()

def main():
    import logging
    from random import randint
    from subspace.game.client.player import Player
    logging.basicConfig(level=logging.DEBUG,
        format="<%(threadName)25.25s > %(message)s")
    # creates zone, attempts 10 player logins
    # all are inspected and rejected, until Zone is properly implemented
    z = Zone(("127.0.0.1",5000))
    p = {}
    for i in range(10):
        p[i] = Player("divtest"+str(i),"password",("127.0.0.1",5000))
        p[i].login(timeout=0) 
    sleep(5)
    for i in range(10):
        if p[i].arena_entered.is_set():
            print i,"login success"
            p[i].logout()
        else:
            print i,"login failure"
            p[i].logout()
    sleep(1)
    z.shutdown()

if __name__ == '__main__':
    main()