
from subspace.game import c2s_packet, s2c_packet

class Type:
    Arena, PublicMacro, Public, Freq, FreqPriv, \
    Priv, SysPriv, Remote, Sys, Channel = range(10)
    NAMES = {
            0 : "ARENA",        # green text, e.g. from *arena or *zone
            1 : "PUB_MACRO",
            2 : "PUB",          # normal
            3 : "FREQ",         # //text
            4 : "FREQPRIV",     # "text
            5 : "PRIV",         # /text
            6 : "SYSPRIV",      # red text with a player name, e.g. *warn text
            7 : "REMOTE",       # :name:text
            8 : "SYS",          # red text w/o a player name, e.g. checksum
            9 : "CHANNEL"       # ;1;text
            }

class Messenger:
    def __init__(self, zone, configuration):
        self.cfg = configuration
        self.zone = zone
        local_packet_handlers = {
            c2s_packet.ChatMessage._id : self._handle_chat_message,
            }
        zone.add_packet_handlers(**local_packet_handlers)
    
    def _handle_chat_message(self, address, raw_packet):
        p = c2s_packet.ChatMessage(raw_packet)
        player = self.zone.sessions.get_player(address)
        target_player = self.zone.sessions.get_player(id = p.target_player_id)
        for arena in self.zone.arenas:
            if player in arena:
                arena.process_message(player, p.type, p.message(), target_player = target_player)
        print p