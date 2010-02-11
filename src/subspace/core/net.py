"""
This module implements the core protocol used by subspace atop UDP.

net.Client and net.Server handle all core UDP packets (i.e. those beginning
with \x00).  Any other packets, e.g. subspace.billing.packet or 
subspace.game.packet, are queued for another class to handle via .recv() or
to emit via .send().

For details on how this fiddles with packets, see subspace.core.packet.  This 
module implements the controlling logic for these core packets.

"""
from subspace.core import packet
from subspace.core.encryption import VIE
from subspace.core.util import now
from socket import socket,AF_INET,SOCK_DGRAM,timeout
from threading import Thread, Lock, Event
from Queue import Queue, Empty
from time import time, sleep
from logging import warn
from subspace.game import c2s_packet

MAX_PACKET_SIZE = 512 # we grab up to this many bytes from the socket at a time
QUEUE_SIZE_IN = 500 # the number of incoming packets to queue before dropping 
QUEUE_SIZE_OUT = 500 # same, but for outgoing packets
SYNC_PERIOD = 5.0 # seconds between Sync's (see _sync)
RELIABLE_TIMEOUT_RESEND = 5.0 # seconds between reliable resends

class Server(object):
    """
    This is a server using the subspace core protocol.
    TODO: implement the server end of core.
    """
    def __init__(self):
        pass

