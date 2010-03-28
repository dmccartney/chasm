"""
http://wiki.minegoboom.com/index.php/UDP_Billing_Protocol
"""
from subspace.core.packet import Packet
from struct import unpack_from

class B2ZPacket(Packet):
    pass

class PlayerLoginResponse(B2ZPacket):
    _id = '\x01'
    _format = "BI24s24s96sI6H3I" # + "3H2I"
    _components = ["response","player_id","name","squad","banner","usage","year",
                   "month","day","hour","minute","second","unused_1","user_id",
                   "unused_2"]

    SUCCESS, PROMPT_NEW_USER, BAD_PASSWORD, IP_BLOCK, NO_NEW_USERS, \
    BAD_NAME, DEMO, BUSY, REG_FORM = range(9)
    response = 0 # one of the above range(9)
    player_id = 0
    name = ""
    squad = ""
    banner = ""
    usage = 0
    year = month = day = hour = minute = second = 0 # when account was created
    user_id = 0
    unused_1 = 0
    unused_2 = 0
    # score = PlayerScores.raw() # this is now in .tail if response == SUCCESS
    class PlayerScores(Packet):
        """ This is not an actual packet.  Rather, it is the format for player
        scores if and when they are included in biller conversations.
        """
        _id = '' # no id
        _format = "3H2I"
        _components = ["kills","deaths","goals","kill_points","flag_points"]
        kills = deaths = goals = kill_points = flag_points = 0

    def score(self,**args):
        """ 
        This is designed to let score() be called to both insert scores into
        and to parse scores out from the PlayerLoginResponse.
        It attempts to parse the scores from the tail.
        If any keyword args are supplied, it uses these to fill the scores.
        And it then updates the packet to include the scores in its tail, all
        before it ultimately returns the player scores (technically it returns
        a PlayerLoginResponse.PlayerScores object, but it can be accessed like
        a named tuple as it contains at least the integer members
             .kills, .deaths, .goals, .kill_points, .flag_points
        """
        raw_scores = self.tail
        if len(self.tail) < 1:
            raw_scores = None
        p = PlayerLoginResponse.PlayerScores(raw_scores,**args)
        self.tail = p.raw()
        return p
    
class PlayerPrivateChat(B2ZPacket):
    _id = '\x03'
    _format = "IBB"
    _components = ["zone_id","type","sound"]
    zone_id = 0
    type = 0x02 # seems the only valid type
    sound = 0
    def message(self):
        return self.tail.rstrip('\x00')

class ZoneRecycle(B2ZPacket):
    _id = '\x04'
    _format = "BII"
    _components = ["unknown1","unknown2","unknown3"]
    unknown1 = 0
    unknown2 = 1
    unknown3 = 2

class KickPlayer(B2ZPacket):
    _id = '\x08'
    _format = "II"
    _components = ["player_id","reason"]
    SYSTEM,FLOOD,BAN = range(3)
    player_id = 0
    reason = 0

class Command(B2ZPacket):
    _id = '\x09'
    _format = "I"
    _components = ["player_id"]
    player_id = 0
    def message(self):
        return self.tail.rstrip('\x00')

class Channel(B2ZPacket):
    _id = '\x0a'
    _format = "IB"
    _components = ["player_id","channel"]
    player_id = 0
    channel = 0
    def message(self):
        return self.tail.rstrip('\x00')

class ScoreReset(B2ZPacket):
    _id = '\x31'
    _format = "II"
    _components = ["score_id","inv_score_id"]
    score_id = 0
    inv_score_id = 0

class PlayerUserPacket(B2ZPacket):
    _id = '\x32'
    _format = "I1024s"
    _components = ["player_id","data"]
    player_id = 0
    data = ""

class BillingIdentity(B2ZPacket):
    _id = '\x33'
    _format = "256s"
    _components = ["identity"]
    identity = ""

class UserMultichannelChat(B2ZPacket):
    _id = '\x34'
    _format = "BI"
    _components = ["count"]
    count = 0
    player_id = 0

    def channels(self):
        return [unpack_from("IB",self.tail[n*5:5]) for n in range(self.count)]
    def message(self):
        return self.tail[self.count*5:].rstrip('\x00')
