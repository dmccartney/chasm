"""
This implements a subspace game zone atop the subspace core protocol.
(thus far it implements very little of the game)

Zone contains a PingServer, a SessionManager and one or more Arenas.  

The PingServer responds on Zone port + 1 and responds with the current player 
count.  This is used by clients when browsing zone lists.  PingServer gets the
current player_count from the SessionManager. 

SessionManager is responsible for player logins and associating a player with
a temporary player ID.  SessionManager handles all Session* c2s_packet's.

Once a Player is logged in, the Zone is responsible for assigning him to an 
arena.  The Zone handles c2s_packets ArenaEnter and ArenaLeave.  It uses these
to tell the proper Arena to process_entering_player or process_leaving_player.

In theory (though not yet in practice) a player can be in more than one arena.

All other c2s_packets from a Player are handled by the Player's Arena via 
Arena.process_player_packet.  Before handing the packets off to the Arena, the
Zone looks up the Player, so the Arena receives the Player and the raw_packet.
"""
from subspace.core import server
from subspace.game.server import ping, session, arena, message
from subspace.game import c2s_packet, s2c_packet
from time import sleep
from logging import debug, info, warn
from threading import Thread, Event, RLock
from Queue import Queue, Empty, Full
from yaml import load as yaml_load

class Zone:
    
    def __init__(self, address = ("", 5000), 
            config = '/etc/chasm/zone.conf', auto_start = True):
        self._address = address
        # this will contain all registered packet handlers
        # the lock protects this from adds/gets during _receiving_loop 
        self._packet_handlers_lock = RLock()
        self._packet_handlers = {}
        # this is an arbitrary packet identifier which handlers can register
        # if they want to be invoked when an address disconnects in the core.
        # See the SessionManager._handle_disconnect() for an example.
        self.DISCONNECT_PACKET_ID = "DISCONNECTED" 
        self.cfg = yaml_load(open(config))
        self._local_packet_handlers = {
            c2s_packet.ArenaEnter._id : self._handle_arena_enter,
            c2s_packet.ArenaLeave._id : self._handle_arena_leave,
            self.DISCONNECT_PACKET_ID : self._handle_disconnect,
        }
        self.add_packet_handlers(**self._local_packet_handlers)
        self.core = server.Server(self._address)
        self.shutting_down = Event()
        self._threads = {
            "recv"  : Thread(target=self._receiving_loop,name="Zone:recv")
            }
        # ping server runs on port + 1
        ping_address = address[0], address[1] + 1
        self.ping_server = ping.PingServer(ping_address, self)
        self.sessions = session.SessionManager(self)
        self.message = message.Messenger(self, self.cfg["messaging"])
        self.arenas = [arena.Arena(self, "0", self.cfg["arenas"]["aswz"])]
    
    def start(self):
        info("starting zone")
        self.ping_server.start()
        for thread_name, thread in self._threads.iteritems():
            thread.start()

    def shutdown(self):
        self.shutting_down.set()
        self.ping_server.shutdown()
        debug("closing zone threads")
        for thread_name, thread in self._threads.iteritems():
            thread.join(3.0) # give each thread 3s to join
        self.core.shutdown()


    def _receiving_loop(self):
        while not self.shutting_down.is_set():
            try:
                address, raw_packet = self.core.recv(timeout=1.0)
            except Empty:
                continue
            # core spits out None to signal disconnect
            if raw_packet is None:
                debug("zone: disconnect %s:%d" % (address[0], address[1]))
                packet_id = self.DISCONNECT_PACKET_ID
            else:
                packet_id = raw_packet[0]
            with self._packet_handlers_lock:
                handlers = self._packet_handlers.get(packet_id,[])[:]
                # we make a copy of this packet's handlers so we can unlock
            if len(handlers) < 1:
                # when the zone doesn't handle it, the player's arena(s) get it.
                player = self.sessions.get_player(address)
                if player is not None:
                    processed = False
                    for arena in self.arenas:
                        if player in arena:
                            arena.process_player_packet(player, raw_packet)
                            processed = True
                    if not processed:
                        warn("unprocessed packet from %s" % player)
                elif raw_packet is not None:
                    warn("packet from unknown player %s:%d (len=%d, id=0x%s) %s" % 
                          (address[0], address[1], len(raw_packet), packet_id.encode("hex"),
                           ' '.join([x.encode("hex") for x in raw_packet])))
            else:
                for hnd in handlers: 
                    hnd(address,raw_packet)

    def add_packet_handlers(self, **new_packet_handlers):
        """
        This permits other classes to register as a handler for a specified 
        game packet.  Internally, it adds all id:func entries from new_handlers
        to the table of packet handlers for type id, contained at key=id in
        self._packet_handlers.
        """
        with self._packet_handlers_lock:
            for id, fn in new_packet_handlers.iteritems():
                self._packet_handlers.setdefault(id,[]).append(fn)
    
    def _handle_arena_enter(self, address, raw_packet):
        p = c2s_packet.ArenaEnter(raw_packet)
        player = self.sessions.get_player(address)
        new_arena = self.arenas[0] # TODO: arena lookup on p.arena_name/number
        new_arena.process_entering_player(player, p.desired_ship)

    def _handle_arena_leave(self, address, raw_packet):
        p = c2s_packet.ArenaLeave(raw_packet)
        player = self.sessions.get_player(address)
        for arena in self.arenas:
            if player in arena:
                arena.process_leaving_player(player)
    
    def _handle_disconnect(self, address, raw_packet = None):
        player = self.sessions.get_player(address)
        if player is None:
            warn("unknown session disconnected %s:%d" % (address[0], address[1]))
            return
        for arena in self.arenas:
            if player in arena:
                arena.process_leaving_player(player)

    def send_to_many(self, players, packet, reliable = False, exclude = None):
        """
        Arenas (and the Game's inside them) can call this convenience function
        which translates the recipient players into their addresses and 
        forwards the send_to_many onto the core.
        It avoids constructing the same packet for multiple people.
        """
        exclude_list = exclude if exclude is not None else []
        addresses = [player.address for player in players if player not in exclude_list]
        self.core.send_to_many(addresses, packet, reliable)

def main():
    from random import randint
    from subspace.game.client.player import Player
    import logging
    logging.basicConfig(level=logging.DEBUG,
        format="<%(threadName)25.25s > %(message)s")
    # creates zone, attempts 10 player logins
    # all are inspected and rejected, until Zone is properly implemented
    z = Zone(("127.0.0.1", 5000))
    z.start()
    p = {}
    for i in range(10):
        p[i] = Player("divtest"+str(i), "password", ("127.0.0.1", 5000))
        p[i].login(timeout=0) 
    sleep(5)
    for i in range(10):
        if p[i].arena_entered.is_set():
            print i, "login success"
            p[i].logout()
        else:
            print i, "login failure"
            p[i].logout()
    sleep(1)
    z.shutdown()

def run():
    from subspace.game.client.player import Player
    import logging
    logging.basicConfig(level=logging.DEBUG,
        format="<%(threadName)25.25s | %(module)10.10s > %(message)s")
    z = Zone(("", 5000))
    z.start()
    #players = [Player({"address" : ("localhost", 5000),
    #                   "name" : "divtest-%s" % chr(ord('A') + i)}, arena="") 
    #                   for i in range(10)]
    #sleep(5)
    #for player in players: 
    #    player.login()
    #    print z.sessions

    #sleep(60)
    #print z.sessions
    #for player in players:
    #    player.logout()
        #sleep(1)
        #print z.sessions
    #sleep(5)
    #z.shutdown()

    
if __name__ == '__main__':
    run()