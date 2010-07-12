"""
This provides a set of readable classes for creating and accessing subspace
packets.  This module does not do encryption or protocol logic.  It just 
exposes the components of the packets. (Note: I use the term "components" to 
refer to the members of the unpackaged packet, e.g. "key" and "version" are the
components of the Connect packet.)

This module gives specific detail to the core subspace packets.  Core packets 
on the wire begin with byte 0x00, followed by the core packet id. 
The controlling protocol for these core packets is implemented in 
subspace.core.net.

This module enables you to load a received packet by initializing it with the
raw packet data:

>>> raw_packet_data = "\x00\x06\x38\x90\x0d\x00\x3f\x42\x0f\x00"
>>> p = packet.SyncResponse(raw_packet_data)
>>> p.server_time
999999
>>> p.last_sync
888888

Or you can create new packets by initializing a packet with the components as
labeled arguments:

>>> p = packet.SyncResponse(last_sync=888888,server_time=999999)
>>> p.raw()
'\x00\x06\x38\x90\x0d\x00\x3f\x42\x0f\x00'

As shown above, once created, a packet's raw form is provided by calling raw().
Any changes made to the packet will be reflected in subsequent calls to raw():

>>> raw_packet_data = "\x00\x06\x38\x90\x0d\x00\x3f\x42\x0f\x00"
>>> p = packet.SyncResponse(raw_packet_data)
>>> p.last_sync = 0
>>> p.raw()
'\x00\x06\x00\x00\x00\x00\x3f\x42\x0f\x00'

Some of the core packets make use of a "tail" of variable sized data.  This 
tail is included in the output from raw().  And it is accessible as 
packet.tail. As an example, packet.Chunk contains a piece of a larger packet.
So the Chunk packet has only a header that reveals nothing except that its 
contents are, in fact, a Chunk to be stored.  So the tail of Chunk contains the
rest of the data that should be saved by the handler. And so it is: see its
controlling logic in subspace.core.socket.Client._handle_chunk.

For a nice view of a packet, simply print it (or call str() on it): 

>>> p = packet.Connect(key=0x12345678,version=0x0001)
>>> print p
CorePacket.Connect(_id=0x01):
    .key: 305419896
    .version: 1
raw:
00 01 78 56 34 12 01 00

"""
from struct import calcsize, unpack_from, pack
from logging import debug, warn

class Packet(object):
    """
    Known implementing subclasses:
     subspace.core.packet.CorePacket    : subspace socket packets
     subspace.game.s2c_packet.S2CPacket : packets from game server to client
     subspace.game.c2s_packet.C2SPacket : packets from client to game server 
     subspace.billing.packet.S2BPacket  : packets from game server to billing
     subspace.billing.packet.B2SPacket  : packets from billing server to game
    """
    # subclasses might overwrite these
    _prefix = ''        # prepended (e.g. core _prefix = '\x00', others are '')
    _id = '\x00'        # the packet ID, first byte (after _prefix)
    _format = ""        # struct.pack format (excluding first 2 bytes)
    _components = []    # labels for the components of this packet 
    # note: _components are paired with the results of unpacking using _format
    
    # subclasses should be careful with tail.  It is part of raw().
    tail = b''
    
    def __init__(self,raw_data=None,**components):
        """ 
        This creates the packet.  If raw_data is provided it will be loaded. 
        Then any specified components will be set.  Thus specified components
        override those contained in the raw_data.
        """
        if raw_data is not None: # if raw_data supplied, unpack and use it
            format = self._all_format()
            self.tail = raw_data[calcsize(format):]
            try:
                values = unpack_from(format,raw_data)
            except:
                warn("unable to unpack (len=%d) %s \n using (len=%d) %s" % \
                     (len(raw_data),' '.join(x.encode("hex") for x in raw_data),
                      calcsize(format),format))
                return
            if len(self._prefix) > 0:
                values = values[len(self._prefix):] # self._prefix
            values = values[len(self._id):] # self._id
            components.update(dict(zip(self._components,values)))
        self.__dict__.update(components)

    def _all_format(self):
        """ Return the full format string for pack/unpack. """
        fmt = "<"
        # really, these if's are superfluous, but it improves readability
        if len(self._id) > 0:
            fmt += ("B" * len(self._id))
        if len(self._prefix) > 0:
            fmt += ("B" * len(self._prefix))
        return fmt + self._format

    def _all_values(self):
        """ Return the full list of values to be packed/unpacked. """
        v = [ord(x) for x in (self._prefix + self._id)]
        v.extend([getattr(self,k) for k in self._components])
        return v

    def raw(self):
        """ This returns the raw packet data, for transmission. """
        try:
            result = pack(self._all_format(),*self._all_values()) + self.tail
        except:
            warn("unable to pack %s (format=%s)" % \
                 (self.__class__.__name__,
                  self._all_format(),))
            result = ''
        return result

    def __str__(self):
        """ This gives a more helpful view of the packet and its innards. """
        s = self.__class__.__name__+"\n"
        if len(self._prefix) > 0:
            s += "_prefix=0x%02X; " % ord(self._prefix)
        if len(self._id) > 0:
            s += "._id=0x%02X, len=%d\n" % (ord(self._id),len(self.raw()))
        else:
            s += "len=%d\n" % (len(self.raw()))
        s += '\traw: ' 
        s += ' '.join([x.encode("hex") for x in self.raw()])
        if len(self._components) > 0:
            s += '\n'
            s += '\n'.join(['\t'+self.__class__.__name__+'.'+k+': '+ \
                        str(getattr(self,k)) for k in self._components])
        return s

