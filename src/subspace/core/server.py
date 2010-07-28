"""
This module implements the core protocol used by subspace atop UDP.

core.client and core.server handle all core UDP packets (i.e. those beginning
with \x00).  Any other packets, e.g. subspace.billing.packet or 
subspace.game.packet, are queued for another class to handle via .recv() or
to emit via .send().

For details on how this fiddles with packets, see subspace.core.packet.  This 
module implements the controlling logic for these core packets.

TODO: split handlers off of Client so that server can spawn dispatcher.

For a client CoreConnection, it should be initialized with a socket after 
Connect and ConnectResponse.  For a server, it can be initialized immediately
after it is .accept()ed.
"""
from subspace.core import packet
from subspace.core.encryption import VIE
from subspace.util import now
from socket import socket,timeout,AF_INET,SOCK_DGRAM,SOL_SOCKET,SO_REUSEADDR
from select import select
from threading import Thread, RLock, Event
from Queue import Queue, Empty, Full
from time import time, sleep
from logging import warn, info, debug

MAX_PACKET_SIZE = 512 # we grab up to this many bytes from the socket at a time
CHUNK_SIZE = 480 # this is the size of the chunks to send when chunking
QUEUE_SIZE_IN = 500 # the number of incoming packets to queue before dropping 
QUEUE_SIZE_OUT = 500 # same, but for outgoing packets
SYNC_PERIOD = 5.0 # seconds between Sync's (see _sync)
RELIABLE_TIMEOUT_RESEND = 5.0 # seconds between reliable resends

class Server:
    """ This is a server using the subspace core protocol. """

    def __init__(self, address):
        self._connections = {} # all active {client_address:CoreConnection}
        self._connections_lock = RLock() # so rel thread can grab it to resend
        self._server_socket = socket(AF_INET,SOCK_DGRAM)
        self._server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self._server_socket.bind(address)
        self._server_socket.setblocking(False)
        self._in = Queue(QUEUE_SIZE_IN) # contains tuples of incoming (address, packet)
        self.address = self._server_socket.getsockname()
        self._threads = {
            "send" : Thread(target=self._sending_loop,name="Server:Core:send"),
            "recv" : Thread(target=self._receiving_loop,name="Server:Core:recv"),
            "rel"  : Thread(target=self._reliable_resend_loop,name="Server:Core:rel")
            }
        self._shutting_down = Event() # this is set to tell the threads to end
        info("starting core server %s" % self)
        for thread_name,thread in self._threads.iteritems():
            thread.start()
    
    def __str__(self):
        return "Core:Server(%s:%d)" % self.address

    def send(self, address, packet, reliable = False):
        if address in self._connections:
            self._connections[address].send(packet, reliable)
            return True
        else:
            return False

    def send_to_many(self, addresses, packet, reliable = False):
        """ 
        This permits more efficient sending of the same packet to many 
        addresses.
        """
        packet.raw(final_form = True)
        for address in addresses:
            self.send(address, packet, reliable)
        packet.has_final = False
            
    def send_chunked(self, address, packet):
        if address in self._connections:
            self._connections[address].send_chunked(packet)
            return True
        else:
            return False

    def recv(self, timeout=None):
        """ 
        This blocks until it returns the next (address, packet) tuple.
        
        If no timeout is specified, it blocks until it gets a packet.
        But if timeout is not None, then this blocks for at most timeout 
        seconds, when it will throw the threading.Empty exception.
        If the connection is disconnected, it returns None instead of a tuple.
        """
        return self._in.get(True, timeout)

    def disconnect(self, address, notify=True):
        """
        This removes the client at address from the connections list.
        
        If notify is True then this will notify the client of the disconnect by
        sending a Disconnect packet.
        """
        with self._connections_lock:
            if address in self._connections:
                if notify:
                    self.send(address, packet.Disconnect()) # let them know
                    self.send(address, packet.Disconnect()) # let them know
                del self._connections[address]
        
    def shutdown(self):
        """ 
        This notifies the started threads that the server is shutting down and
        waits for them to join.
        """
        debug("shutting down core server")
        self._shutting_down.set()
        with self._connections_lock:
            # make copy so we can iterate and delete
            conns = self._connections.keys()[:]
            for address in conns:
                self.disconnect(address, notify = True)
        for thread_name,thread in self._threads.iteritems():
            thread.join(3.0) # give it 3s to join

    def _sending_loop(self):
        """ This grabs from the outgoing queues and sends them. """
        while True:                 
            with self._connections_lock:
                conn_pairs = self._connections.items()[:]
            sent_any = False
            for address, conn in conn_pairs:
                try:
                    p = conn._out.get(False)
                except Empty:
                    continue
                try:
                    self._server_socket.sendto(p._encrypted, address)
                    sent_any = True
                except timeout:
                    warn("socket send failure")
                conn._out.task_done()
            if self._shutting_down.is_set():
                if sent_any: 
                    info("continuing send loop despite shutdown to flush out")
                else:
                    return # we only exit when we are done sending
            else:
                sleep(0.001)

    def _receiving_loop(self):
        """ This polls the server socket for incoming packets. """
        while not self._shutting_down.is_set():
            rs,_,__ = select([self._server_socket],[],[],1.0)
            if len(rs) == 0:
                continue
            try:
                raw_packet, client_address = \
                            self._server_socket.recvfrom(MAX_PACKET_SIZE)
            except timeout:
                continue
            # we only lock the connections dictionary when we add a new one.
            # fetching from the dict, unlike adding, is atomic and threadsafe
            if client_address not in self._connections:
                with self._connections_lock:
                    conn = self._connections[client_address] = \
                                            CoreConnection(client_address,self)
            else:
                conn = self._connections[client_address]
            try:
                conn.receive_incoming_packet(raw_packet)
            except Exception as err:
                warn("error receiving incoming packet %s" % 
                        ' '.join([x.encode("hex") for x in raw_packet]))
                warn("%s" % err)

    def _reliable_resend_loop(self):
        """ This checks each connection for reliable packets to resend. """ 
        while not self._shutting_down.is_set():
            with self._connections_lock:
                conns = self._connections.values()
            for conn in conns:
                conn.check_reliable_resend()
            sleep(1.0)

