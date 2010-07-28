"""
TODO:
http://wiki.minegoboom.com/index.php/UDP_Game_Protocol
http://d1st0rt.sscentral.com/packets.html
"""
from subspace.core.packet import Packet
from struct import unpack_from, calcsize, pack

class S2CPacket(Packet):
    pass

class SessionLoginResponse(S2CPacket):
    _id = '\x0A'
    _format = "BIB3xI5xBII8x"
    _components = ["response", "server_version", "is_vip","checksum_exe",
                   "demographic_data", "checksum_code", "checksum_news"]
    response = 0
    def response_meaning(self):
        """ Returns a string explaining the login response. """
        meanings = {
            0 : "Login OK",
            1 : "Unregistered Player",
            2 : "Bad Password",
            3 : "Arena is Full",
            4 : "Locked Out of Zone",
            5 : "Permission Only Arena",
            6 : "Permission to Spectate Only",
            7 : "Too many points to Play here",
            8 : "Connection is too Slow",
            9 : "Permission Only Arena",
            10 : "Server is Full",
            11 : "Invalid Name",
            12 : "Offensive Name",
            13 : "No Active Biller",
            14 : "Server Busy, try Later",
            16 : "Restricted Zone",
            17 : "Demo Version Detected",
            18 : "Too many Demo users",
            19 : "Demo Versions not Allowed",
            255 : "Restricted Zone, Mod Access Required",
        }
        return meanings[self.response]
    server_version = 134
    is_vip = 0
    checksum_exe = 0xFFFFFFFF
    demographic_data = False
    checksum_code = 0xFFFFFFFF #0xF1429CE8 #0x281CC948
    checksum_news = 0xFFFFFFFF

class SessionContVersion(S2CPacket):
    _id = '\x34'
    _format = "HI"
    _components = ["continuum_verison","continuum_exe_checksum"]
    continuum_verison = 40
    continuum_exe_checksum = 0xc9b61486

class SessionPlayerID(S2CPacket):
    """ This tells the client his own player ID. """
    _id = '\x01'
    _format = "H"
    _components = ["player_id"]
    player_id = 0

class SessionLoginComplete(S2CPacket):
    _id = '\x31'

class FileTransfer(S2CPacket):
    """ 
    This is used to transfer files to the client when needed.
    On login, this is used to send news.txt and update.exe.
    On arena entrance, this is used to send the lvl/lvz files.
    """
    _id = '\x10'
    _format = "16s"
    _components = ["file_name"]
    # tail contains the file.  if no filename, this is news.txt
    file_name = ""

class ArenaPlayerEntering(S2CPacket):
    """ 
    This tells players already in the arena that a new player is entering.
    The new player also gets a big list of these, one for each other player.
    """
    _id = '\x03'
    _format = "BB20s20sIIHHHHhHB"
    _components = ["ship","accepts_audio","name","squad","kill_points",
                   "flag_points","player_id","freq","wins","losses",
                   "attached_to","flags_carried","misc_bits"]
    player_id = 0
    name = ""
    squad = ""
    freq = 8025
    ship = 8
    accepts_audio = 0
    kill_points = 0
    flag_points = 0
    flags_carried = 0 # this is not authoritative
    wins = 0
    losses = 0
    attached_to = -1 # -1 indicates "not attached"
    misc_bits = 0

class ArenaEntranceComplete(S2CPacket):
    _id = '\x02'

class ArenaPlayerLeaving(S2CPacket):
    _id = '\x04'
    _format = "H"
    _components = ["leaving_player_id"]
    leaving_player_id = 0

class ArenaMapFileVIE(S2CPacket):
    """ See ContMapInformation for the more featureful new packet form. """
    _id = '\x29'
    _format = "16sI"
    _components = ["map_file_name", "map_checksum"]
    map_file_name = "default.lvl"
    map_checksum = 0xffffffff

