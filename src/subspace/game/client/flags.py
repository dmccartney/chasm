"""
This handles the flags in the game.
#TODO: implement
"""
from subspace.game import c2s_packet, s2c_packet
from logging import debug, info, warn

class FlagGame:
    """
    This handles all flag packets to implement the basics of the flag game.
    """
    flags = []
    def __init__(self,player):
        self._player = player
        handlers = {
            s2c_packet.FlagClaim._id        : self._handle_flag_claim,
            s2c_packet.FlagDrop._id         : self._handle_flag_drop,
            s2c_packet.FlagVictory._id      : self._handle_flag_victory,
            s2c_packet.FlagPosition._id     : self._handle_flag_position,
            }
        self._player.add_packet_handlers(**handlers)

    def _handle_flag_drop(self,raw_packet):
        p = s2c_packet.FlagDrop(raw_packet)
        debug("player (id=%d) dropped a flag" % p.player_id)
        # TODO: check his previous state to see how many flags he was carrying

    def _handle_flag_victory(self,raw_packet):
        p = s2c_packet.FlagVictory(raw_packet)
        debug("flag victory (freq=%d,points=%d)" % (p.freq,p.points))
        # TODO: reset flag game internally
        
    def _handle_flag_claim(self,raw_packet):
        p = s2c_packet.FlagClaim(raw_packet)
        debug("player (id=%d) picked up flag (id=%d)" % \
                (p.player_id,p.flag_id))
        # TODO: track flags, issue events
    
    def _handle_flag_position(self,raw_packet):
        p = s2c_packet.FlagPosition(raw_packet)
        if p.freq_owner == 0xFFFF:
            freq_owner = "neutral"
        else:
            freq_owner = "freq(%d)" % p.freq_owner
        debug("got flag freq (freq=%s)" % (freq_owner))
        # TODO: do something with the flag info
