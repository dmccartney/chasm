"""
This module implements the biller -- i.e. the billing server.

For complete documentation see TODO: developer overview doc

Making use of player, zone, message and command modules, this implements the
controlling logic for the biller end of Z2B and B2Z protocol.
 
"""
from subspace.core.server import Server
from subspace.core import packet
from subspace.billing import b2z_packet, z2b_packet
from subspace.billing.server import player, zone, squad, message, command
from subspace.core.util import now
from MySQLdb import connect, Error 
from time import sleep
from logging import debug, info, warn
from threading import Thread, Event, Lock, current_thread
from Queue import Empty

class Biller:
    """ 
    This implements a subspace billing server.
    TODO: put together developer docs and user docs. 
    """

    def __init__(self, address, identity, db_conn):
        self.address = address
        self.identity = identity
        self.db = db_conn
        self.is_running = False
        self._conn = None # after start() this will contain a core.net.Server
        # _packet_handlers will contain all registered packet handlers 
        self._packet_handlers = {}
        # _shutting_down is set inside stop() to tell all threads to terminate
        self._shutting_down = Event()
        self._threads = {
            "recv"  : Thread(target=self._receiving_loop, name="Biller:recv"),
            }
        self.command = command.Dispatcher(self) # this handles commands
        self.zones = zone.Manager(self)
        self.players = player.Manager(self)     # this handles player actions
        self.squads = squad.Manager(self)       # this handles squads
        self.message = message.Messenger(self)  # this sends messages
        # these are packets that are handled here
        local_packet_handlers = {
            z2b_packet.Ping._id              : self._handle_ping,
            }
        self.add_packet_handlers(**local_packet_handlers)
    
    def __str__(self):
        return "Biller(%s)(%s:%d)" % (self.identity, self.address[0], self.address[1]) 

    def start(self):
        """ Starts the biller and spawns its threads."""
        debug("Starting billing server: %s" % self)
        self._conn = Server(self.address)
        for thread_name, thread in self._threads.iteritems():
            debug("Starting biller's thread %s" % thread_name)
            thread.start()
        self.is_running = True

    def stop(self):
        """
        This shuts down the biller.  
        It notifies billing threads and waits for them to join.
        """ 
        self._shutting_down.set()
        self.zones.logout_all_zones()
        self.db.commit()
        debug("Closing biller's threads")
        for thread_name, thread in self._threads.iteritems():
            debug("Stopping biller thread %s" % thread_name)
            if thread is not current_thread():
                thread.join(3.0) # give each thread 3s to join
        self._conn.shutdown()
        self.is_running = False

    def add_packet_handlers(self, **new_packet_handlers):
        """
        This permits other classes to register as a handler for a specified 
        billing packet.  Internally, it adds all id:func entries from the given 
        new_handlers to the table of packet handlers for type id, contained at
        key=id in self._packet_handlers.
        NOTE: we don't have to lock because the biller (outside the core) is a
        single blocking thread.
        """
        for packet_id, packet_fn in new_packet_handlers.iteritems():
            self._packet_handlers.setdefault(packet_id, []) \
                                                    .append(packet_fn)

    def send(self, address, packet, reliable=False):
        """
        This sends the packet to the zone at the provided address.
        It forwards this request on to the core and does not block.
        """
        self._conn.send(address, packet, reliable)

    def disconnect_zone(self, address):
        """ This tells the core to firmly disconnect the specified address. """
        self._conn.disconnect(address,notify=True)

    def _receiving_loop(self):
        """ 
        This loops in its own thread (Billing:recv) grabbing any billing 
        packets from the core and passing each off to the registered handlers.
        """
        while not self._shutting_down.is_set():
            try:
                address, raw_packet = self._conn.recv(timeout=1.0)
            except Empty:
                continue
            if raw_packet is None: # core spits out None to signal disconnect
                warn("Zone %s:%d hung up on the biller" % address)
                continue
            packet_id = raw_packet[0]
            handlers = self._packet_handlers.get(packet_id, [])
            if len(handlers) < 1:
                warn("Unhandled billing packet (len=%d) %s" % (len(raw_packet),
                           ' '.join([x.encode("hex") for x in raw_packet])))
            else:
                for hnd in handlers:
                    try:
                        hnd(address, raw_packet)
                    except Error as e:
                        warn("Error handling %s" % (
                            ' '.join([x.encode("hex") for x in raw_packet])))
                        warn("%s" % e)

    def _handle_ping(self, address, raw_packet):
        p = z2b_packet.Ping(raw_packet)
        #debug("received ping")

def main():
    import logging
    import yaml
    from random import randint
    logging.basicConfig(level=logging.DEBUG,
                        format="<%(threadName)25.25s > %(message)s")
    # TODO: be more convenient (execution time overrides, win32 compat, etc) 
    conf = yaml.load(open('/etc/chasm/biller.conf'))
    db_conn = connect(**conf["db"])
    biller = Biller(("0.0.0.0", conf["port"]), conf["name"], db_conn)
    biller.start()
    while biller.is_running:
        sleep(3)
    db_conn.close()

if __name__ == '__main__':
    main()