class ArenaMapFilesCont(ArenaMapFileVIE):
    """ 
    Continuum clients accept up to 17 tuples of (filename, checksum, size).
    """
    _id = '\x29'
    _format = "" # the tail contains the tuples of file info for Cont
    _components = []
    
    def add_file(self, name, checksum, size):
        if len(self.tail) < 17 * calcsize("16sII"):
            self.tail += pack("16sII", name, checksum, size)
            
    def get_files(self):
        """ 
        This returns a list of tuples.  Each tuple contains filename, 
        checksum, and size.
        """
        result = []
        i = 0
        file_info_length = calcsize("16sII")
        while len(self.tail) >= i + file_info_length:
            result.append(unpack_from("16sII", self.tail))
            i += file_info_length
        return result

class ArenaSettings(S2CPacket):
    _id = '\x0F'
    # http://bitbucket.org/grelminar/asss/src/tip/src/packets/clientset.h
    # TODO: parse spawn_pos, long/short/byte/prizeweight sets
    
    _format = "3s1152s80s16s116s32s28s" 
    _components = ["bits", "ships", "long", "spawn_positions", 
                   "short", "byte", "prizeweight"]
    bits = ''  # 3 byte bitfield
    ships = '' # 8 * 144 byte ShipSettings
    long = ''  # 20 * 4 byte signed integers
    short = '' # 58 * 2 byte signed integers
    byte = ''  # 32 * 1 byte signed integers
    prizeweight = '' # 28 * 1 byte unsigined integers
    spawn_positions = '' # 4 * 4 byte bit fields

    def checksum(self, key):
        return sum(unpack_from("I",self.tail[i:i+4])[0] ^ key 
                    for i in range(0,357)) & 0xffffffff

    def get_ship_settings(self):
        """
        This returns a list of the 8 ship settings.  
        Each has "long_set","short_set","byte_set", and "weapons".
        "weapons" contains the parsed weapons bitfield.
        """
        ship_set_format = [ # there are 8 of these in the result
                           ("long_set", "2i"),
                           ("short_set","49h"),
                           ("byte_set", "18b"),
                           ("weapons",  "I"),
                           ("padding",  "16b")]
        weapons_format = [ # there is one of these in each result[#]["weapon"]
                ("ShrapnelMax",     5),
                ("ShrapnelRate",    5),
                ("CloakStatus",     2),
                ("StealthStatus",   2),
                ("XRadarStatus",    2),
                ("AntiWarpStatus",  2),
                ("InitialGuns",     2),
                ("MaxGuns",         2),
                ("InitialBombs",    2),
                ("MaxBombs",        2),
                ("DoubleBarrel",    1),
                ("EmpBomb",         1),
                ("SeeMines",        1),
                ("Unused1",         3)]
        result = [{} for x in range(8)]
        d = self.ships
        for ship_set in result:
            offset = 0
            for k,format in ship_set_format:
                ship_set[k] = unpack_from(format,d,offset)
                offset += calcsize(format)
            d = d[offset:]
            # now we parse the weapons
            w = ship_set["weapons"][0]
            ship_set["weapons"] = {}
            offset = 0
            for w_set, bit_count in weapons_format:
                offset += bit_count
                mask = (1 << bit_count) - 1
                shift = offset - bit_count
                ship_set["weapons"][w_set] = \
                        (((mask << shift) & w) >> shift) 
        return result

class ArenaAd(S2CPacket):
    _id = '\x30'
    _format = "BHHI"
    _components = ["mode","width","height","duration"]
    mode = 0
    width = 0
    height = 0
    duration = 0

class ArenaBrickDropped(S2CPacket):
    """ TODO: don't reimplement the asss brick bug. """
    _id = '\x21'
    def brick_list(self):
        results = []
        brick_components = ["x1","y1","x2","y2","freq","brick_id","time"]
        brick_format = "HHHHHHI"
        l = calcsize(brick_format)
        d = self.tail
        while len(d) >= l:
            brick_values = unpack_from(brick_format,d)
            results.append(brick_components,brick_values)
            d = d[l:]
        return results

