"""
This implements a subspace game player atop the subspace core protocol.
#TODO: refactor locally handled packets into external modules
"""
from subspace.core import client, server
from subspace.util import now
from subspace.game import map
from subspace.game.client.balls import BallGame
from subspace.game.client.flags import FlagGame
from subspace.game.client.greens import Greens
from subspace.game.client.session import SessionHandler
from subspace.game.client.messages import Messenger
from subspace.game import c2s_packet, s2c_packet
from time import sleep
from logging import debug, info, warn
from threading import Thread, Event, Lock
from Queue import Empty
from collections import namedtuple
from subspace.game.weapon import WeaponInfo

class Player:
    """ 
    This is a player in the game.
    >>> p = Player("divtest1","password",address=("zone.aswz.org",5000))
    >>> p.login()
    >>> p.messenger.send_public_message("hello arena!")
    >>> p.logout()
    """
    def __init__(self, configuration, arena="0", 
                        auto_create_user=False):
        self.cfg = configuration
        self.name = self.cfg["name"] if "name" in self.cfg else "default_player" 
        self.password = self.cfg["password"] if "password" in self.cfg else "password"
        self.address = self.cfg["address"] if "address" in self.cfg else ("localhost", 5000)
        self.map_folder = self.cfg["map_folder"] if "map_folder" in self.cfg else '/etc/chasm/maps/'
        self.arena = arena
        self.auto_create_user = auto_create_user
        self._logging_off = Event()
        # arena_entered .is_set() when we're finally in the arena
        # so if login is instructed to not block, then outsiders can safely
        # .wait([timeout]) for this event.  (incidentally, that is also how
        # login() is setup to block -- it waits for this event).
        self.arena_entered = Event()
        # we don't send position packets when we're not in a ship
        self.in_a_ship = Event()
        # the _position_loop polls this immediate data to be sent with each
        # position packet.  this table should not be accessed without the lock.
        self._immediate_data_lock = Lock() 
        self._immediate_data = {
                "x"             : 0,
                "y"             : 0,
                "rotation"      : 0,
                "dx"            : 0,
                "dy"            : 0,
                "energy"        : 1,
                "bounty"        : 1,
                }
        # this will contain all registered packet handlers
        # the lock protects this from adds/gets during _receiving_loop 
        self._packet_handlers_lock = Lock()
        self._packet_handlers = {} 
        # these will be started during login, stopped during logoff
        self._threads = {
            "recv"  : Thread(target=self._receiving_loop,
                                    name=("Player:%s:recv" % self.name)),
            "pos"   : Thread(target=self._position_loop,
                                    name=("Player:%s:pos" % self.name))
            # we do not need a thread for sending since _send is threadsafe
            }
        self._session = SessionHandler(self)
        self.arena_player_list = _ArenaPlayerList(self)
        self._flag_game = FlagGame(self)
        self._ball_game = BallGame(self)
        self._greens = Greens(self)
        self._locations = _Locations(self)
        self.messenger = Messenger(self)
        self._stats = _Stats(self)
        self._misc = _Misc(self)

    def login(self, timeout = None):
        """ 
        This initiates the connection and spawns the receiving thread.
        Most clients will do nothing until the player has actually entered the 
        arena.  Only once we are actually in the arena will (most) player 
        activities work as expected.  So, by default, this method will block 
        until we are in the arena.  If however a client sets a timeout, then
        this login() will connect and then wait at most 'timeout' seconds 
        before returning.  When so used, the client should manually inspect the
        player.arena_entered, which is a threading.Event that is set upon arena
        entry.
        """
        # setup connection
        self._conn = client.Client(self.address)
        if not self._conn._connected:
            warn("Connection failed!")
            return False
        for name,thread in self._threads.iteritems():
            thread.start()
        info("attempting player login as %s" % self.name)            
        self._session.login(self.name, self.password)
        del self.password # forget it now that we're done with it
        if timeout is not None:
            self.arena_entered.wait(timeout=timeout)
        return self.arena_entered.is_set()

    def logout(self):
        info("logging out as %s" % self.name)
        self._logging_off.set()
        if self.arena_entered.is_set():
            self._send(c2s_packet.ArenaLeave(), reliable = True)
        # Traces of the VIE client seem to show that it waits until it receives
        # an ACK for this LeaveArena packet before it closes the core
        # connection.  
        # i.e. 
        # it sends Reliable(LeaveArena) (00 03 xx xx xx xx 02) 
        # then waits to receive ReliableACK (00 04 xx xx xx xx)
        # and only then sends Disconnect (00 07).
        # This may be how it prevents players from quitting when their energy
        # is low.  For now, we just fire off Disconnect right away. 
        # TODO: investigate  
        if self._conn is not None:
            self._conn.close()
        for name, thread in self._threads.iteritems():
            #debug("joining thread %s..." % name)
            thread.join(1)
        
    def set_ship(self, ship = 0):
        # TODO: update immediate_data with _settings defaults
        p = c2s_packet.SetShip(ship = ship)
        self._send(p, reliable = True)
    
    def set_ship_data(self, **args):
        """ 
        This updates the immediate data with the supplied arguments.
        We're all consenting adults here, but to avoid some really baffling 
        surprises, this ensures only valid keywords are used to update the
        immediate ship data.
        TODO: provide better interface to setting ship data (requires some
        speculation on what clients might use this interface for ...) 
        """
        valid_k = ["x","y","rotation",
                   "dx","dy","energy","bounty"]
        valid_args = dict([(k,args[k]) for k in valid_k if k in args])
        with self._immediate_data_lock:
            self._immediate_data.update(**valid_args)

    def add_packet_handlers(self, **new_packet_handlers):
        """
        This permits other classes to register as a handler for a specified 
        game packet.  Internally, it adds all id:func entries from new_handlers
        to the table of packet handlers for type id, contained at key=id in
        self._packet_handlers.
        """
        with self._packet_handlers_lock:
            for id, fn in new_packet_handlers.iteritems():
                self._packet_handlers.setdefault(id, []).append(fn) 
    
    def _send(self, packet, **arg):
        """
        This should be called by classes to send raw packets.  It is a mostly
        private method, used by this module to send c2s_packet's. 
        It is threadsafe.
        """
        # We could check if self._conn is alive.  But leaving this naked will 
        # make bugs louder and easier to locate.  Eventually, we should 
        # gracefully catch these.
        #print '>',packet._id.encode("hex")
        self._conn.send(packet, **arg)

    def _receiving_loop(self):
        """ 
        This is the incoming loop for game packets.  It receives game packets 
        from the core and dispatches them to any registered handlers.
        """
        while not self._logging_off.is_set():
            try:
                raw_packet = self._conn.recv(timeout = 1.0)
            except Empty:
                continue
            if raw_packet is None: # core spits out a None to signal disconnect
                warn("disconnected from server")
                self._logging_off.set()
                return
            packet_id = raw_packet[0]
            #print '<',packet_id.encode("hex")
            with self._packet_handlers_lock:
                handlers = self._packet_handlers.get(packet_id, [])[:]
                # we make a copy of this packet's handlers so we can unlock
            if len(handlers) < 1:
                warn("unhandled game packet (len=%d) %s" % (len(raw_packet),
                           ' '.join([x.encode("hex") for x in raw_packet])))
            else:
                for hnd in handlers: 
                    hnd(raw_packet)

    def _position_loop(self):
        # we don't start send positions until we are in a ship
        while not self._logging_off.is_set():
            if not self.in_a_ship.is_set(): # if not in a ship, don't send
                self.in_a_ship.wait(1.0) # and slow down the poll cycle to 1s
                continue
            with self._immediate_data_lock:
                p = c2s_packet.PositionWeapon(**self._immediate_data)
            p.time = now()
            p.calculate_checksum() # this only works after any modifications
            self._send(p)
            sleep(0.2) # TODO: get Misc:SendPositionDelay from _settings

