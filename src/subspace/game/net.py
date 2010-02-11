"""
This implements the subspace game protocol atop the subspace core protocol.
"""
from subspace.core import net
from subspace.core.util import now
from subspace.game import map
from subspace.game import c2s_packet, s2c_packet
from time import sleep
from logging import debug, info, warn
from threading import Thread, Event, Lock
from Queue import Empty
from collections import namedtuple

class Player:
    """ 
    This is a player in the game.
    >>> p = Player("divtest1","password",address=("zone.aswz.org",5000))
    >>> p.login()
    >>> p.messenger.send_public_message("hello arena!")
    >>> p.logout()
    """
    def __init__(self, name=None, password=None, 
                        address=("zone.aswz.org",5000), arena="0"):
        self.name = name
        self.password = password
        self.address = address
        self.arena = arena
        self._logging_off = Event()
        # arena_entered .is_set() when we're finally in the arena
        # so if login is instructed to not block, then outsiders can safely
        # .wait([timeout]) for this event.  (incidentally, that is also how
        # login() is setup to block -- it waits for this event).
        self.arena_entered = Event()
        # we don't send position packets when we're not in a ship
        self._in_a_ship = Event()
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
                                    name=("Game:%s:recv" % self.name)),
            "pos"   : Thread(target=self._position_loop,
                                    name=("Game:%s:pos)" % self.name))
            # we do not need a thread for sending since _send is threadsafe
            }
        self._session = _Session(self)
        self.arena_player_list = _ArenaPlayerList(self)
        self._flag_game = _FlagGame(self)
        self._ball_game = _BallGame(self)
        self._locations = _Locations(self)
        self._greens = _Greens(self)
        self.messenger = _Messenger(self)
        self._stats = _Stats(self)
        self._misc = _Misc(self)

    def login(self,block_until_in_arena=True):
        """ 
        This initiates the connection and spawns the receiving thread.
        Most clients will do nothing until the player has actually entered the 
        arena.  Because only once we are in the arena will (most) player 
        activities work as expected.  So, by default, this method will block 
        until we are in the arena.  If, however, a client sets 
        block_until_in_arena = False, then this login() will return as soon as
        it is connected.  When so used, the client should manually inspect the
        player.arena_entered, a threading.Event that is set upon arena entry.
        """
        # setup connection
        self._conn = net.Client(self.address)
        for name,thread in self._threads.iteritems():
            debug("starting thread %s" % name)
            thread.start()
        self._session.login(self.name, self.password)
        del self.password # forget it now that we're done with it
        if block_until_in_arena:
            self.arena_entered.wait()

    def logout(self):
        info("logging out")
        self._send(c2s_packet.LeaveArena(),reliable=True)
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
        self._logging_off.set()
        for name,thread in self._threads.iteritems():
            debug("joining thread %s..." % name)
            thread.join(1)
            debug("...thread %s joined." % name)
        info("logged out")
        
    def set_ship(self,ship=0):
        # TODO: update immediate_data with _settings defaults
        p = c2s_packet.SetShip(ship=ship)
        self._send(p,reliable=True)
        if ship == 8:
            self._in_a_ship.clear() # these signal _position_loop to (not) send
        else:
            self._in_a_ship.set()
    
    def set_ship_data(self,**args):
        """ 
        This updates the immediate data with the supplied arguments.
        We're all consenting adults, but to avoid some really baffling 
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

    def add_packet_handlers(self,**new_packet_handlers):
        """
        This permits other classes to register as a handler for a specified 
        game packet.  Internally, it adds all id:func entries from new_handlers
        to the table of packet handlers for type id, contained at key=id in
        self._packet_handlers.
        """
        with self._packet_handlers_lock:
            for id, fn in new_packet_handlers.iteritems():
                self._packet_handlers.setdefault(id,[]).append(fn) 
    
    def _send(self,packet,**arg):
        """
        This should be called by classes to send raw packets.  It is a mostly
        private method, used by this module to send c2s_packet's. 
        It is threadsafe.
        """
        # We could check if self._conn is alive.  But leaving this naked will 
        # make bugs louder and easier to locate.  Eventually, we should 
        # gracefully catch these.
        self._conn.send(packet,**arg)

    def _receiving_loop(self):
        """ 
        This is the incoming loop for game packets.  It receives game packets 
        from the core and dispatches them to any registered handlers.
        """
        while not self._logging_off.is_set():
            try:
                raw_packet = self._conn.recv(timeout=1.0)
            except Empty:
                continue
            if raw_packet is None: # core spits out a None to signal disconnect
                warn("disconnected from server")
                self._logging_off.set()
                return
            packet_id = raw_packet[0]
            with self._packet_handlers_lock:
                handlers = self._packet_handlers.get(packet_id,[])[:]
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
            if not self._in_a_ship.is_set(): # if not in a ship, don't send
                self._in_a_ship.wait(1.0) # and slow down the poll cycle to 1s
                continue
            with self._immediate_data_lock:
                p = c2s_packet.Position(**self._immediate_data)
            p._do_checksum() # this only works after any modifications
            self._send(p)
            sleep(0.200) # TODO: get Misc:SendPositionDelay from _settings
        info("stopping sending positions")

class _Misc:
    """ 
    Until they naturally fall into a class, this is where I play around with
    new packet types.
    """
    def __init__(self,player):
        self._player = player
        handlers = {
            s2c_packet.ZoneAd._id     : self._handle_zone_ad, 
            s2c_packet.SpecData._id   : self._handle_spec_data, 
            }
        self._player.add_packet_handlers(**handlers)

    # These handlers don't have a home yet -- they should be tossed into
    # separate classes that use their data, but for now, here they are.

    def _handle_zone_ad(self,raw_packet):
        p = s2c_packet.ZoneAd(raw_packet)
        debug("received zone advertisement (mode=%d,w=%d,h=%d,duration=%d)" % \
                (p.mode,p.width,p.height,p.duration))
        # TODO: investigate p.tail to determine content format
    
    def _handle_spec_data(self,raw_packet):
        p = s2c_packet.SpecData(raw_packet)
        debug("received specdata (is_someone_watching? %s)" % \
                 bool(p.is_someone_watching))
        # TODO: have _position_loop send extra pos data if someone is watching

class _ArenaPlayerList():
    """
    This handles updating and exposing a list of players in the arena.
    I.e. "who is here" 
    """
    def __init__(self,player):
        """ 
        player is "me", that is, an instance of game.net.Player.  
        """
        self._player = player # this is me connected to the zone, not in list
        self._player_list = {} # the list of players we know about
        handlers = {
            s2c_packet.PlayerEntering._id   : self._handle_player_entering,
            s2c_packet.PlayerLeaving._id    : self._handle_player_leaving,
            s2c_packet.PlayerID._id         : self._handle_player_id,
            s2c_packet.FreqShipChange._id   : self._handle_freqship_change,
        }
        self._player.add_packet_handlers(**handlers)
        self._player_tuple = namedtuple('player','id, name, squad, freq, ship')
    
    def player(self, id):
        """ 
        This returns player with the specified id or None if unknown.
        The result is a named tuple containing id, name, squad, freq, ship.
        E.g.
        ...
        >>> p = arena_player_list.player(id=0)
        >>> print "%s is on squad %s and freq %s" % (p.name,p.squad,p.freq)
        """
        return self._player_list.get(id,None)
    
    def me(self):
        """ Returns myself as a player tuple, or None if we don't know yet. """
        if self._my_player_id is not None:
            return self._player_list.get(self._my_player_id,None)
        else:
            return None 

    def all(self):
        """ 
        This returns a list of all players in the arena.
        Each list entry is a named tuple as if returned by player(). 
        """
        return [p for p in self._player_list.values()]

    def freq(self,freq_number=0):
        """ This returns a list of all players on the specified freq. """
        return [p for p in self._player_list.values() if p.freq == freq_number]

    def _handle_player_id(self,raw_packet):
        """ NOTE: also handled by _Session """
        p = s2c_packet.PlayerID(raw_packet)
        self._my_player_id = p.player_id
        #debug("got my player id = %d" % self._my_player_id)
    
    def _handle_player_leaving(self,raw_placket):
        p = s2c_packet.PlayerLeaving(raw_placket)
        info("player leaving (id=%d)" % p.leaving_player_id)
        if p.leaving_player_id in self._player_list:
            del self._player_list[p.leaving_player_id]

    def _handle_player_entering(self,raw_packet):
        p = s2c_packet.PlayerEntering(raw_packet)
        info("player entering %s" % p.name)
        player = self._get_player(p.player_id)
        n = p.name.rstrip('\x00') # they come in padded with NULLs
        s = p.squad.rstrip('\x00')
        self._player_list[p.player_id] = player._replace(
                                name=n,squad=s,freq=p.freq,ship=p.ship)
    
    def _handle_freqship_change(self,raw_packet):
        p = s2c_packet.FreqShipChange(raw_packet)
        debug("player (id=%d) changed freq/ship (freq=%d,ship=%d)" % \
                            (p.player_id,p.freq,p.ship))
        player = self._get_player(p.player_id)
        self._player_list[p.player_id] = \
                                    player._replace(freq=p.freq,ship=p.ship)
    
    def _get_player(self,id):
        """ Initializes a new player or returns their current tuple. """
        return self._player_list.get(id,self._player_tuple(id,"","",-1,-1))