class PlayerPosition(S2CPacket):
    _id = '\x28'
    _format = "bHhBBBBhhh" # + "HHHI"  # may not exist (ExtraPositionData)
    _components = ["rotation", "time", "x", "ping", "bounty", "player_id",
                   "status", "dy", "y", "dx"]
                    # + ["energy2", "s2c_latency", "timer", "item_info"]
    player_id = 0
    x = 0 # 0-16384 
    y = 0
    rotation = 0 # 0-63
    dx = 0
    dy = 0
    bounty = 0
    status = 0
    time = 0
    ping = 0
    # energy2 = 0
    # s2c_latency = 0
    # timer = 0
    # item_info = 0

class PlayerPositionWeapon(S2CPacket):
    _id = '\x05'
    _format = "bHhhHhBBBhHH" # + "HHHI"  # may not exist (ExtraPosData)
    _components = ["rotation","time","x","dy","player_id","dx",
                   "checksum","status","ping","y","bounty",
                   "weapon_info"] # + ExtraPosData (10 bytes)
    player_id = 0
    x = 0 # 0-16384 
    y = 0
    rotation = 0
    dx = 0
    dy = 0
    time = 0
    bounty = 0
    status = 0

    checksum = 0
    ping = 0
    # This can be fully interpreted by class subspace.game.weapon.WeaponInfo
    # and it can be quickly checked with method subspace.game.weapon.has_weapon()
    weapon_info = 0 

    def calculate_checksum(self):
        self.checksum = 0
        # we only do the checksum on the first 21 bytes
        # i.e. no checksum on the ExtraPosData
        for c in self.raw()[:21]:
            self.checksum ^= ord(c)
            
    # TODO: implement ExtraPosData (asss/src/packets/ppk.h)
    # struct ExtraPosData /* 10 bytes */
    #    { u16 energy; u16 s2cping; u16 timer;
    #      u32 shields : 1; u32 super : 1; u32 bursts : 4;
    #      u32 repels : 4; u32 thors : 4; u32 bricks : 4;
    #      u32 decoys : 4; u32 rockets : 4; u32 portals : 4;
    #      u32 padding : 2;
    #    };

class PlayerDeath(S2CPacket):
    _id = '\x06'
    _format = "BHHHH"
    _components = ["green_id_produced","killer_player_id","killed_player_id",
                   "bounty","flag_count"]
    killer_player_id = 0
    killed_player_id = 0
    bounty = 0
    flag_count = 0
    green_id_produced = 0

class PlayerChatMessage(S2CPacket):
    _id = '\x07'
    _format = "BBH"
    _components = ["type","sound","sending_player_id"]
    type = 2    # 0 green, 1 pub macro, 2 pub msg, 3 freq msg, 4 p to freq,
                # 5 priv, 6 red named, 7 remote priv, 8 red nameless, 9 channel
    sound = 0
    sending_player_id = 0
    def message(self, message = None):
        if message is not None:
            self.tail = message + '\x00'
        return self.tail.rstrip('\x00')

class PlayerGreen(S2CPacket):
    _id = '\x08'
    _format = "Ihhhh"
    _components = ["time","x","y","prize_number","player_id"]
    player_id = 0
    prize_number = 0
    x = 0
    y = 0
    time = 0

class PlayerStatsUpdate(S2CPacket):
    _id = '\x09'
    _format = "HIIHH"
    _components = ["player_id","flag_points","kill_points","kills","deaths"]
    player_id = 0
    flag_points = 0
    kill_points = 0
    kills = 0
    deaths = 0

class PlayerVoice(S2CPacket):
    _id = '\x0C'
    _format = "H"
    _components = ["player_id"]
    # Voice.tail contains a .wav of the voice

class PlayerFreqChange(S2CPacket):
    _id = '\x0D'
    _format = "HH"
    _components = ["player_id","new_freq"]
    player_id = 0
    new_freq = 0

class PlayerCreateTurret(S2CPacket):
    _id = '\x0E'
    _format = "HH"
    _components = ["rider_player_id","driver_player_id"]    
    rider_player_id = 0 # the one attaching
    driver_player_id = 0

class PlayerDestroyTurret(S2CPacket):
    _id = '\x15'
    _format = "H"
    _component = ["player_id"]
    driver_player_id = 0 # former driver, shaking off turrets

class PlayerResetScore(S2CPacket):
    _id = '\x1A'
    _format = "H"
    _components = ["player_id"]
    player = 0 # 0xFFFF means all players


