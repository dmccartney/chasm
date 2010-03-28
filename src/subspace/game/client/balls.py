"""
This handles the flags in the game.
#TODO: implement
"""
from subspace.game import c2s_packet, s2c_packet
from logging import debug, info, warn

class BallGame:
    """
    This handles all ball packets to implement the basics of the ball game.
    """
    def __init__(self,player):
        self._player = player
        handlers = {
            s2c_packet.BallPosition._id     : self._handle_ball_position,
            }
        self._player.add_packet_handlers(**handlers)
        
    def _handle_ball_position(self,raw_packet):
        p = s2c_packet.BallPosition(raw_packet)
        #debug("got ball (id=%d) position (%d,%d) moving (%d,%d)" % \
        #            (p.id,p.x,p.y,p.dx,p.dy))
        # TODO: do something with this and with its p.time (stateful logic)

