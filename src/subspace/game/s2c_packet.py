"""
TODO:
http://wiki.minegoboom.com/index.php/UDP_Game_Protocol
http://d1st0rt.sscentral.com/packets.html
"""
from subspace.core.packet import Packet
from struct import unpack_from, calcsize

class S2CPacket(Packet):
    pass

class PlayerID(S2CPacket):
    _id = '\x01'
    _format = "H"
    _components = ["player_id"]
    player_id = 0

class ArenaEntered(S2CPacket):
    _id = '\x02'

class PlayerEntering(S2CPacket):
    _id = '\x03'
    _format = "bB20s20sIIHHHHHHB"
    _components = ["ship","accepts_audio","name","squad","kill_points",
                   "flag_points","player_id","freq","wins","losses",
                   "attached_to","flags_carried","misc_bits"]
    player_id = 0
    name = ""
    squad = ""
    freq = 0
    ship = 0
    kill_points = 0
    flag_points = 0
    flags_carried = 0 # this is not authoritative
    wins = 0
    losses = 0
    attached_to = -1 # -1 indicates "not attached"
    
    accepts_audio = False

class PlayerLeaving(S2CPacket):
    _id = '\x04'
    _format = "H"
    _components = ["leaving_player_id"]
    leaving_player_id = 0

class Weapons(S2CPacket):
    _id = '\x05'
    _format = "bHhhHhBBBhHH" # + "HHHI"  # may not exist (ExtraPosData)
    _components = ["direction","time","x","dy","player_id","dx",
                   "checksum","status","c2s_latency","y","bounty",
                   "weapons"] # + ExtraPosData (10 bytes)
                    # TODO: implement ExtraPosData (asss/src/packets/ppk.h)
    player_id = 0
    x = 0 # 0-16384 
    y = 0
    dx = 0
    dy = 0
    bounty = 0
    status = 0
    energy = 1
    weapons = 0
    time = 0
    checksum = 0
    c2s_latency = 0
    def weapon_info(self):
        parts = [("type",5),
                 ("level",2),
                 ("shrapbouncing",1),
                 ("shraplevel",2),
                 ("shrap",5),
                 ("multifire",1)]
        types = {
            1 : "Bullet",
            2 : "Bouncing Bullet",
            3 : "Bomb",
            4 : "Proximity Bomb",
            5 : "Repel",
            6 : "Decoy",
            7 : "Burst",
            8 : "Thor" }
        result = {}
        d = self.weapons
        for name,length in parts:
            result[name] =  d & ((1 << length) - 1)
            d >>= length
        # pretty up the results, for now
        result["type"] = types[result["type"]]
        result["level"] += 1
        result["shraplevel"] += 1
        return result

class Death(S2CPacket):
    _id = '\x06'
    _format = "BHHHH"
    _components = ["green_id_produced","killer_player_id","killed_player_id",
                   "bounty","flag_count"]
    killer_player_id = 0
    killed_player_id = 0
    bounty = 0
    flag_count = 0
    green_id_produced = 0

class ChatMessage(S2CPacket):
    _id = '\x07'
    _format = "BBH"
    _components = ["type","sound","sending_player_id"]
    type = 2    # 0 green, 1 pub macro, 2 pub msg, 3 freq msg, 4 p to freq,
                # 5 priv, 6 red named, 7 remote priv, 8 red nameless, 9 channel
    sound = 0
    sending_player_id = 0
    def message(self):
        return self.tail.rstrip('\x00')

class OtherGreenPickup(S2CPacket):
    _id = '\x08'
    _format = "IHHHH"
    _components = ["time","x","y","prize_number","player_id"]
    player_id = 0
    prize_number = 0
    x = 0
    y = 0
    time = 0

class StatsUpdate(S2CPacket):
    _id = '\x09'
    _format = "HIIHH"
    _components = ["player_id","flag_points","kill_points","kills","deaths"]
    player_id = 0
    flag_points = 0
    kill_points = 0
    kills = 0
    deaths = 0

class LoginResponse(S2CPacket):
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
    is_vip = False
    checksum_exe = 0xF1429CE8
    demographic_data = False
    checksum_code = 0x281CC948
    checksum_news = 0xFFFFFFFF

class BallGoal(S2CPacket):
    _id = '\x0B'
    _format = "HI"
    _components = ["freq", "points"]
    freq = 0
    points = 0

class Voice(S2CPacket):
    _id = '\x0C'
    _format = "H"
    _components = ["player_id"]
    # Voice.tail contains a .wav of the voice

class FreqChange(S2CPacket):
    _id = '\x0D'
    _format = "HH"
    _components = ["player_id","new_freq"]
    player_id = 0
    new_freq = 0

