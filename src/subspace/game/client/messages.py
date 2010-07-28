"""
This handles sending and receiving messages.
"""
from subspace.game import c2s_packet, s2c_packet
from logging import debug, info, warn

class Messenger:
    """ 
    This handles incoming messages and exposes methods for sending.
    add_message_handler() allows registering handlers for incoming messages
    send_message() permits sending of any message.
    send_*_message are convenience methods that use send_message()
    E.g.
    >>> send_message("hello",type=messenger.PUB)
    >>> send_message("pssst",type=messenger.PRIV,target_player_id=player_id)
    >>> send_message(":divine.216:hello",type=messenger.REMOTE)
    >>> send_message("5;hello",type=messenger.CHANNEL)
    >>> send_public_message("hello")
    >>> send_private_message(player_id,"pssst")
    >>> send_remote_message("divine.216","hello") 
    >>> send_channel_message(5,"hello")
    """
    message_types = { 
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
    # using these instead of raw integer makes code more readable
    ARENA, PUB_MACRO, PUB, FREQ, FREQ_PRIV, \
    PRIV, SYS_PRIV, REMOTE, SYS, CHANNEL = range(10)
    
    def __init__(self,player):
        self._player = player
        handlers = {
            s2c_packet.PlayerChatMessage._id  : self._handle_player_chat_message,
            }
        self._player.add_packet_handlers(**handlers)
        self._message_handlers = {} 
    
    def send_message(self,text,type=2,sound=0,target_player_id=-1):
        p = c2s_packet.ChatMessage()
        p.sound = sound
        p.type = type
        p.target_player_id = target_player_id
        p.tail = text + '\x00'
        info('sent  "%s"' % text)
        self._player._send(p)
    
    def send_public_message(self,text,**args):
        self.send_message(text,type=self.PUB,**args)
        
    def send_private_message(self,player_id,text,**args):
        self.send_message(text,type=self.PUB,target_player_id=player_id,**args)
    
    def send_remote_message(self,player_name,text,**args):
        # TODO: check for malformed player names (special chars etc.)
        self.send_message(':'+player_name+':'+text,type=self.REMOTE,**args)
    
    def send_freq_message(self,text,**args):
        self.send_message(text,type=self.FREQ,**args)
    
    def send_channel_message(self,channel_id,text,**args):
        """ Note: until you join a channel, the server will disregard these."""
        self.send_message(str(channel_id)+';'+text,type=self.CHANNEL,**args)
        
    def set_channels(self,channels=[]):
        """ This sets the ?chat channels to the list of channels provided. """
        self.send_public_message("?chat=" + ','.join(channels))
        # TODO: store these to do error checking on send and translate on recv

    def add_message_handler(self,message_type,hnd):
        self._message_handlers.setdefault(message_type,[]).append(hnd)

    def _handle_player_chat_message(self,raw_packet):
        p = s2c_packet.PlayerChatMessage(raw_packet)
        info("got chat message (type=0x%02X): %s" % (p.type, p.message()))
        for hnd in self._message_handlers.get(p.type,[]):
            hnd(p) # we are adults, handlers can have at the actual packet