from time import sleep
from subspace.core import client
from logging import debug, warn
from subspace.billing import z2b_packet, b2z_packet
from threading import Thread, RLock, Event
from Queue import Empty 

class Status:
    """ These are the possible status of the ZoneBilling connection. """
    is_offline, is_connecting, is_online = range(3)

class ZoneBilling:
    """ 
    This implements a zone connected to the billing server.
    
    Upon .connect(), this spawns a single thread that handles incoming b2z
    packets. 
    
    No class members block.
    
    Upon successful login, .status will be Status.is_online.
    
    TODO: better doc
    TODO: a little sloppy about relying on atomic .status operations
    """
    
    def __init__(self, biller_address, zone, network, name, password):
        self._connected = False
        self._address, self._zone = biller_address, zone
        self._network, self._name, self._password = network, name, password
        self.status = Status.is_offline
        self._logging_off = Event() # this will bet "set" to kill other threads
        self._packet_handlers = {} # this contains the packet dispatch table
        self._packet_handlers_lock = RLock() # this mutex locks the above table
        self._threads = {
            "recv"  : Thread(target=self._receiving_loop,
                             name="ZoneBilling:%s<->%s:recv" % \
                                        (self._name, self._address))
        }
        local_handlers = { # these are packets handled internally
        #    b2z_packet.KickPlayer._id           : self._handle_kick_player,
            b2z_packet.BillingIdentity._id      : self._handle_billing_identity,
        #    b2z_packet.PlayerLoginResponse._id  : self._handle_player_login_response,
        #    b2z_packet.Channel._id              : self._handle_channel,
        #    b2z_packet.Command._id              : self._handle_command,
        #    b2z_packet.PlayerPrivateChat._id    : self._handle_player_private_chat,
        #    b2z_packet.PlayerUserPacket._id     : self._handle_player_user_packet,
        #    b2z_packet.ScoreReset._id           : self._handle_score_reset,
        #    b2z_packet.UserMultichannelChat._id : self._handle_user_multichannel_chat,
        #    b2z_packet.ZoneRecycle._id          : self._handle_zone_recycle
        }
        self.add_packet_handlers(**local_handlers)


    def connect(self):
        if self.status is not Status.is_offline:
            warn("connect() issued on live billing connection")
            return None
        debug("Zone connecting to biller at %s:%d" % self._address)
        self._conn = client.Client(self._address) # create a core connection
        p = z2b_packet.ZoneConnect(zone_name = self._name, 
                                   port = self._zone._address[1], # game port
                                   password = self._password)
        self._conn.send(p,reliable=True)
        self.status = Status.is_connecting
        for thread_name, thread in self._threads.iteritems():
            debug("Starting zone's billing thread: %s" % thread_name)
            thread.start()

    def disconnect(self):
        if self.status in (Status.is_online, Status.is_connecting):
            debug("Zone disconnecting from the biller")
            p = z2b_packet.ZoneDisconnect()
            self._send(p)
            self._logging_off.set()
            self._conn.close()
            for thread_name, thread in self._threads.iteritems():
                debug("Joining zone's billing thread %s" % thread_name)
                thread.join(2)
            self.status = Status.is_offline
        else:
            debug("Unnecessary attempt to disconnect from biller (not connected)")

    def add_packet_handlers(self,**new_packet_handlers):
        """
        This permits other threads to register as a handler for a specified 
        b2z packet.  Internally, it adds all id:func entries from new_handlers
        to the table of packet handlers for type id, contained at key=id in
        self._packet_handlers.
        """
        with self._packet_handlers_lock:
            for id, fn in new_packet_handlers.iteritems():
                self._packet_handlers.setdefault(id,[]).append(fn) 

    def _receiving_loop(self):
        """ 
        This is the incoming loop for b2z packets.  It receives b2z packets 
        from the core and dispatches them to any registered handlers.
        """
        while not self._logging_off.is_set():
            try:
                raw_packet = self._conn.recv(timeout=1.0)
            except Empty:
                continue
            if raw_packet is None: # core spits out a None to signal disconnect
                warn("disconnected from biller")
                self._logging_off.set()
                return
            elif self.status is Status.is_connecting:
                # any received B2ZPacket indicates a successful login
                self.status = Status.is_online
                debug("biller is online")
            packet_id = raw_packet[0]
            with self._packet_handlers_lock:
                handlers = self._packet_handlers.get(packet_id,[])[:]
                # we make a copy of this packet's handlers so we can unlock
            if len(handlers) < 1:
                warn("unhandled b2z packet (len=%d) %s" % (len(raw_packet),
                           ' '.join([x.encode("hex") for x in raw_packet])))
            else:
                for handler in handlers: 
                    handler(raw_packet)
                    
    def _send(self, packet, reliable=False):
        """ 
        This sends the packet (B2ZPacket) and can optionally be made reliable. 
        """
        # NOTE: we permit sends while we're still Status.is_connecting because
        # the old billers do not let us know if the ZoneConnect (from 
        # self.connect()) was successful.  So we must be hopeful that it was.
        # ASSS solves this the same way. Newer servers (including 
        # subspace.billing.server.biller.Biller and the SSC biller) will send a
        # packet to indicate successful ZoneConnect which we catch in the recv
        # thread to set our status to Status.is_online.
        if self.status in (Status.is_online, Status.is_connecting):
            self._conn.send(packet, reliable)
        else:
            warn("failed attempt to send to biller before it is online")

    def _handle_billing_identity(self, raw_packet):
        p = b2z_packet.BillingIdentity(raw_packet)
        debug("Got Biller's Identity: %s" % p.identity)
        pass # TODO: something useful with identity and abilities

    def authenticate(self, player):
        debug("Authenticate: %s" % player)
        pass # TODO
    
    def update_score(self, player):
        debug("Update Score: %s" % player)
        pass # TODO
    
    def process_logoff(self, player):
        debug("Logoff %s" % player)
        pass # TODO
    
    def update_demographics(self, player):
        debug("Demographics %s" % player)
        pass # TODO
    
    def set_banner(self, player):
        debug("Banner %s" % player)
        pass # TODO
    
    def process_command(self, player):
        debug("Command %s" % player)
        pass # TODO

