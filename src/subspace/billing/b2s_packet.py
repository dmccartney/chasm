"""
http://wiki.minegoboom.com/index.php/UDP_Billing_Protocol
"""
from subspace.core.packet import Packet
from struct import unpack_from

class B2SPacket(Packet):
    pass

class PlayerResponse(B2SPacket):
    _id = '\x01'
    _format = "BI24s24s96sIHHHHHHIIIHHHII"
    _components = ["params","player_id","name","squad","banner","usage","year",
                   "month","day","hour","minute","second","extra_1","score_id",
                   "extra_2"]

    SUCCESS, PROMPT, BAD_PASSWORD, IP_BLOCK, NO_NEW_USERS, \
    BAD_NAME, DEMO, BUSY, REG_FORM = range(9)
    response = 0 # one of the above range(9)
    player_id = 0
    name = ""
    squad = ""
    banner = ""
    usage = 0
    year = 0 # when the account was created
    month = 0
    day = 0
    hour = 0
    minute = 0
    second = 0
    score_id = 0
    extra_1 = 0
    extra_2 = 0
    def scores(self):
        """ There are no scores if the response is not SUCCESS. """
        score_format = "HHHII"
        score_components = ["kills","deaths","goals","kill_points","flag_points"]
        if self.response ==  PlayerResponse.SUCCESS:
            try:
                score_values = unpack_from(score_format,self._tail)
                return dict(score_components,score_values)
            except:
                return None
        else:
            return None

class PlayerPrivateChat(B2SPacket):
    _id = '\x03'
    _format = "IBB"
    _components = ["server_id","type","sound"]
    server_id = 0
    type = 0x02 # seems the only valid type
    sound = 0
    def message(self):
        return self.tail.rstrip('\x00')

class ZoneRecycle(B2SPacket):
    _id = '\x04'
    _format = "BII"
    _components = ["unknown1","unknown2","unknown3"]
    unknown1 = 0
    unknown2 = 1
    unknown3 = 2

class KickPlayer(B2SPacket):
    _id = '\x08'
    _format = "II"
    _components = ["player_id","reason"]
    SYSTEM,FLOOD,BAN = range(3)
    player_id = 0
    reason = 0

class Command(B2SPacket):
    _id = '\x09'
    _format = "I"
    _components = ["player_id"]
    player_id = 0
    def message(self):
        return self.tail.rstrip('\x00')

class Chat(B2SPacket):
    _id = '\x0a'
    _format = "IB"
    _components = ["player_id","channel"]
    player_id = 0
    channel = 0
    def message(self):
        return self.tail.rstrip('\x00')

class ScoreReset(B2SPacket):
    _id = '\x31'
    _format = "II"
    _components = ["score_id","inv_score_id"]
    score_id = 0
    inv_score_id = 0

class UserPacket(B2SPacket):
    _id = '\x32'
    _format = "I1024s"
    _components = ["player_id","data"]
    player_id = 0
    data = ""

class BillingIdentity(B2SPacket):
    _id = '\x33'
    _format = "256s"
    _components = ["identity"]
    identity = ""

class UserMultichannelChat(B2SPacket):
    _id = '\x34'
    _format = "BI"
    _components = ["count"]
    count = 0
    player_id = 0

    def channels(self):
        return [unpack_from("IB",self.tail[n*5:5]) for n in range(self.count)]
    def message(self):
        return self.tail[self.count*5:].rstrip('\x00')
