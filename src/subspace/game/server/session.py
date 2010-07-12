
from subspace.game import c2s_packet, s2c_packet
from subspace.game.server.player import Player
from logging import debug, warn
from struct import unpack_from
from binascii import crc32
from string import printable

MAX_PLAYERS = 256
class SessionManager:
    _CONT_VERSION = 40
    _CONT_EXE_FILE = "/home/dmccartney/.wine/drive_c/Program Files/Continuum/Continuum.exe"
    _CONT_CSUM_FILE = "/home/dmccartney/.wine/drive_c/Program Files/Continuum/scrty"
    def __init__(self, zone):
        self._sessions = {} # player IDs indexed by address
        self._local_packet_handlers = {
            c2s_packet.LoginVIE._id             : self._handle_login_vie,
            c2s_packet.LoginCont._id            : self._handle_login_cont,
            }
        self._do_cont_checksums()
        self._zone = zone
        self.players = [None for x in range(MAX_PLAYERS)]
        self.player_count = 0 
        zone.add_packet_handlers(**self._local_packet_handlers)

    def get_player(self, address):
        player_id = self.get_player_id(address)
        return self.players[player_id] if player_id != -1 else None

    def get_player_id(self, address):
        """ 
        Given an address, this returns the corresponding player ID.
        It returns -1 on error 
        """
        if address in self._sessions:
            return self._sessions[address]
        else:
            warn("No player ID for requested address: %s:%d" % address)
            return -1
    
    def _do_cont_checksums(self):
        code_sum = exe_sum = 0
        try:
            with open(self._CONT_EXE_FILE, "rb") as f:
                for line in f:
                    exe_sum = crc32(line, exe_sum)
        except IOError:
            warn("Continuum EXE file not found at '%s'" % self._CONT_EXE_FILE)
            exe_sum = -1
        try:
            with open(self._CONT_CSUM_FILE, "rb") as f:
                f.seek(4)
                code_sum = unpack_from("I",f.read(4))[0]
        except IOError:
            warn("Continuum scrty file not found at '%s'" % self._CONT_CSUM_FILE)
        self._cont_exe_checksum = exe_sum & 0xffffffff
        self._cont_code_checksum = code_sum & 0xffffffff
        debug("cont_exe_checksum = 0x%x" % (exe_sum & 0xffffffff))
        debug("cont_code_checksum = 0x%x" % (code_sum & 0xffffffff))
        
    def _process_login(self, address, login_packet):
        """ 
        Whether VIE or Cont, the client login attempts are handled, ultimately,
        by this method.  (See _handle_login_vie/_cont which forward here.)
        """
        if address in self._sessions:
            self._process_second_login(address, login_packet)
            return # TODO: investigate why we get a second packet
        p = login_packet
        p.name = self._clean_name(p.name)
        debug("%s is trying to login" % p.name.rstrip('\x00'))
        if True: # if self._check_login(...):
            login_resp = s2c_packet.LoginResponse(server_version=134)
            self._zone._conn.send(address,login_resp, reliable=True)
            login_comp = s2c_packet.LoginComplete()
            self._zone._conn.send(address,login_comp, reliable=True)
            player = self._get_new_player(address, p.name)
            self._sessions[address] = player.id
        #else:
            #self._conn.send(address,s2c_packet.LoginResponse(response=2)) # bad pwd

    def _process_second_login(self, address, packet):
        warn("Second Login from %s:%d" % address)
        warn("%s" % packet)

    def _get_new_player(self, address, name):
        """ This returns a new player using the next available player_id """
        for id in range(len(self.players)):
            if self.players[id] is None:
                self.players[id] = Player(self._zone, id, address, name)
                self.player_count += 1
                return self.players[id]
        warn("Max players reached!  No player ID available")
        return -1
    
    def _clear_player(self, player):
        """ This clears the specified player's slot (his id) """
        id = player.id
        if self.players[id] is not None:
            del self.players[id]
            self.player_count -= 1
            self.players[id] = None
        else:
            warn("Attempting to clear a non-existant player %s" % player)

    def _clean_name(self, name):
        """ 
        Given a player name, this cleans it up.  
        If it is invalid, this returns None.
        """
        # cut it to 19 characters
        # strip whitespace at the start or end
        # remove any non-printable and any colons
        name = ''.join(x for x in name[:19].strip() if x in printable and x != ':')
        if name[0].isalnum(): # must begin with a number or letter
            return name
        else:
            return None

    def _handle_login_vie(self, address, raw_packet):
        """
        TODO: Check player name characters, length, starting char
        """
        p = c2s_packet.LoginVIE(raw_packet)
        self._process_login(address, p)
        
    def _handle_login_cont(self, address, raw_packet):
        """
        TODO: Check player name characters, length, starting char 
        """
        # this sends the continuum version and checksum so the client can
        # know if it is "up to date" -- cont does this different than did VIE
        cont_version_p = s2c_packet.ContVersion(
                                    continuum_version=self._CONT_VERSION,
                                   continuum_checksum=self._cont_exe_checksum)
        self._zone._conn.send(address, cont_version_p, reliable=True)
        debug("sent cont checksum %s" % cont_version_p)
        p = c2s_packet.LoginCont(raw_packet)        
        self._process_login(address, p)
