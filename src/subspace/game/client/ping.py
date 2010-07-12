
from socket import socket,timeout,AF_INET,SOCK_DGRAM,SOL_SOCKET, SO_REUSEADDR
from select import select
from threading import Thread, Event, Lock
from logging import debug, warn
from Queue import Queue, Empty, Full
from time import time, sleep
from subspace.game.ping_packet import C2SSimplePing, S2CSimplePong

class PingPlayer:
    """
    This is the clients end of the ping protocol 
    """
    def __init__(self, address):
        self.MAX_PING_PACKET_SIZE = 512
        self._socket = socket(AF_INET,SOCK_DGRAM)
        try:
            self._socket.connect(address)
        except:
            warn("unable to connect socket to %r" % address)
            return
        self._socket.setblocking(True)
        self._socket.settimeout(3.0)
        self._socket.sendall(C2SSimplePing(timestamp=0).raw())
        for attempt in range(3):
            try:
                raw_packet = self._socket.recv(self.MAX_PING_PACKET_SIZE)
            except timeout:
                continue
            if len(raw_packet) > 0:
                p = S2CSimplePong(raw_packet)
                print p
                break

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG,
            format="%(levelname)-7.7s:<%(threadName)15.15s > %(message)s")
    pp = PingPlayer(("127.0.0.1", 5001))
    sleep(180)
    pp.shutdown()
