"""
http://wiki.minegoboom.com/index.php/UDP_Billing_Protocol
"""
from subspace.core.packet import Packet

class S2BPacket(Packet):
    pass

class Ping(S2BPacket):
    _id = '\x01'

class ServerConnect(S2BPacket):
    _id = '\x02'
    _format = "III126sI32s"
    _components = ["server_id","group_id","score_id",
                   "server_name","port","password"]
    server_id = 0
    group_id = 0
    score_id = 0
    server_name = ""
    port = 0
    password = ""

class ServerDisconnect(S2BPacket):
    _id = '\x03'

class UserLogin(S2BPacket):
    _id = '\x04'
    _format = "BI32s32sIIIBBH256s"
    _components = ["is_new_user","ip","username","password","player_id",
                   "machine_id","timezone","unused","is_sysop",
                   "client_version","client_extra_data"]
    is_new_user = False
    ip = 0
    username = "" 
    password = ""
    player_id = 0
    machine_id = 0
    timezone = 0
    unused = 0
    is_sysop = False
    client_version = 0
    client_extra_data = ""

class UserLogoff(S2BPacket):
    _id = '\x05'
    _format = "I8HII"
    _components = ["player_id","reason","latency","ping","packetloss_s2c",
                   "packetloss_c2s","kills","deaths","flags",
                   "kill_points","flag_points"]
    player_id = 0
    reason = 0
    latency = 0
    ping = 0
    packetloss_s2c = 0
    packetloss_c2s = 0
    kills = 0
    deaths = 0
    flags = 0
    kill_points = 0
    flag_points = 0

class UserPrivateChat(S2BPacket):
    _id = '\x07'
    _format = "IIBB"
    _components = ["player_id","group_id","sub_type","sound"]
    player_id = 0
    group_id = 0
    sub_type = 0
    sound = 0

class UserDemographics(S2BPacket):
    _id = '\x0d'
    _format = "I"
    _components = ["player_id"]
    player_id = 0

class UserBanner(S2BPacket):
    _id = '\x10'
    _format = "I96s"
    _components = ["player_id","banner"]
    player_id = 0
    banner = ""

class UserScore(S2BPacket):
    _id = '\x11'
    _format = "IHHHII"
    _components = ["player_id","kills","deaths","flags",
                   "kill_score","flag_score"]
    player_id = 0
    kills = 0
    deaths = 0
    goals = 0
    kill_score = 0
    flag_score = 0

class UserCommand(S2BPacket):
    _id = '\x13'
    _format = "I"
    _components = ["player_id"]
    player_id = 0

class UserChannelChat(S2BPacket):
    _id = '\x14'
    _format = "I32s"
    _components = ["player_id","channel_name"]
    player_id = 0
    channel_name = ""

class ServerCapabilities(S2BPacket):
    _id = '\x15'
    _format = ""
    _components = ["capabilities"]
    capabilities = 0

    def has_multicast_chat(self):
        return (self.capabilities & (1 << 0)) != 0
    def has_demographics(self):
        return (self.capabilities & (1 << 1)) != 0