class _Misc:
    """ 
    Until they naturally fall into a class, this is where I play around with
    new packet types.
    """
    def __init__(self, player):
        self._player = player
        handlers = {
            s2c_packet.ArenaAd._id               : self._handle_arena_ad, 
            s2c_packet.PersonalBeingWatched._id  : self._handle_personal_being_watched, 
            }
        self._player.add_packet_handlers(**handlers)

    # These handlers don't have a home yet -- they should be tossed into
    # separate classes that use their data, but for now, here they are.

    def _handle_arena_ad(self, raw_packet):
        p = s2c_packet.ArenaAd(raw_packet)
        debug("received arena advertisement (mode=%d,w=%d,h=%d,duration=%d)" % \
                (p.mode, p.width, p.height, p.duration))
        # TODO: investigate p.tail to determine content format
    
    def _handle_personal_being_watched(self,raw_packet):
        p = s2c_packet.PersonalBeingWatched(raw_packet)
        debug("%s is watching me" % \
                 "someone" if bool(p.is_someone_watching) else "nobody")
        # TODO: have _position_loop send extra pos data if someone is watching

class _ArenaPlayerList():
    """
    This handles updating and exposing a list of players in the arena.
    I.e. "who is here" 
    """
    def __init__(self, player):
        """ 
        player is "me", that is, an instance of game.net.Player.  
        """
        self._player = player # this is me connected to the zone, not in list
        self._my_player_id = None
        self._player_list = {} # the list of players we know about
        handlers = {
            s2c_packet.ArenaPlayerEntering._id   : self._handle_arena_player_entering,
            s2c_packet.ArenaPlayerLeaving._id    : self._handle_arena_player_leaving,
            s2c_packet.SessionPlayerID._id       : self._handle_session_player_id,
            s2c_packet.PlayerFreqShipChange._id  : self._handle_player_freqship_change,
        }
        self._player.add_packet_handlers(**handlers)
        self._player_tuple = namedtuple('player','id, name, squad, freq, ship')
    
    def player(self, id):
        """ 
        This returns player with the specified id or None if unknown.
        The result is a named tuple containing id, name, squad, freq, ship.
        E.g.
        ...
        >>> p = arena_player_list.player(id = 0)
        >>> print "%s is on squad %s and freq %s" % (p.name, p.squad, p.freq)
        """
        return self._player_list.get(id,None)
    
    def me(self):
        """ Returns myself as a player tuple, or None if we don't know yet. """
        if self._my_player_id is not None:
            return self._player_list.get(self._my_player_id, None)
        else:
            return None 

    def all(self):
        """ 
        This returns a list of all players in the arena.
        Each list entry is a named tuple as if returned by player(). 
        """
        return self._player_list.values()

    def freq(self,freq_number = 0):
        """ This returns a list of all players on the specified freq. """
        return [p for p in self._player_list.values() if p.freq == freq_number]

    def _handle_session_player_id(self,raw_packet):
        """ NOTE: also handled by _Session """
        p = s2c_packet.SessionPlayerID(raw_packet)
        self._my_player_id = p.player_id
        debug("my player id = %d" % self._my_player_id)
    
    def _handle_arena_player_leaving(self,raw_placket):
        p = s2c_packet.ArenaPlayerLeaving(raw_placket)
        #info("player leaving (id=%d)" % p.leaving_player_id)
        if p.leaving_player_id in self._player_list:
            del self._player_list[p.leaving_player_id]

    def _handle_arena_player_entering(self,raw_packet):
        p = s2c_packet.ArenaPlayerEntering(raw_packet)
        #info("player entering %s" % p.name)
        player = self._get_player(p.player_id)
        name = p.name.rstrip('\x00') # they come in padded with NULLs
        squad = p.squad.rstrip('\x00')
        self._player_list[p.player_id] = player._replace(
                                name = name,
                                squad = squad,
                                freq = p.freq,
                                ship = p.ship)
    
    def _handle_player_freqship_change(self,raw_packet):
        p = s2c_packet.PlayerFreqShipChange(raw_packet)
        debug("player (id=%d) changed freq/ship (freq=%d,ship=%d)" % \
                            (p.player_id, p.freq, p.ship))
        if p.player_id == self._my_player_id:
            if p.ship == 8:
                self._player.in_a_ship.clear() # these signal _position_loop to (not) send
            else:
                self._player.in_a_ship.set()
        player = self._get_player(p.player_id)
        self._player_list[p.player_id] = \
                            player._replace(freq = p.freq, ship = p.ship)
    
    def _get_player(self,id):
        """ Initializes a new player or returns their current tuple. """
        return self._player_list.get(id, 
                            self._player_tuple(id, "", "", -1, -1))