class _Session():
    """
    This handles all session handshake packets and exposes session information.
    On initialization it takes a connected player and sends the login packet.
    It then responds to packets to keep the player logged into the zone.
    """
    def __init__(self,player):
        self._player = player
        self._map_checksum = 0 # properly set later by _handle_map_information
        handlers = {
            s2c_packet.LoginResponse._id    : self._handle_login_response,
            s2c_packet.ArenaSettings._id    : self._handle_arena_settings,
            s2c_packet.ArenaEntered._id     : self._handle_arena_entered,
            s2c_packet.LoginComplete._id    : self._handle_login_complete,
            s2c_packet.MapInformation._id   : self._handle_map_information,
            s2c_packet.SecurityRequest._id  : self._handle_security_request,
            s2c_packet.KeepAlive._id        : self._handle_keep_alive,
            }
        self._player.add_packet_handlers(**handlers)
    
    def login(self, name, password):
        # send the player login packet 
        self._player._send(c2s_packet.Login(name=name, password=password),
                            reliable=True)

    def _handle_login_response(self,raw_packet):
        p = s2c_packet.LoginResponse(raw_packet)
        if p.response == 0:
            debug("login succeeded, sending arena login")
            self._player._send(c2s_packet.ArenaLogin(),
                            reliable=True)
        else:
            warn("login failure: %s" % p.response_meaning())
            self.logoff()
            
    def _handle_arena_entered(self,raw_packet):
        p = s2c_packet.ArenaEntered(raw_packet)
        info("entered arena")
        self._player.arena_entered.set() # trigger any waiting until we're in
        # TODO: check sequence handshake

    def _handle_arena_settings(self,raw_packet):
        p = s2c_packet.ArenaSettings(raw_packet)
        self._settings = p
        # TODO: generate interface to access settings
        #r = p.get_ship_settings()
        #debug("ship and game settings received\n"+
        #      "a warbird starts with gun level = %d" % \
        #            r[0]["weapons"]["InitialGuns"])

    def _handle_login_complete(self,raw_packet):
        p = s2c_packet.LoginComplete(raw_packet)
        debug("login sequence complete")
        # TODO: begin sending position packets
        self._player._position_thread.start()

    def _handle_keep_alive(self,raw_packet):
        p = s2c_packet.KeepAlive(raw_packet)
        #debug("got keep-alive")
        # TODO: ignore or maybe respond

    def _handle_security_request(self,raw_packet):
        p = s2c_packet.SecurityRequest(raw_packet)
        k = p.checksum_key & 0xffffffff
        debug("got security request with key = 0x%08x" % k)
        # TODO: do checksums
        # if we are going to do it, do it, but for now we send default garbage
        r = c2s_packet.SecurityChecksum()
        #from subspace.core.checksum import exe_checksum, lvl_checksum, settings_checksum
        #r.subspace_exe_checksum = exe_checksum(k)
        #r.map_lvl_checksum = lvl_checksum(self._map,k)
        #r.settings_checksum = settings_checksum(self._settings,k)
        #debug("responding with: %s" % r)
        self._player._send(r)

    def _handle_map_information(self,raw_packet):
        p = s2c_packet.MapInformation(raw_packet)
        map_file_name = p.map_file_name.rstrip('\x00')
        debug("got map information (%s) (provided checksum=0x%08x)" % \
                    (map_file_name,p.map_checksum))
        # TODO: check if we actually have this map, otherwise request it
        try:
            self._map = map.LVL(map_file_name)
            self._map.load()
        except Exception as e:
            debug("failure loading %s: %s" % (map_file_name,e))
            self._map = None
            return
        debug("loaded map (checksum=0x%08x)" % self._map.checksum(0))
        

