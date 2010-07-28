""" 
This handles greens in the game. 
TODO: implement 
"""
from subspace.game import c2s_packet, s2c_packet
from logging import debug, info, warn

class Greens:
    
    def __init__(self,player):
        self._player = player
        handlers = {
            s2c_packet.PersonalGreen._id  : self._handle_personal_green,
            s2c_packet.PlayerGreen._id    : self._handle_player_green,
            }
        self._player.add_packet_handlers(**handlers)

    def _handle_player_green(self,raw_packet):
        """ This means someone else picked up a green. """
        p = s2c_packet.PlayerGreen(raw_packet)
        debug("other green pickup (player_id=%d) (prize_number=%d)" % \
                (p.player_id,p.prize_number))
        # TODO: update internal green distribution
    
    def _handle_personal_green(self,raw_packet):
        """ This means that we received some prizes. """
        p = s2c_packet.PersonalGreen(raw_packet)
        debug("self green pickup (prize_number=%d)" % p.prize_number)
        # TODO: process green