class CreateTurret(S2CPacket):
    _id = '\x0E'
    _format = "HH"
    _components = ["rider_player_id","driver_player_id"]    
    rider_player_id = 0 # the one requesting the attachment
    driver_player_id = 0

class ArenaSettings(S2CPacket):
    _id = '\x0F'
    # http://bitbucket.org/grelminar/asss/src/tip/src/packets/clientset.h
    # TODO: parse spawn_pos, long/short/byte/prizeweight sets

    def checksum(self,key):
        #assert len(self.tail) == 357*4
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
        d = self.tail[3:]
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

class FileTransfer(S2CPacket):
    _id = '\x10'
    _format = "16s"
    _components = ["file_name"]
    # tail contains the file.  if no filename, this it is news.txt
    file_name = ""

class FlagPosition(S2CPacket):
    _id = '\x12'
    _format = "HHHH"
    _components = ["flag_id","x","y","freq_owner"]
    flag_id = 0
    x = 0
    y = 0
    freq_owner = 0xFFFF # 0xFFFF == neutral flags

class FlagClaim(S2CPacket):
    _id = '\x13'
    _format = "HH"
    _components = ["flag_id","player_id"]
    player_id = 0
    flag_id = 0

class FlagVictory(S2CPacket):
    _id = '\x14'
    _format = "HI"
    _components = ["freq","points"]
    freq = 0
    points = 0

class DestroyTurret(S2CPacket):
    _id = '\x15'
    _format = "H"
    _component = ["player_id"]
    player_id = 0 # former driver, shaking off turrets

class FlagDrop(S2CPacket):
    _id = '\x16'
    _format = "H"
    _component = ["player_id"]
    player_id = 0 # former flag carrier, dropping flags

class SecurityRequest(S2CPacket):
    _id = '\x18'
    _format = "IIII"
    _components = ["green_seed","door_seed","time","checksum_key"]
    green_seed = 0
    door_seed = 0
    time = 0
    checksum_key = 0

class RequestFile(S2CPacket):
    _id = '\x19'
    _format = "256s16s"
    _components = ["local_file","remote_file"]
    # i.e. *putfile
    local_file = ""
    remote_file = ""

class ResetScores(S2CPacket):
    _id = '\x1A'
    _format = "H"
    _components = ["player_id"]
    player = 0 # 0xFFFF means all players

class PersonalShipReset(S2CPacket):
    _id = '\x1B'

class SpecData(S2CPacket):
    _id = '\x1C'
    _format = "B"
    _components = ["is_someone_watching"]
    is_someone_watching = False # if yes, should probably send extra pos data

class FreqShipChange(S2CPacket):
    _id = '\x1D'
    _format = "BHH"
    _components = ["ship","player_id","freq"]
    player_id = 0
    ship = 0
    freq = 0

class SelfGreenPickup(S2CPacket):
    _id = '\x20'
    _format = "H"
    _components = ["type"]
    prize_number = 0

class BrickDropped(S2CPacket):
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

class KeepAlive(S2CPacket):
    _id = '\x27'

class SmallPosition(S2CPacket):
    _id = '\x28'
    _format = "BHHBBBBHHH" # + "HHHI"  # may not exist (ExtraPositionData)
    _components = ["direction","time","x","ping","bounty","player_id","togglables",
                   "dy","y","dx"]
                    # + ["energy2", "s2c_latency", "timer", "item_info"]
    player_id = 0
    x = 0 # 0-16384 
    y = 0
    dx = 0
    dy = 0
    bounty = 0
    togglables = 0
    time = 0
    ping = 0
    # energy2 = 0
    # s2c_latency = 0
    # timer = 0
    # item_info = 0

class MapInformation(S2CPacket):
    _id = '\x29'
    _format = "16sI"
    _components = ["map_file_name","map_checksum"]
    map_file_name = ""
    map_checksum = 0

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

class ZoneAd(S2CPacket):
    _id = '\x30'
    _format = "BHHI"
    _components = ["mode","width","height","duration"]
    mode = 0
    width = 0
    height = 0
    duration = 0

class LoginComplete(S2CPacket):
    _id = '\x31'

class WarpedTo(S2CPacket):
    _id = '\x32'
    _format = "HH"
    _components = ["x","y"]
    x = 0
    y = 0

def main_settings_test():
    t = '\x00' * 1428
    a = ArenaSettings('\x0F' + t)
    print a.get_ship_settings()

def main():
    r = """
    07 00 00 ff ff 57 65 6c 63 6f 6d 65 20 74 6f 20
    41 53 57 5a 2e 20 20 68 74 74 70 3a 2f 2f 61 73
    77 7a 2e 6f 72 67 00
    """
    d = ''.join([b.decode('hex') for b in r.split()])
    p = ChatMessage(d)
    print p
    print p.tail.rstrip('\x00')

if __name__ == '__main__':
    main()
