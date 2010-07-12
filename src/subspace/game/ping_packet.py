from subspace.core.packet import Packet
from struct import unpack_from, calcsize

class PingPacket(Packet):
    _id = '' # ping packets have no "id" -- they ping and pong
    pass

class C2SSimplePing(PingPacket):
    _format = "I"
    _components = ["timestamp"]
    timestamp = 0

class S2CSimplePong(PingPacket):
    _format = "II"
    _components = ["total", "timestamp"]
    total = 0
    timestamp = 0