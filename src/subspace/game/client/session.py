"""
This handles player login sessions.
TODO: better doc
"""
from subspace.game import c2s_packet, s2c_packet
from subspace.game.map import LVL
from logging import debug, info, warn

class SessionHandler():
    """
    This handles all session handshake packets and exposes session information.
    On initialization it takes a connected player and sends the login packet.
    It then responds to packets to keep the player logged into the zone.
    """
    def __init__(self, player):
        self._player = player
        self.name, self.password = None, None # only set if doing auto-create
        self._map_checksum = 0 # properly set later by _handle_map_information
        handlers = {
            s2c_packet.SessionLoginResponse._id  : self._handle_session_login_response,
            s2c_packet.SessionLoginComplete._id  : self._handle_session_login_complete,
            s2c_packet.ArenaSettings._id         : self._handle_arena_settings,
            s2c_packet.ArenaEntranceComplete._id : self._handle_arena_entrance_complete,
            s2c_packet.ArenaMapFilesCont._id     : self._handle_arena_map_files_cont,
            s2c_packet.ArenaMapFileVIE._id       : self._handle_arena_map_file_vie,
            s2c_packet.PersonalSecuritySeeds._id : self._handle_personal_security_seeds,
            s2c_packet.PersonalKeepAlive._id     : self._handle_personal_keep_alive,
            }
        self._player.add_packet_handlers(**handlers)
    
    def login(self, name, password):
        # send the player login packet 
        self._player._send(c2s_packet.SessionLoginVIE(name=name, password=password),
                            reliable=True)
        if self._player.auto_create_user: # store them if we might need them
            self.name, self.password = name, password

    def _handle_session_login_response(self,raw_packet):
        p = s2c_packet.SessionLoginResponse(raw_packet)
        if p.response == 0:
            self._player._send(c2s_packet.ArenaEnter(),
                            reliable=True)
        else:
            warn("login failure: %s" % p.response_meaning())
            if self._player.auto_create_user and p.response == 1:
                self._player._send(c2s_packet.SessionLoginVIE(name=self.name, 
                                                    password=self.password,
                                                    is_new_user=True))
            else:
                self._player._logging_off.set()
            
    def _handle_arena_entrance_complete(self,raw_packet):
        p = s2c_packet.ArenaEntranceComplete(raw_packet)
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

    def _handle_session_login_complete(self,raw_packet):
        p = s2c_packet.SessionLoginComplete(raw_packet)
        # TODO: begin sending position packets

    def _handle_personal_keep_alive(self,raw_packet):
        p = s2c_packet.PersonalKeepAlive(raw_packet)
        #debug("got keep-alive")
        # TODO: ignore or maybe respond

    def _handle_personal_security_seeds(self,raw_packet):
        p = s2c_packet.PersonalSecuritySeeds(raw_packet)
        key = p.checksum_key & 0xffffffff
        debug("got security request with key = 0x%08x" % key)
        # TODO: do checksums
        # if we are going to do it, do it, but for now we send default garbage
        r = c2s_packet.SecurityChecksum()
        #from subspace.core.checksum import exe_checksum, lvl_checksum, settings_checksum
        #r.subspace_exe_checksum = exe_checksum(key)
        #r.map_lvl_checksum = lvl_checksum(self._map, key)
        #r.settings_checksum = settings_checksum(self._settings, key)
        #debug("responding with: %s" % r)
        self._player._send(r)

    def _handle_arena_map_files_cont(self, raw_packet):
        p = s2c_packet.ArenaMapFilesCont(raw_packet)
        files = p.get_files()
        if len(files) < 1:
            warn("received empty map information")
            return
        map_file_name, map_checksum, map_compressed_size = files[0]
        self._process_map_info(map_file_name, map_checksum)
    
    def _process_map_info(self, map_file_name, map_checksum):
        # TODO: check if we actually have this map, otherwise request it
        map_file_name = map_file_name.rstrip('\x00')
        try:
            self._map = LVL(self._player.map_folder + map_file_name)
            self._map.load()
        except Exception as e:
            warn("failure loading map %s: %s" % (map_file_name,e))
            # TODO: request file
            self._map = None
            return
        if self._map.checksum(0) <> map_checksum:
            warn("loaded map checksum eq 0x%08x, should eq 0x%08x" % \
                    (self._map.checksum(0), map_checksum))
            # TODO: request file
        
    def _handle_arena_map_file_vie(self, raw_packet):
        p = s2c_packet.ArenaMapFileVIE(raw_packet)
        self._process_map_info(p.map_file_name, p.map_checksum)