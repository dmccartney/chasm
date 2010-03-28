"""
http://wiki.minegoboom.com/index.php/UDP_Billing_Protocol
"""
from subspace.core.packet import Packet

class Z2BPacket(Packet):
    pass

class Ping(Z2BPacket):
    _id = '\x01'

class ZoneConnect(Z2BPacket):
    _id = '\x02'
    _format = "3I126sH32s"
    _components = ["zone_id","group_id","score_id",
                   "zone_name","port","password"]
    zone_id = 0
    zone_name = ""
    group_id = 0
    score_id = 0
    port = 0
    password = ""

class ZoneDisconnect(Z2BPacket):
    _id = '\x03'

class PlayerLogin(Z2BPacket):
    _id = '\x04'
    _format = "BI32s32sIIiBBH" # + "256s"
    _components = ["is_new_user","ip","name","password","player_id",
                   "machine_id","timezone","unused","is_sysop",
                   "client_version"] # + ["client_extra_data"]
    is_new_user = False
    ip = 0
    name = "" 
    password = ""
    player_id = 0
    machine_id = 0
    timezone = 0
    unused = 0
    is_sysop = False
    client_version = 0
    #client_extra_data = ""

class PlayerLogout(Z2BPacket):
    _id = '\x05'
    _format = "I8HII"
    _components = ["player_id","reason","latency","ping","packetloss_s2c",
                   "packetloss_c2s","kills","deaths","goals",
                   "kill_points","flag_points"]
    player_id = 0
    reason = 0
    latency = 0
    ping = 0
    packetloss_s2c = 0
    packetloss_c2s = 0
    kills = 0
    deaths = 0
    goals = 0
    kill_points = 0
    flag_points = 0

class PlayerPrivate(Z2BPacket):
    _id = '\x07'
    _format = "IIBB"
    _components = ["player_id","group_id","sub_type","sound"]
    player_id = 0xffffffff
    group_id = 1
    sub_type = 2
    sound = 0
    def message(self):
        return self.tail.rstrip('\x00')

class PlayerDemographics(Z2BPacket):
    _id = '\x0d'
    _format = "I"
    _components = ["player_id"]
    player_id = 0

class PlayerBanner(Z2BPacket):
    _id = '\x10'
    _format = "I96s"
    _components = ["player_id","banner"]
    player_id = 0
    banner = ""

class PlayerScore(Z2BPacket):
    _id = '\x11'
    _format = "IHHHII"
    _components = ["player_id","kills","deaths","goals",
                   "kill_points","flag_points"]
    player_id = 0
    kills = 0
    deaths = 0
    goals = 0
    kill_points = 0
    flag_points = 0

class PlayerCommand(Z2BPacket):
    _id = '\x13'
    _format = "I"
    _components = ["player_id"]
    player_id = 0
    def message(self):
        return self.tail.rstrip('\x00')

class PlayerChannel(Z2BPacket):
    _id = '\x14'
    _format = "I32s"
    _components = ["player_id","channel_name"]
    player_id = 0
    channel_name = ""
    def message(self):
        return self.tail.rstrip('\x00')

class ZoneAbilities(Z2BPacket):
    _id = '\x15'
    _format = "I"
    _components = ["capabilities"]
    capabilities = 0

    def has_multicast_chat(self):
        return (self.capabilities & (1 << 0)) != 0
    def has_demographics(self):
        return (self.capabilities & (1 << 1)) != 0

class Unknown(Z2BPacket):
    _id = '\x36'