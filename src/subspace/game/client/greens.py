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
            s2c_packet.SelfGreenPickup._id  : self._handle_self_green_pickup,
            s2c_packet.OtherGreenPickup._id : self._handle_other_green_pickup,
            }
        self._player.add_packet_handlers(**handlers)

    def _handle_other_green_pickup(self,raw_packet):
        p = s2c_packet.OtherGreenPickup(raw_packet)
        debug("other green pickup (player_id=%d) (prize_number=%d)" % \
                (p.player_id,p.prize_number))
        # TODO: update internal green distribution
    
    def _handle_self_green_pickup(self,raw_packet):
        """ This means that we received some prizes. """
        p = s2c_packet.SelfGreenPickup(raw_packet)
        debug("self green pickup (prize_number=%d)" % p.prize_number)
        # TODO: process green