class Client(object):
    """
    This is a client socket that implements the subspace core protocol.
    
    It blocks to connect on initialization.
    
    >>> c = subspace.core.socket.Client(("localhost",5000))
    >>> c.send(packet,reliable=True)
    >>> response = c.recv()
    
    send() is threadsafe.

    TODO: (improve this doc)
    """
    def __init__(self,address,client_key=0x12345678,encryption=VIE):
        self._in = Queue(QUEUE_SIZE_IN)
        self._out = Queue(QUEUE_SIZE_OUT)
        # added to by _handle_reliable, removed from by _process_any_reliable
        self._reliable_in = [] 
        self._reliable_in_seq = 0
        # for outgoing reliable packets, reliable_out is locked by 3 methods: 
        # 1:send (if reliable)   -- to add unacknowledged reliable packets
        # 2:_handle_reliable_ack -- to remove now-acknowledged reliable packets
        # 3:_reliable_loop       -- to resend unacknowledged rel packets
        self._reliable_out = []
        self._reliable_out_lock = Lock()
        self._reliable_out_seq = 0
        # payload accumulates in _handle_chunk and _handle_chunk_tail
        self._chunks = [] 
        self._threads = { # these do nothing until they .start()
            # this sends packets from the outgoing queue
            "send"  : Thread(target=self._sending_loop,name="Core:send"),
            # this recvs packets into the incoming queue
            "recv"  : Thread(target=self._receiving_loop,name="Core:recv"),
            # this resends unacknowledged items from the reliable outgoing list
            "rel"   : Thread(target=self._reliable_loop,name="Core:rel"),
            # this sends a sync packet every SYNC_PERIOD seconds
            "sync"  : Thread(target=self._syncing_loop,name="Core:sync"),
            }
        self._sent_packet_count = 0
        self._received_packet_count = 0
        self._socket = None
        # this is properly initialized during self._connect (after we receive
        # the server's encryption key).
        self._enc = None         
        # core packets begin with 0x00. the next byte, packet[1], is the key 
        # into this dispatch table.  see _process_core_packet
        self._handlers = {
            packet.Reliable._id     : self._handle_reliable,
            packet.ReliableACK._id  : self._handle_reliable_ack,
            packet.Sync._id         : self._handle_sync,
            packet.SyncResponse._id : self._handle_sync_response,
            packet.Disconnect._id   : self._handle_disconnect,
            packet.Chunk._id        : self._handle_chunk,
            packet.ChunkTail._id    : self._handle_chunk_tail,
            packet.Cluster._id      : self._handle_cluster,
            # packet.ConnectResponse is handled inside _connect
            }
        self._disconnecting = Event() # all threads poll this event to continue
        self._connect(address,client_key,encryption)

    def send(self,outgoing_packet,reliable=False):
        """ 
        This adds packet to the outgoing queue and immediately returns.
        NOTE: packet is not raw data, it is a packet class having member .raw()
        """
        if reliable:
            p = packet.Reliable(seq=self._reliable_out_seq)
            p.tail = outgoing_packet.raw()
            self._reliable_out_seq += 1
            p._last_send_time = time()
            with self._reliable_out_lock:
                self._reliable_out.append(p)
            outgoing_packet = p
        self._out.put(outgoing_packet)
    
    def recv(self,timeout=None):
        """ 
        This blocks until it returns the next packet.
        
        If no timeout is specified, it blocks until it gets a packet.
        But if timeout is not None, then this blocks for at most timeout 
        seconds, when it will throw the threading.Empty exception.
        If the connection is disconnected, this returns None.
        """
        if not self._connected:
            return None
        return self._in.get(True,timeout)

    def close(self):
        """ This blocks to disconnect and tie up loose threads. """
        if self._connected:
            self.send(packet.Disconnect())
            sleep(1)
            self._connected = False
        self._disconnecting.set() # this tells the threads to end
        for name,thread in self._threads.iteritems():
            if thread.is_alive():
                thread.join(2) # giving them all 2s may leave sync dawdling +3s

    def _connect(self,address,client_key,encryption):
        """
        This creates the socket, does the connection handshake, and if that
        succeeds, it spawns threads for sending, receiving, and syncing.
        """
        # setup socket
        self._socket = socket(AF_INET,SOCK_DGRAM)
        try:
            self._socket.connect(address)
        except:
            warn("unable to connect socket to %r" % address)
            return
        self._socket.setblocking(True)
        self._socket.settimeout(3.0)
        # raw send the Connect packet
        connect_p = packet.Connect(key=client_key,version=encryption.version)
        d = connect_p.raw()
        if d is not None:
            self._socket.sendall(d)
        else:
            warn("unable to form connect request")
            return
        # now we wait for ConnectResponse
        self._connected = False
        for attempt in range(3):
            try:
                raw_packet = self._socket.recv(MAX_PACKET_SIZE)
            except timeout:
                continue
            # ensure we got the ConnectResponse packet
            if raw_packet[:2] == '\x00'+packet.ConnectResponse._id:
                p = packet.ConnectResponse(raw_packet)
                self._enc = encryption(client_key,p.server_key)
                self._connected = True
                break
        # the connection handshake is done, if it worked then we spawn threads
        if self._connected:
            self._spawn_threads()
        else:
            warn("connection failed")
    
    def _spawn_threads(self):
        """
        This starts all threads.
        """
        for name,thread in self._threads.iteritems():
            thread.start()
    
    def _encrypt_packet(self,packet_data):
        """
        This doesn't encrypt the first byte of any packet.  And for core 
        packets, it doesn't encrypt the first 2 bytes.
        """
        unencrypted_prefix_size = 1
        if packet_data[0] == '\x00': # core packets have an extra byte prefix
            unencrypted_prefix_size += 1
        encrypted_data = self._enc.encrypt(\
                                    packet_data[unencrypted_prefix_size:])
        if encrypted_data is None:
            return None
        else:
            return packet_data[:unencrypted_prefix_size] + encrypted_data

    def _decrypt_packet(self,packet_data):
        """ This doesn't decrypt certain leading bytes, as in _encrypt. """
        unencrypted_prefix_size = 1
        if packet_data[0] == '\x00': # core packets have an extra byte prefix
            unencrypted_prefix_size += 1
        decrypted_data = self._enc.decrypt(\
                                    packet_data[unencrypted_prefix_size:])
        if decrypted_data is None:
            return None
        else:
            return packet_data[:unencrypted_prefix_size] + decrypted_data

    def _sending_loop(self):
        """ 
        This thread grabs packets from the outgoing queue, then encrypts and 
        sends them.
        """
        while not self._disconnecting.is_set():
            try:
                p = self._out.get(True,1)
            except Empty:
                continue
            raw = p.raw()
            if raw is None:
                warn("unable to get raw, discarding")
                self._out.task_done()
                continue
            raw_encrypted_data = self._encrypt_packet(raw)
            if raw_encrypted_data is None:
                warn("unable to encrypt, discarding %s" % p)
                self._out.task_done()
                continue
            try:
                self._socket.sendall(raw_encrypted_data)
                self._sent_packet_count += 1
            except timeout:
                warn("socket send failure")
            self._out.task_done()
    
    def _receiving_loop(self):
        """ This thread receives, decrypts, and then processes packets. """
        while not self._disconnecting.is_set():
            try:
                packet_data = self._socket.recv(MAX_PACKET_SIZE)
            except timeout:
                continue
            decrypted_data = self._decrypt_packet(packet_data)
            self._received_packet_count += 1
            self._process_packet(decrypted_data)

    def _syncing_loop(self):
        """ 
        This is the sync loop.
        While connected, this sends one Sync every SYNC_PERIOD seconds.
        """
        #sleep(0.01) # a little magic
        while not self._disconnecting.is_set():
            self.send(packet.Sync(sender_time=now(),
                      packets_sent=self._sent_packet_count,
                      packets_received=self._received_packet_count))
            sleep(SYNC_PERIOD)
            
    def _reliable_loop(self):
        """
        This begins the reliable loop.
        While connected, this resends any packet in reliable_out list that has 
        gone unacknowledged for RELIABLE_TIMEOUT_RESEND seconds.
        This must move quickly else it starves the 
        """
        while not self._disconnecting.is_set():
            now = time()
            with self._reliable_out_lock:
                for p in self._reliable_out:
                    if now - p._last_send_time > RELIABLE_TIMEOUT_RESEND:
                        self.send(p)
                        p._last_send_time = now
            sleep(0.5)


    def _process_packet(self,packet_data):
        """ This processes any core \x00 packets, and queues all others. """
        if packet_data[0] == '\x00':
            self._process_core_packet(packet_data)
        else:
            self._in.put(packet_data)

    def _process_core_packet(self, packet_data):
        """ This dispatches the core packet to the appropriate handler. """
        core_id = packet_data[1]
        if core_id in self._handlers:
            self._handlers[core_id](packet_data)
        else:
            warn("unhandled core packet id=%s" % core_id.encode("hex"))

    def _process_any_reliables(self):
        """ 
        This goes through the list of received reliable packets and processes
        any that are now ready to be processed.  
        
        self._reliable_in is the list, it contains packet.Reliable items.
        self._reliable_in_seq is the next id to be processed.
        It is incremented as the packets are processed.
        
        The actual contents of each reliable packet is retrieved by calling the
        instance member .tail() on the packet.

        If nothing is ready for processing, this function does nothing.
        Also, we might squeeze some performance with bisect instead of sort
        """
        self._reliable_in.sort(key=lambda x: x.seq)
        while len(self._reliable_in) > 0 and \
                self._reliable_in[0].seq == self._reliable_in_seq:
            p = self._reliable_in.pop(0)
            self._process_packet(p.tail)
            self.send(packet.ReliableACK(seq=self._reliable_in_seq))
            self._reliable_in_seq += 1
            

    def _handle_reliable(self,raw_data):
        """
        This receives any incoming reliable packet.  It adds the new reliable
        packet to the incoming reliable list, and processes any reliable
        packets that are newly ripe for processing.
        """
        p = packet.Reliable(raw_data)
        if p.seq < self._reliable_in_seq: # we already got this, re-ACK
            self.send(packet.ReliableACK(seq=self._reliable_in_seq))
        else:
            self._reliable_in.append(p)
            self._process_any_reliables()
        if len(self._reliable_in) > 30:
            warn("outgoing reliable queue getting large seq=%d,size=%d" % \
                  (self._reliable_in_next_id,len(self._reliable_in)))

    def _handle_reliable_ack(self,raw_data):
        """
        This Handles incoming ACKs for reliable packets we earlier sent. This
        ensures we stop waiting for acknowledgements about packets that we now
        know have been received.  An ACK operates to acknowledge every seq <= 
        that seq.
        """
        p = packet.ReliableACK(raw_data)
        with self._reliable_out_lock:
            if p.seq < self._reliable_out_seq:
                for out_p in self._reliable_out:
                    if out_p.seq <= p.seq:
                        self._reliable_out.remove(out_p)
                                           
    def _handle_sync(self,raw_packet):
        """ This receives the Sync packet and responds with a SyncResponse. """
        p = packet.Sync(raw_packet)
        sync_resp = packet.SyncResponse(remote_time=p.sender_time,
                                        sender_time=now())
        self.send(sync_resp)

    def _handle_sync_response(self,raw_packet):
        """ This receives SyncResponses to our earlier Sync requests. """
        p = packet.SyncResponse(raw_packet)
        # TODO: store or do something to synchronize

    def _handle_disconnect(self,raw_packet):
        """ 
        This propagates the disconnect notification by setting the flag in
        self._disconnecting.  The threads for sending and receiving both loop
        until this flag is set.
        """
        p = packet.Disconnect(raw_packet)
        # this fires a "None" to any games recv'ing to let them know that we
        # were disconnected in the core.
        self._in.put(None)
        warn("disconnected from server") 
        self._disconnecting.set()

    def _handle_chunk(self,raw_packet):
        """ This handles accumulating chunks. """
        p = packet.Chunk(raw_packet)
        self._chunks.append(p.tail)

    def _handle_chunk_tail(self,raw_packet):
        """ 
        This takes the accumulated chunks, adds this last one, and processes
        the content as a single packet.
        """ 
        p = packet.ChunkTail(raw_packet)
        self._chunks.append(p.tail)
        all_chunks = ''.join(self._chunks)
        self._process_packet(all_chunks)
        self._chunks = []
    
    def _handle_cluster(self,raw_packet):
        """ This takes a cluster and processes the packets inside. """
        p = packet.Cluster(raw_packet)
        d = p.tail
        while len(d) > 0:
            size = ord(d[0])
            if len(d) > size:
                self._process_packet(d[1:size+1]) 
            d = d[size+1:]

def main():
    import logging
    logging.basicConfig(level=logging.DEBUG,
            format="%(levelname)-7.7s:<%(threadName)15.15s > %(message)s")
    c = Client(("zone.aswz.org",5000))
    sleep(10)
    c.close()
    
if __name__ == '__main__':
    main()