class PlayerFreqShipChange(S2CPacket):
    _id = '\x1D'
    _format = "BHH"
    _components = ["ship","player_id","freq"]
    player_id = 0
    ship = 0
    freq = 0

class PersonalWarpTo(S2CPacket):
    _id = '\x32'
    _format = "HH"
    _components = ["x","y"]
    x = 0
    y = 0
    
class PersonalSecuritySeeds(S2CPacket):
    _id = '\x18'
    _format = "IIII"
    _components = ["green_seed","door_seed","time","checksum_key"]
    green_seed = 0
    door_seed = 0
    time = 0
    checksum_key = 0

class PersonalRequestFile(S2CPacket):
    _id = '\x19'
    _format = "256s16s"
    _components = ["local_file","remote_file"]
    # i.e. *putfile
    local_file = ""
    remote_file = ""


class PersonalShipReset(S2CPacket):
    """ The server sends this to tell the client to reset his ship. """
    _id = '\x1B'

class PersonalBeingWatched(S2CPacket):
    """ 
    The server sends this to tell the client he is being spectated, thus he
    needs to send extra data with his position packets.
    """
    _id = '\x1C'
    _format = "B"
    _components = ["is_someone_watching"]
    is_someone_watching = False # if yes, should probably send extra pos data

class PersonalGreen(S2CPacket):
    _id = '\x20'
    _format = "H"
    _components = ["type"]
    prize_number = 0

class PersonalKeepAlive(S2CPacket):
    _id = '\x27'

class FlagPosition(S2CPacket):
    _id = '\x12'
    _format = "HHHH"
    _components = ["flag_id","x","y","freq_owner"]
    flag_id = 0
    x = 0
    y = 0
    freq_owner = 0xFFFF # 0xFFFF == neutral flags

class FlagPickup(S2CPacket):
    _id = '\x13'
    _format = "HH"
    _components = ["flag_id","player_id"]
    player_id = 0
    flag_id = 0

class FlagDrop(S2CPacket):
    _id = '\x16'
    _format = "H"
    _component = ["player_id"]
    player_id = 0 # former flag carrier, dropping flags

class FlagVictory(S2CPacket):
    _id = '\x14'
    _format = "HI"
    _components = ["freq","points"]
    freq = 0
    points = 0

class BallPosition(S2CPacket):
    _id = '\x2E'
    _format = "BHHhhHI"
    _components = ["ball_id","x","y","dx","dy","time"]
    id = 0
    x = 0
    y = 0
    dx = 0
    dy = 0
    time = 0

class BallGoal(S2CPacket):
    _id = '\x0B'
    _format = "HI"
    _components = ["freq", "points"]
    freq = 0
    points = 0


def test_arena_settings():
    t = '\x00' * 1428
    a = ArenaSettings('\x0F' + t)
    print a.get_ship_settings()

def test_chat_message():
    r = """
    07 00 00 ff ff 57 65 6c 63 6f 6d 65 20 74 6f 20
    41 53 57 5a 2e 20 20 68 74 74 70 3a 2f 2f 61 73
    77 7a 2e 6f 72 67 00
    """
    d = ''.join([b.decode('hex') for b in r.split()])
    p = PlayerChatMessage(d)
    print p
    print p.tail.rstrip('\x00')

def test_cont_map_info():
    raw_cont_map_info = ''.join([chr(x) for x in 
        [0x29, 0x61, 0x73, 0x77, 0x7a, 0x2e, 0x6c, 0x76, 
         0x6c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
         0x00, 0x27, 0x27, 0x11, 0xb7, 0x9b, 0x8c, 0x00,
         0x00]])
    p1 = ArenaMapFilesCont(raw_cont_map_info)

    p2 = ArenaMapFilesCont()
    p2.add_file("aswz.lvl", 3071354663, 35995)
    
    assert p1.raw() == p2.raw()
    
    p2.add_file("other.lvz", 2123823234, 13555)
    assert len(p2.get_files()) == 2

    print p1
    print p2

if __name__ == '__main__':
    test_cont_map_info()