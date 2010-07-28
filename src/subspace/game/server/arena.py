"""
The zone will invoke "process_entering_player" and "process_leaving_player" to
indicate that the player is entering or leaving.  The zone's messenger will
invoke "process_message" to instruct the Arena to process a Player's message
from inside that Arena.  

On "entering", the Arena must send the player the map and settings information.
It must send the entering player the list of existing players, and it must send
the existing players a notice that the new player is entering.  

This Arena class is then responsible for keeping track of which players are in
the arena.  It does this by keeping a set of players to which it adds each 
entering player and removes each leaving player.  The Arena is also responsible
for processing chat messages from Player's inside itself.
"""

from subspace.game.map import LVL
from subspace.game.ship import Ship
from subspace.game import c2s_packet, s2c_packet
from subspace.game.server import message
from subspace.game.weapon import WeaponInfo, WeaponTypes, has_weapon
from subspace.util import now
from logging import debug, info, warn
from threading import RLock

class Arena(set):
    
    def __init__(self, zone, arena_name, arena_configuration):
        set.__init__(self)
        self.name = arena_name
        self.cfg = arena_configuration
        if self.cfg is not None and "map" in self.cfg:
            self.map = LVL(self.cfg["map"])
            self.map.load()
        else:
            self.map = None
        # this will contain all registered player packet handlers
        self._player_packet_handlers = {}
        # the lock protects this from adds/gets during process_player_packet 
        self._player_packet_handlers_lock = RLock()
        self.zone = zone
        self.games = [DefaultGame(self)]#self.load_games(self.cfg["games"])

    def __str__(self):
        return '\n'.join([
            self.__class__.__name__,
            'name = "'+self.name+'"',
            "games: \n\t" + '\n\t'.join([str(game) for game in self.games])])  

    def process_entering_player(self, player, desired_ship):
        """ 
        This adds the player to the Arena.
        Then it invokes do_arena_entrance.  
        """
        set.add(self, player) # make this act like a set
        self.do_arena_entrance(player)
    
    def process_leaving_player(self, player):
        """
        This removes the player from this Arena.
        Then it invokes do_arena_leave
        """
        set.remove(self, player)
        self.do_arena_leave(player)

    def process_message(self, player, type, msg, target_player = None):
        if type is message.Type.Public:
            p = s2c_packet.PlayerChatMessage(
                        type = message.Type.Public,
                        sending_player_id = player.id
                        )
            p.message(msg)
            # TODO: support p.sound
            # TODO: reliable = self.zone.message.cfg["reliable"]
            self.zone.send_to_many(self, p, reliable = True, exclude = [player])
        else:
            warn("Unimplemented message type %d" % type)
        
    def do_arena_entrance(self, player):
        """
        This is the default routine for an entering player.
        1. They are placed into spec mode (ship SPECTATOR, freq SpectatorFreq)
        2. They are sent the ship settings
        3. They are sent their own player ID
        4. They are notified of each other player and each other player is 
           notified of the new player
        5. They are sent the map information
        6. They are notified that the entrance is compeleted
        
        This is invoked by process_entering_player immediately after adding the
        player to this Arena. 
        """
        # treat them as if they are in spectator mode
        player.ship = Ship.SPECTATOR
        player.freq = 8025 # TODO: self.cfg["SpectatorFreq"]
        # send them the ship settings
        player.send_ship_settings(None)
        # tell them their own player ID
        player.send_session_id()
        # tell them about every other player in the arena
        for other_player in self:
            if other_player is not None:
                # tell the new player about the other player
                self.notify_of_entering_player(player, other_player)
                if player.id <> other_player.id:
                    # tell the other player about the new player
                    self.notify_of_entering_player(other_player, player)
        self._send_map_info(player)
        self.notify_of_entrance_completion(player)
        # TODO the rest of the cluster (bricks, flags, etc. - see login_cont.c)
    
    def do_arena_leave(self, player):
        """
        This is the default routine for a leaving player.
        1. Notify all others in the arena that the player has left. 
        """
        for other_player in self: # let the entire arena know that they left
            self.notify_of_leaving_player(other_player, player)

    def process_player_packet(self, player, raw_packet):
        packet_id = raw_packet[0]
        with self._player_packet_handlers_lock:
            handlers = self._player_packet_handlers.get(packet_id,[])[:]
            # we make a copy of this packet's handlers so we can unlock
        if len(handlers) < 1:
            warn("unhandled player packet from %s (len=%d, id=0x%s) %s" % 
                 (player, len(raw_packet), packet_id.encode("hex"),
                  ' '.join([x.encode("hex") for x in raw_packet])))            
        else:
            for hnd in handlers: 
                hnd(player, raw_packet)

    def add_player_packet_handler(self, **new_player_packet_handlers):
        """
        This permits other classes to register as a handler for a specified 
        player packet.  Internally, it adds all id:func entries to the table of
        player packet handlers for type id, contained at key=id in
        self._player_packet_handlers.
        
        These functions should accept 2 arguments: player and raw_packet.
        Where player is a Player and raw_packet is the bytes of the packet.
        """
        with self._player_packet_handlers_lock:
            for id, fn in new_player_packet_handlers.iteritems():
                self._player_packet_handlers.setdefault(id,[]).append(fn)

    # These variously notify a player in the arena
    
    def notify_of_entrance_completion(self, player):
        """ This notifies the player that they have entered the arena. """
        p = s2c_packet.ArenaEntranceComplete()
        player.send(p, reliable = True)
        
    def notify_of_entering_player(self, recipient, entering_player):
        """ This notifies the recipient about the entering_player. """
        p = s2c_packet.ArenaPlayerEntering(player_id = entering_player.id,
                                      name = entering_player.name,
                                      ship = entering_player.ship,
                                      freq = entering_player.freq,
                                      #squad = entering_player.squad,
                                      #wins = entering_player.wins,
                                      #losses = entering_player.losses,
                                      )
        recipient.send(p, reliable = True)    

    def notify_of_leaving_player(self, recipient, leaving_player):
        """ This notifies the recipient about the entering_player. """
        p = s2c_packet.ArenaPlayerLeaving(
                            leaving_player_id = leaving_player.id)
        recipient.send(p, reliable = True)

    def _send_map_info(self, player):
        # TODO: make this perform full map check / transfer, as needed
        p = s2c_packet.ArenaMapFilesCont()
        p.add_file(self.map.filename, self.map.checksum(0), 0x8c9b)
        # TODO: fix map "size" (it need to use compressed filesize + 17)
        player.send(p, reliable = True)