class _Messenger:
    """ 
    This handles incoming messages and exposes methods for sending.
    send_message() permits sending of any message.
    send_*_message are convenience methods that use send_message()
    E.g.
    >>> send_message("hello",type=messenger.PUB)
    >>> send_message("pssst",type=messenger.PRIV,target_player_id=player_id)
    >>> send_message(":divine.216:hello",type=messenger.REMOTE)
    >>> send_message("5;hello",type=messenger.CHANNEL)
    >>> send_public_message("hello")
    >>> send_private_message(player_id,"pssst")
    >>> send_remote_message("divine.216","hello") 
    >>> send_channel_message(5,"hello")
    """
    message_types = { 
            0 : "ARENA",        # green text, e.g. from *arena or *zone
            1 : "PUB_MACRO",
            2 : "PUB",          # normal
            3 : "FREQ",         # //text
            4 : "FREQPRIV",     # "text
            5 : "PRIV",         # /text
            6 : "SYSPRIV",      # red text with a player name, e.g. *warn text
            7 : "REMOTE",       # :name:text
            8 : "SYS",          # red text w/o a player name, e.g. checksum
            9 : "CHANNEL"       # ;1;text
            }
    # using these instead of raw integer makes code more readable
    ARENA, PUB_MACRO, PUB, FREQ, FREQ_PRIV, \
    PRIV, SYS_PRIV, REMOTE, SYS, CHANNEL = range(10)
    
    def __init__(self,player):
        self._player = player
        handlers = {
            s2c_packet.ChatMessage._id      : self._handle_chat_message,
            }
        self._player.add_packet_handlers(**handlers)
        self._message_handlers = {} 
    
    def send_message(self,text,type=2,sound=0,target_player_id=-1):
        p = c2s_packet.ChatMessage()
        p.sound = sound
        p.type = type
        p.target_player_id = target_player_id
        p.tail = text + '\x00'
        info('sent  "%s"' % text)
        self._player._send(p)
    
    def send_public_message(self,text,**args):
        self.send_message(text,type=self.PUB,**args)
        
    def send_private_message(self,player_id,text,**args):
        self.send_message(text,type=self.PUB,target_player_id=player_id,**args)
    
    def send_remote_message(self,player_name,text,**args):
        # TODO: check for malformed player names (special chars etc.)
        self.send_message(':'+player_name+':'+text,type=self.REMOTE,**args)
    
    def send_freq_message(self,text,**args):
        self.send_message(text,type=self.FREQ,**args)
    
    def send_channel_message(self,channel_id,text,**args):
        """ Note: until you join a channel, the server will disregard these."""
        self.send_message(str(channel_id)+';'+text,type=self.CHANNEL,**args)
    
    def add_message_handler(self,message_type,hnd):
        self._message_handlers.setdefault(message_type,[]).append(hnd)
    
    def set_channels(self,channels=[]):
        """ This sets the ?chat channels to the list of channels provided. """
        self.send_public_message("?chat=" + ','.join(channels))
        # TODO: store these to do error checking on send and translate on recv

    def _handle_chat_message(self,raw_packet):
        p = s2c_packet.ChatMessage(raw_packet)
        info("got chat message (type=0x%02X): %s" % (p.type,p.message()))
        for hnd in self._message_handlers.get(p.type,[]):
            hnd(p) # we are adults, they can have the actual packet