class CoreConnection:
    """
    This is a single client connected to the server.  It is made unique by the
    client_address tuple (ip, port).  It provides the methods for interacting
    with this particular client.
    
    It can do 3 things: 
        1. send -- which sends a packet to this client,
        2. receive_incoming_packet -- which accepts and processes a packet, and
        3. check_reliable_resend -- which resends any unacknowledged reliables
        
    When a packet is sent (.send()) it is encrypted and added to the
    server's outgoing queue.  If it is a reliable send, then it is wrapped as
    such before encryption.
    
    When a packet is received (.receive_incoming_packet()) it is decrypted and
    then processed.  If it is a core packet, it is handled internally.  If it
    is a game packet, then it is added to the server's incoming queue and
    tagged as coming from this client's address.
    
    When .check_reliable_resend() is invoked, it cycles through the list of
    reliable packets previously sent and checks whether they have timed out 
    (i.e. if the client has not acknowledged receipt).  Any that have so 
    expired are resent.  NOTE: .check_reliable_resend() is threadsafe 
    vis-a-vis .send().  
    """
    
    def __init__(self, client_address, server):
        self.address = client_address
        self.server = server
        self._out = Queue(QUEUE_SIZE_OUT)
        # added to by _handle_reliable, removed from by _process_any_reliable
        self._reliable_in = [] 
        self._reliable_in_seq = 0
        # for outgoing reliable packets, reliable_out is locked by 3 methods: 
        # 1:send (if reliable)   -- to add unacknowledged reliable packets
        # 2:_handle_reliable_ack -- to remove now-acknowledged reliable packets
        # 3:_reliable_loop       -- to resend unacknowledged rel packets
        self._reliable_out = []
        self._reliable_out_lock = RLock()
        self._reliable_out_seq = 0
        # payload accumulates in _handle_chunk and _handle_chunk_tail
        self._chunks = [] 
        self._sent_packet_count = 0
        self._received_packet_count = 0
        self._socket = None
        # this is properly initialized during self._connect (after we receive
        # the server's encryption key).
        self._enc = None
        # core packets begin with 0x00. the next byte, packet[1], is the key 
        # into this dispatch table.  see _process_core_packet
        self._handlers = {
            # Connect & ConnectResponse are already handled
            packet.Connect._id             : self._handle_connect,
            packet.Reliable._id            : self._handle_reliable,
            packet.ReliableACK._id         : self._handle_reliable_ack,
            packet.Sync._id                : self._handle_sync,
            packet.SyncResponse._id        : self._handle_sync_response,
            packet.Disconnect._id          : self._handle_disconnect,
            packet.Chunk._id               : self._handle_chunk,
            packet.ChunkTail._id           : self._handle_chunk_tail,
            packet.StreamRequest._id       : self._handle_stream_request,
            packet.StreamCancelRequest._id : self._handle_stream_cancel_request,
            packet.Cluster._id             : self._handle_cluster,
            }

    def send(self, outgoing_packet, reliable=False):
        """ 
        This sends the packet to this client.
        It adds the packet to the outgoing queue and immediately returns.
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
        outgoing_packet._encrypted = \
                            self._encrypt_packet(outgoing_packet.raw())
        try:
            self._out.put(outgoing_packet,False)
        except Full:
            warn("outgoing queue full, discarding packet:\n %s"\
                                     % outgoing_packet)

    def send_chunked(self, outgoing_packet):
        """
        This sends a large packet to the client in reliable chunks.  It is 
        used, for example, to send ArenaSettings.
        """
        data = outgoing_packet.raw()
        data_length = len(data)
        if data_length < CHUNK_SIZE: # don't chunk it if we don't have to
            self.send(outgoing_packet, reliable=True)
        else: 
            index = 0 # use index to avoid too many copies of the data
            while data_length - index > CHUNK_SIZE:
                p = packet.Chunk()
                p.tail = data[index:index+CHUNK_SIZE]
                index += CHUNK_SIZE
                self.send(p, reliable=True)
            p = packet.ChunkTail()
            p.tail = data[index:]
            self.send(p, reliable=True)  
    
    def receive_incoming_packet(self, packet_data):
        """ 
        This should be called when we recv incoming packets.  It processes the
        packet which, in turn, passes it off to the appropriate handlers.  None
        of the processing or handling functions should block for long. 
        """
        decrypted_data = self._decrypt_packet(packet_data)
        self._received_packet_count += 1
        self._process_packet(decrypted_data)

    def check_reliable_resend(self):
        """ 
        This should be called periodically to resend unacknowledged reliables.
        It is threadsafe vis-a-vis calls to receive_incoming_packet.
        """
        with self._reliable_out_lock:
            for p in self._reliable_out:
                if now() - p._last_send_time > RELIABLE_TIMEOUT_RESEND:
                    # NOTE: resend must not be reliable else this will deadlock
                    self.send(p,reliable=False)
                    p._last_send_time = now()

    def _encrypt_packet(self, packet_data):
        """
        This doesn't encrypt the first byte of any packet.  And for core 
        packets, it doesn't encrypt the first 2 bytes.
        """
        unencrypted_prefix_size = 1
        if packet_data[0] == '\x00': # core packets have an extra byte prefix
            unencrypted_prefix_size += 1
        if self._enc is None: # before encryption is setup, don't
            return packet_data
        else:
            encrypted_data = self._enc.encrypt(\
                                    packet_data[unencrypted_prefix_size:])
            if encrypted_data is None:
                return None
            else:
                return packet_data[:unencrypted_prefix_size] + encrypted_data

    def _decrypt_packet(self, packet_data):
        """ This doesn't decrypt certain leading bytes, as in _encrypt. """
        unencrypted_prefix_size = 1
        if packet_data[0] == '\x00': # core packets have an extra byte prefix
            unencrypted_prefix_size += 1
        if self._enc is None:
            return packet_data
        else:
            decrypted_data = self._enc.decrypt(\
                                    packet_data[unencrypted_prefix_size:])
        if decrypted_data is None:
            return None
        else:
            return packet_data[:unencrypted_prefix_size] + decrypted_data

    def _process_packet(self, packet_data):
        """ This processes any core \x00 packets, and queues all others. """
        if packet_data[0] == '\x00':
            self._process_core_packet(packet_data)
        else:
            self.server._in.put((self.address,packet_data))

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

    def _handle_connect(self, raw_data):
        """
        This receives the incoming Connect packet.  It responds with the
        ConnectReponse.
        """
        p = packet.Connect(raw_data)
        server_key = p.key # this, in essence, disables encryption
        self.send(packet.ConnectResponse(server_key=server_key))
        self._enc = VIE(p.key,server_key)
 