class Game(object):
    
    def __init__(self, arena, desired_event_types):
        self.arena = arena 
        game_events = {
            "ships" : {
                c2s_packet.SetShip._id : self._handle_set_ship,
                },
            "freqs" : {
                c2s_packet.SetFreq._id : self._handle_set_freq,            
                },
            "positions" : {
                c2s_packet.PositionWeapon._id : self._handle_position_weapon,
                },
            "deaths" : {
                c2s_packet.SufferDeath._id : self._handle_suffer_death,
                }
            }
        self.watching_events = []
        for desired_type in desired_event_types:
            if desired_type in game_events:
                self.watching_events.append(desired_type)
                arena.add_player_packet_handler(**game_events[desired_type])
    
    def __str__(self):
        return self.__class__.__name__ + \
            (' watching events: %s' % (', '.join(self.watching_events)))
    
    def _handle_set_ship(self, player, raw_packet):
        p = c2s_packet.SetShip(raw_packet)
        debug("got c2s_packet.SetShip")
        self.process_ship_change(player, player.ship, p.new_ship)
        
    def _handle_set_freq(self, player, raw_packet):
        p = c2s_packet.SetFreq(raw_packet)
        debug("got c2s_packet.SetFreq")
        self.process_freq_change(player, player.freq, p.new_freq)
    
    def _handle_position_weapon(self, player, raw_packet):
        p = c2s_packet.PositionWeapon(raw_packet)
        #print "<<<< status: 0x%02x - %s" % (p.status, ' '.join([x.encode("hex") for x in raw_packet]))        
        if p.x == -1 and p.y == -1:
            return # these are sent before respawn, we can ignore        
        if has_weapon(p.weapon_info):
            w_info = WeaponInfo(p.weapon_info)
            self.process_weapon(player, w_info, p.x, p.y, p.rotation, p.dx, p.dy, 
                                 p.time, p.bounty, p.energy, p.status)
            
        else:
            self.process_position(player, p.x, p.y, p.rotation, p.dx, p.dy, 
                                 p.time, p.bounty, p.energy, p.status)
    
    def _handle_suffer_death(self, player, raw_packet):
        p = c2s_packet.SufferDeath(raw_packet)
        killer = self.arena.zone.sessions.get_player(id = p.killer_player_id)
        if killer is None:
            warn("%s killed by unknown player ID %d" % (player, p.killer_player_id))
            return
        self.process_death(killer, player, p.bounty_at_death)
    # These should be implemented by subclasses
    
    def process_ship_change(self, player, old_ship, new_ship):
        """
        player is trying to change ship.
        """
        pass

    def process_freq_change(self, player, old_freq, new_freq):
        """
        player is trying to change freq.
        """
        pass

    def process_weapon(self, player, weapon_info, x, y, rotation, dx, dy, 
                        time, bounty, energy, status):
        """
        player has fired a weapon.
        weapon_info is of type s2c_packet.PlayerPositionWeapon.WeaponInfo
        The other arguments are as in process_position().
        This should also operate to update the player's current position.
        """
        pass

    def process_position(self, player, x, y, rotation, dx, dy, 
                        time, bounty, energy, status):
        """
        player has a new position.
        x, y - 0-16384
        rotation - 0-63
        dx, dy - pixels per second
        time - the sync'd tick time
        bounty - the players current bounty
        energy - the players current energy
        status - bitfield of STEALTH, CLOAK, XRADAR, ANTIWARP, FLASH, SAFEZONE, UFO
        """
        pass
    
    def process_death(self, killer, killed, bounty):
        pass

