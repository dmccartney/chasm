"""
This handles player login sessions.
TODO: better doc
"""
from subspace.game import c2s_packet, s2c_packet
from subspace.game.client.map import LVL
from logging import debug, info, warn

class SessionHandler():
    """
    This handles all session handshake packets and exposes session information.
    On initialization it takes a connected player and sends the login packet.
    It then responds to packets to keep the player logged into the zone.
    """
    def __init__(self,player):
        self._player = player
        self.name, self.password = None, None # only set if doing auto-create
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
        self._player._send(c2s_packet.LoginVIE(name=name, password=password),
                            reliable=True)
        if self._player.auto_create_user: # store them if we might need them
            self.name, self.password = name, password

    def _handle_login_response(self,raw_packet):
        p = s2c_packet.LoginResponse(raw_packet)
        if p.response == 0:
            debug("login succeeded, sending arena login")
            self._player._send(c2s_packet.ArenaLogin(),
                            reliable=True)
        else:
            warn("login failure: %s" % p.response_meaning())
            if self._player.auto_create_user and p.response == 1:
                self._player._send(c2s_packet.LoginVIE(name=self.name, 
                                                    password=self.password,
                                                    is_new_user=True))
            else:
                self._player._logging_off.set()
            
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
            self._map = LVL(map_file_name)
            self._map.load()
        except Exception as e:
            debug("failure loading %s: %s" % (map_file_name,e))
            self._map = None
            return
        debug("loaded map (checksum=0x%08x)" % self._map.checksum(0))
        