#    for clients (the only ones who will ever receive this packet) the socket
#    has already undergone the connect/response exchange.  so we don't need to
#    handle this packet here.
#    def _handle_connect_response(self,raw_data):
#        """ This receives the connection response. """
#        p = packet.ConnectResponse(raw_data)

    def _handle_reliable(self, raw_data):
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
                  (self._reliable_in_seq,len(self._reliable_in)))

    def _handle_reliable_ack(self, raw_data):
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
                                           
    def _handle_sync(self, raw_packet):
        """ This receives the Sync packet and responds with a SyncResponse. """
        p = packet.Sync(raw_packet)
        sync_resp = packet.SyncResponse(remote_time=p.sender_time,
                                        sender_time=now())
        self.send(sync_resp)

    def _handle_sync_response(self, raw_packet):
        """ This receives SyncResponses to our earlier Sync requests. """
        p = packet.SyncResponse(raw_packet)
        # TODO: store or do something to synchronize

    def _handle_disconnect(self, raw_packet):
        """ 
        This propagates the disconnect notification by setting the flag in
        self._disconnecting.  The threads for sending and receiving both loop
        until this flag is set.
        """
        p = packet.Disconnect(raw_packet)
        # this tosses a "None" to anything recv'ing to let them know that we
        # were disconnected in the core.
        self.server._in.put((self.address,None))
        self.server.disconnect(self.address,
                    notify=False) # they sent Disconnect, so no need to notify

    def _handle_chunk(self, raw_packet):
        """ This handles accumulating chunks. """
        p = packet.Chunk(raw_packet)
        # TODO: should probably do some checks to avoid an unending chunk
        self._chunks.append(p.tail)

    def _handle_chunk_tail(self, raw_packet):
        """ 
        This takes the accumulated chunks, adds this last one, and processes
        the content as a single packet.
        """ 
        p = packet.ChunkTail(raw_packet)
        self._chunks.append(p.tail)
        all_chunks = ''.join(self._chunks)
        self._process_packet(all_chunks)
        self._chunks = []
    
    def _handle_stream_request(self, raw_packet):
        p = packet.StreamRequest(raw_packet)
        # TODO: handle stream requests (must investigate first)
        debug("got stream request: %s" % p)
    
    def _handle_stream_cancel_request(self, raw_packet):
        p = packet.StreamCancelRequest(raw_packet)
        debug("got stream cancel request, acknowledging")
        self.send(packet.StreamCancelRequestACK(), reliable = True)
    
    def _handle_cluster(self, raw_packet):
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
    from subspace.core.client import Client
    logging.basicConfig(level=logging.DEBUG,
            format="<%(threadName)25.25s > %(message)s")
    s = Server(("",5000))
    c = [] # joined clients
    for n in range(10):
        print "Client connecting ..."
        c.append(Client(("127.0.0.1",5000)))
    sleep(3)
    for client in c:
        print "Client leaving ..."
        client.close()
    s.shutdown()
    
if __name__ == '__main__':
    main()