class _Stats:
    """ This tracks player statistics in the game. """

    def __init__(self,player):
        self._player = player
        handlers = {
            s2c_packet.PlayerStatsUpdate._id  : self._handle_player_stats_update,
            s2c_packet.PlayerDeath._id        : self._handle_player_death,
            }
        self._player.add_packet_handlers(**handlers)

    def _handle_player_stats_update(self, raw_packet):
        p = s2c_packet.PlayerStatsUpdate(raw_packet)
        debug("stats updated (id=%d, points=%d+%d=%d, k=%d, d=%d)" % \
                (p.player_id, p.flag_points, p.kill_points,
                    p.kill_points + p.flag_points, p.kills, p.deaths))
        # TODO: do something with this data

    def _handle_player_death(self, raw_packet):
        p = s2c_packet.PlayerDeath(raw_packet)
        debug("player(id=%d) killed by player(id=%d)" % \
                (p.killed_player_id, p.killer_player_id) )
        # TODO: reference player names, store p.bounty to killer's points

class _Locations:
    """
    This handles all player and weapon position updates.
    NOTE: this does not handle ball or flag positions.  They are handled by
    _BallGame and _FlagGame.
    """
    def __init__(self, player):
        self._player = player
        handlers = {
            s2c_packet.PlayerCreateTurret._id    : self._handle_player_create_turret,
            s2c_packet.PlayerDestroyTurret._id   : self._handle_player_destroy_turret,
            # position related events
            s2c_packet.PlayerPositionWeapon._id  : self._handle_player_position_weapon,
            s2c_packet.PlayerPosition._id        : self._handle_player_position,
            s2c_packet.ArenaBrickDropped._id     : self._handle_arena_brick_dropped,
            s2c_packet.PersonalWarpTo._id        : self._handle_personal_warp_to,
            }
        self._player.add_packet_handlers(**handlers)
    
    def _handle_player_position_weapon(self, raw_packet):
        p = s2c_packet.PlayerPositionWeapon(raw_packet)
        weapon_info = WeaponInfo(p.weapon_info)
        #debug("%s" % weapon_info)
        #debug("weapon received (player_id=%d) (%d,%d) %s " % \
        # (p.player_id, p.x, p.y, weapon_info))
        # TODO: parse out positions / weapons etc.

    def _handle_player_position(self, raw_packet):
        p = s2c_packet.PlayerPosition(raw_packet)
        #debug("pos received (id=%d) (%d,%d)" % \
        #      (p.player_id, p.x, p.y))
        # TODO: update player positions

    def _handle_player_destroy_turret(self, raw_packet):
        p = s2c_packet.PlayerDestroyTurret(raw_packet)
        debug("player (id=%d) is shaking off turrets" % p.player_id)
        # TODO: check if we're on him, if so, acknowledge that we hopped off
    
    def _handle_player_create_turret(self, raw_packet):
        p = s2c_packet.PlayerCreateTurret(raw_packet)
        debug("player (id=%d) is turreting player (id=%d)" % \
              (p.rider_player_id, p.driver_player_id))
        # TODO: check if me == driver, if so, adjust accordingly

    def _handle_arena_brick_dropped(self, raw_packet):
        p = s2c_packet.ArenaBrickDropped(raw_packet)
        debug("got brick dropped (count=%d)", len(p.brick_list()))
        # TODO: do something with any bricks in the list

    def _handle_personal_warp_to(self, raw_packet):
        p = s2c_packet.PersonalWarpTo(raw_packet)
        debug("received warpto (%d,%d)" % (p.x, p.y))
        # TODO: keep track of where it stuck us

def main():
    import logging
    from random import randint
    logging.basicConfig(level=logging.DEBUG,
        format="<%(threadName)25.25s > %(message)s")
    p = Player({"name":"divtest1", "password":"password","address":("zone.aswz.org",5000)}, 
               arena="0", auto_create_user=True)
    if p.login(5):
        p.messenger.send_public_message("hello!")
        #p.set_ship(4)
        p.set_ship_data(x=10600, y=8000)
        sleep(60)
        #p.messenger.send_public_message("g'bye!")
        p.logout()
    else:
        debug("login failed")


if __name__ == '__main__':
    main()
