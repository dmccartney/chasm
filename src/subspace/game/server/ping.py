
from socket import socket,timeout,AF_INET,SOCK_DGRAM,SOL_SOCKET, SO_REUSEADDR
from select import select
from threading import Thread, Event, Lock
from logging import debug, warn
from Queue import Queue, Empty, Full
from time import time, sleep
from subspace.game.ping_packet import S2CSimplePong, C2SSimplePing

class PingZone:
    """
    This is where the clients can fetch player counts from the server.
    Most often, they'll query this when browsing the "zone list" in Continuum.
    This runs on zone port + 1 and is supposed to reply with the playercount.
    """
    def __init__(self, address, zone):
        self.MAX_PING_PACKET_SIZE = 512
        self._zone = zone
        self._server_socket = socket(AF_INET,SOCK_DGRAM)
        self._server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self._server_socket.bind(address)
        self._server_socket.setblocking(False)
        self.address = self._server_socket.getsockname()
        self._shutting_down = Event() # this is set to tell the threads to end
        self._threads = {
            "Server:Game:Ping" : Thread(target=self._receiving_loop,name="Server:Game:Ping"),
            }
        self._shutting_down = Event() # this is set to tell the threads to end
    
    def start(self):
        debug("starting ping server threads")
        for thread_name,thread in self._threads.iteritems():
            warn("Starting ping thread %s" % thread_name)
            thread.start()

    def shutdown(self):
        self._shutting_down.set()
        for thread_name,thread in self._threads.iteritems():
            warn("Closing thread %s" % thread_name)
            thread.join(3.0) # give it 3s to join
        
    def _receiving_loop(self):
        """ This polls the server socket for incoming packets. """
        while not self._shutting_down.is_set():
            rs,_,__ = select([self._server_socket],[],[],1.0)
            if len(rs) == 0:
                continue
            try:
                raw_packet, client_address = \
                        self._server_socket.recvfrom(self.MAX_PING_PACKET_SIZE)
            except timeout:
                continue
            raw_hex = ' '.join([x.encode("hex") for x in raw_packet])
            try:
                if len(raw_packet) < 4:
                    warn("improper packet length (len=%d) %s" %
                         (len(raw_packet), raw_hex))
                else:
                    p = C2SSimplePing(raw_packet)
                    self._send_pong(client_address, p.timestamp)
            except Exception as err:
                warn("Error receiving incoming ping packet %s" % raw_hex)
                warn("%s" % err)
                
    def _send_pong(self, client_address, timestamp):
        player_count = self._zone.player_count()
        p = S2CSimplePong(total=player_count, timestamp=timestamp)
        try:
            self._server_socket.sendto(p.raw(), client_address)
        except timeout:
            warn("ping socket send failure")

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG,
            format="%(levelname)-7.7s:<%(threadName)15.15s > %(message)s")
    from random import randint
    class Test_Zone:
        def player_count(self):
            return randint(0,255)
            
    ps = PingZone(("127.0.0.1", 5001), Test_Zone())
    ps.start()
    sleep(180)
    ps.shutdown()