class _Stats:
    """ This tracks player statistics in the game. """

    def __init__(self,player):
        self._player = player
        handlers = {
            s2c_packet.StatsUpdate._id      : self._handle_stats_update,
            s2c_packet.Death._id            : self._handle_death,
            }
        self._player.add_packet_handlers(**handlers)

    def _handle_stats_update(self,raw_packet):
        p = s2c_packet.StatsUpdate(raw_packet)
        debug("stats updated (id=%d, points=%d+%d=%d, k=%d, d=%d)" % \
                (p.player_id,p.flag_points,p.kill_points,
                    p.kill_points+p.flag_points,p.kills,p.deaths))
        # TODO: do something with this data

    def _handle_death(self,raw_packet):
        p = s2c_packet.Death(raw_packet)
        debug("player(id=%d) killed by player(id=%d)" % \
                (p.killed_player_id,p.killer_player_id) )
        # TODO: reference player names, store p.bounty to killer's points

class _Locations:
    """
    This handles all player and weapon position updates.
    NOTE: this does not handle ball or flag positions.  They are handled by
    _BallGame and _FlagGame.
    """
    def __init__(self,player):
        self._player = player
        handlers = {
            s2c_packet.CreateTurret._id     : self._handle_create_turret,
            s2c_packet.DestroyTurret._id    : self._handle_destroy_turret,
            # position related events
            s2c_packet.Weapons._id          : self._handle_weapons,
            s2c_packet.SmallPosition._id    : self._handle_small_position,
            s2c_packet.BrickDropped._id     : self._handle_brick_dropped,
            s2c_packet.WarpedTo._id         : self._handle_warped_to,
            }
        self._player.add_packet_handlers(**handlers)
    
    def _handle_weapons(self,raw_packet):
        p = s2c_packet.Weapons(raw_packet)
        debug("pos/weapon received (id=%d) (%d,%d)" % \
              (p.player_id,p.x,p.y))
        print p.weapon_info()
        # TODO: parse out positions / weapons etc.

    def _handle_small_position(self,raw_packet):
        p = s2c_packet.SmallPosition(raw_packet)
        debug("pos received (id=%d) (%d,%d)" % \
              (p.player_id,p.x,p.y))
        # TODO: update player positions

    def _handle_destroy_turret(self,raw_packet):
        p = s2c_packet.DestroyTurret(raw_packet)
        debug("player (id=%d) is shaking off turrets" % p.player_id)
        # TODO: check if we're on him, if so, acknowledge that we hopped off
    
    def _handle_create_turret(self,raw_packet):
        p = s2c_packet.CreateTurret(raw_packet)
        debug("player (id=%d) is turreting player (id=%d)" % \
              (p.rider_player_id,p.driver_player_id))
        # TODO: check if me == driver, if so, adjust accordingly

    def _handle_brick_dropped(self,raw_packet):
        p = s2c_packet.BrickDropped(raw_packet)
        debug("got brick dropped (count=%d)",len(p.brick_list()))
        # TODO: do something with any bricks in the list

    def _handle_warped_to(self,raw_packet):
        p = s2c_packet.WarpedTo(raw_packet)
        debug("received warpto (%d,%d)" % (p.x,p.y))
        # TODO: keep track of where it stuck us