class DefaultGame(Game):

    def __init__(self, arena):
        Game.__init__(self, arena, ["ships", "freqs", "positions", "deaths"])

    def process_ship_change(self, player, old_ship, new_ship):
        """ 
        The default implementation executes the change and tells the rest of
        this arena. 
        """
        player.ship = new_ship
        change_p = s2c_packet.PlayerFreqShipChange(
            player_id = player.id, ship = player.ship, freq = player.freq)
        self.arena.zone.send_to_many(self.arena, change_p, reliable = True)
            
    def process_freq_change(self, player, old_freq, new_freq):
        """ 
        player is trying to change from old_freq to new_freq. 
        """
        player.freq = new_freq
        change_p = s2c_packet.PlayerFreqShipChange(
            player_id = player.id, ship = player.ship, freq = player.freq)
        self.arena.zone.send_to_many(self.arena, change_p, reliable = True)
    
    def process_weapon(self, player, weapon_info, x, y, rotation, dx, dy, 
                        time, bounty, energy, status):
        """
        By default, all players in the arena get the weapon fired.
        """
        p = s2c_packet.PlayerPositionWeapon(
                player_id = player.id, weapon_info = weapon_info.raw(),
                x = x, y = y, rotation = rotation, dx = dx, dy = dy,
                time = now() & 0xffff, bounty = bounty, energy = energy, 
                status = status)
        p.calculate_checksum() # this sets p.checksum properly
        player.position = p
        # players don't get their own weapon packets (TODO: bots may want them)
        self.arena.zone.send_to_many(self.arena, p, exclude = [player])

    def process_position(self, player, x, y, rotation, dx, dy, 
                        time, bounty, energy, status):
        """
        By default, all players in the arena get the position update.
        """
        p = s2c_packet.PlayerPosition(
                player_id = player.id,
                x = x, y = y, rotation = rotation, dx = dx, dy = dy,
                time = now() & 0xffff, bounty = bounty, energy = energy,
                status = status)
        player.position = p
        if player.ship is Ship.SPECTATOR:
            return # spectator positions are not broadcast
        self.arena.zone.send_to_many(self.arena, p, exclude = [player])

    def process_death(self, killer, killed, bounty):
        """
        By default, all players in the arena get the death notice.
        """
        p = s2c_packet.PlayerDeath(
                killer_player_id = killer.id,
                killed_player_id = killed.id,
                bounty = bounty,
                flag_count = 0, # TODO: flag game will adjust this
                green_id_produced = 0 # TODO: green etc will adjust this
                )
        self.arena.zone.send_to_many(self.arena, p, reliable = True)