if __name__ == "__main__":
    """ This starts a biller locally and connects to it with ZoneBilling. """
    import logging
    import yaml
    logging.basicConfig(level=logging.DEBUG,
                        format="<%(threadName)12.12s><%(funcName)25.25s> %(message)s")
    from subspace.billing.server.biller import Biller
    from subspace.game.server.zone import Zone
    from subspace.game.client.player import Player
    from MySQLdb import connect
    b_conf = yaml.load(open('/etc/chasm/biller.conf'))
    b_db_conn = connect(**b_conf["db"])
    print "Connected to DB"
    b = Biller(("0.0.0.0", b_conf["port"]), b_conf["name"], b_db_conn)
    b.start()
    print "Biller Started"
    sleep(1)
    z = Zone(("0.0.0.0",5000))
    z.start()
    print "Zone Started"
    sleep(1)
    zb = ZoneBilling(("localhost", 5500), z, "ASWZ", "A Small Warzone", "test")
    zb.connect()
    print "Zone's Billing Started"
    sleep(5)
    print "Zone %s able to connect to the biller" % \
            ("was" if zb.status is Status.is_online else "was NOT")
    p = Player("divtest", "password", ("127.0.0.1", 5000))
    print "Player logging in."
    p.login()
    print "Player logged in."
    sleep(60)
    print "Player logging out"
    p.logout()
    sleep(1)
    print "Disconnecting Zone's Billing"
    zb.disconnect()
    sleep(1)
    print "Shutting down Zone"
    z.shutdown()
    sleep(1)
    print "Shutting down Biller"
    b.stop()
    sleep(1)
    print "Disconnecting from DB"
    b_db_conn.close()    