class _FlagGame:
    """
    This handles all flag packets to implement the basics of the flag game.
    """
    flags = []
    def __init__(self,player):
        self._player = player
        handlers = {
            s2c_packet.FlagClaim._id        : self._handle_flag_claim,
            s2c_packet.FlagDrop._id         : self._handle_flag_drop,
            s2c_packet.FlagVictory._id      : self._handle_flag_victory,
            s2c_packet.FlagPosition._id     : self._handle_flag_position,
            }
        self._player.add_packet_handlers(**handlers)

    def _handle_flag_drop(self,raw_packet):
        p = s2c_packet.FlagDrop(raw_packet)
        debug("player (id=%d) dropped a flag" % p.player_id)
        # TODO: check his previous state to see how many flags he was carrying

    def _handle_flag_victory(self,raw_packet):
        p = s2c_packet.FlagVictory(raw_packet)
        debug("flag victory (freq=%d,points=%d)" % (p.freq,p.points))
        # TODO: reset flag game internally
        
    def _handle_flag_claim(self,raw_packet):
        p = s2c_packet.FlagClaim(raw_packet)
        debug("player (id=%d) picked up flag (id=%d)" % \
                (p.player_id,p.flag_id))
        # TODO: track flags, issue events
    
    def _handle_flag_position(self,raw_packet):
        p = s2c_packet.FlagPosition(raw_packet)
        if p.freq_owner == 0xFFFF:
            freq_owner = "neutral"
        else:
            freq_owner = "freq(%d)" % p.freq_owner
        debug("got flag freq (freq=%s)" % (freq_owner))
        # TODO: do something with the flag info