class CorePacket(Packet):
    """ This is a core packet, with a prefix of 0x00. """
    _prefix = '\x00'

class Connect(CorePacket):
    _id = '\x01'
    _format = "iH"
    _components = ["key","version"]
    key = 0xFFFFFFFF
    version = 0x0001

class ConnectResponse(CorePacket):
    _id = '\x02'
    _format = "i"
    _components = ["server_key"]
    server_key = 0xFFFFFFFF

class Reliable(CorePacket):
    _id = '\x03'
    _format = "I"
    _components = ["seq"]
    seq = 0

class ReliableACK(CorePacket):
    _id = '\x04'
    _format = "I"
    _components = ["seq"]
    seq = 0

class Sync(CorePacket):
    """ 
    Sync and SyncResponse operate like Ping and Pong.  Either side can send a
    Sync packet containing the sender's time and packet data.  The other side
    should then respond with a SyncResponse repeating the received time from
    the Sync packet, but also include their own time.
    """
    _id = '\x05'
    _format = "III"
    _components = ["sender_time","packets_sent","packets_received"]
    sender_time = 0
    packets_sent = 0
    packets_received = 0

class SyncResponse(CorePacket):
    _id = '\x06'
    _format = "II"
    _components = ["remote_time","sender_time"]
    remote_time = 0
    sender_time = 0

class Disconnect(CorePacket):
    _id = '\x07'

class Chunk(CorePacket):
    _id = '\x08'

class ChunkTail(CorePacket):
    _id = '\x09'

class StreamRequest(CorePacket):
    _id = '\x0A'
    _format = "I"
    _components = ["total_length"]
    total_length = 0

class StreamCancelRequest(CorePacket):
    _id = '\x0B'

class StreamCancelRequestACK(CorePacket):
    _id = '\x0C'

class Cluster(CorePacket):
    _id = '\x0E'

# continuum sends
class _ContEncResponse(CorePacket):
    _id = '\x10'
    _format = "II"
    _components = ["key1", "key2"]
    unknown = ""
    key1 = 0
    key2 = 0

class _ContEncResponseACK(CorePacket):
    _id = '\x11'
    _format = "I"
    _components = ["key1"]
    key1 = 0

def main():
    d = "00 06 6b 33 01 00 4f df 17 78"
    d = ''.join([b.decode('hex') for b in d.split()])
    p = SyncResponse(d)
    print p

if __name__ == '__main__':
    main()