class _BallGame:
    """
    This handles all ball packets to implement the basics of the ball game.
    """
    def __init__(self,player):
        self._player = player
        handlers = {
            s2c_packet.BallPosition._id     : self._handle_ball_position,
            }
        self._player.add_packet_handlers(**handlers)
        
    def _handle_ball_position(self,raw_packet):
        p = s2c_packet.BallPosition(raw_packet)
        #debug("got ball (id=%d) position (%d,%d) moving (%d,%d)" % \
        #            (p.id,p.x,p.y,p.dx,p.dy))
        # TODO: do something with this and with its p.time (stateful logic)

class _Greens:
    """ This handles greens in the game. TODO: implement """
    def __init__(self,player):
        self._player = player
        handlers = {
            s2c_packet.SelfGreenPickup._id  : self._handle_self_green_pickup,
            s2c_packet.OtherGreenPickup._id : self._handle_other_green_pickup,
            }
        self._player.add_packet_handlers(**handlers)

    def _handle_other_green_pickup(self,raw_packet):
        p = s2c_packet.OtherGreenPickup(raw_packet)
        debug("other green pickup (player_id=%d) (prize_number=%d)" % \
                (p.player_id,p.prize_number))
        # TODO: update internal green distribution
    
    def _handle_self_green_pickup(self,raw_packet):
        """ This means that we received some prizes. """
        p = s2c_packet.SelfGreenPickup(raw_packet)
        debug("self green pickup (prize_number=%d)" % p.prize_number)
        # TODO: process green

class Zone:
    pass # TODO: implement

def main():
    import logging
    from random import randint
    logging.basicConfig(level=logging.INFO,
        format="<%(threadName)25.25s > %(message)s")
    
    p = Player("divtest","password",("zone.aswz.org",5000))
    p.login()
    p.messenger.send_public_message("hello!")
    sleep(1) # do other stuff
    p.set_ship(0)
    p.messenger.send_public_message("I'm in a ship!")
    sleep(1)
    p.set_ship(8)
    # TODO: rethink how to interface with movement spin in a circle at x,y
    x,y = 10000,10000
    p.set_ship_data(x=x,y=y,energy=1000,bounty=216,rotation=0)
    for rot in range(0,40):
        p.set_ship_data(rotation=rot)
        sleep(0.3)
    p.set_ship(8)
    p.messenger.send_public_message("hmph, back to spec")
    print p.arena_player_list.all()
    p.logout()

if __name__ == '__main__':
    main()
