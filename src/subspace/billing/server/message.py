"""

"""
from logging import debug, info, warn
from subspace.billing import b2z_packet, z2b_packet

class Messenger:
    
    def __init__(self, biller):
        self.biller = biller
        self._chat_channels = {}
        command_handlers = {
            "chat"          : self._command_chat,
            "message"       : self._command_message,
            "messages"      : self._command_messages, 
            "bshutdown"     : self._command_bshutdown,
            }
        for command, handler in command_handlers.iteritems():
            self.biller.command.set_handler(command, handler)

    def squad(self, sender, squad_name, text):
        debug("squad message, %s -> %s: %s" % (sender, squad_name, text))
        squad_players = self.biller.players.find_players_on_squad(squad_name)
        p = b2z_packet.PlayerPrivateChat()
        p.tail = '(#%s)(%s)>' % (squad_name, sender.name)
        p.tail += text+'\x00'
        for player in squad_players:
            p.player_id = player.id
            player.send(p)
    
    def remote(self, sender, receiver, text):
        debug("remote message, %s -> %s: %s" % (sender, receiver, text))
        p = b2z_packet.PlayerPrivateChat(player_id=receiver.id)
        p.tail = '(%s)>' % sender.name
        p.tail += text+'\x00'
        receiver.send(p)

    def info(self, receiver, text):
        """ This sends the provided text to the specified receiver. """
        debug("info message, Biller -> %s: %s" % (receiver, text))
        p = b2z_packet.Command(player_id=receiver.id)
        p.tail = text+'\x00'
        receiver.send(p)
    
    def _command_chat(self, player, args):
        """
        ?chat=channel[, channel, ... ]
         join the specified chat channels
        ?chat
         list your channels and the players in each channel
        """
        debug("got chat")
        if len(args) > 0: # setting chat channels 
            self._set_player_to_channels(player, args.split(','))
        else:
            self._report_chat_channels(player)

    def _set_player_to_channels(self, player, channels):
        """ This sets the players chat channels. """
        debug("setting player to channels")
        player.chat_channels = []
        for channel in channels:
            players_in_channel = self._chat_channels.setdefault(channel,[])
            if player.name not in players_in_channel:
                players_in_channel.append(player.name)
                player.chat_channels.append(channel)

    def _report_chat_channels(self, player):
        """ This gives the player a report of his chat channels. """
        debug("reporting chat channels")
        if hasattr(player, "chat_channels"):
            for channel in player.chat_channels:
                self.info(player, channel + ": " + \
                    ','.join(name for name in self._chat_channels[channel]))
            
    def _command_message(self, player, args):
        """
        ?message name:message
         leave a message for the named player.
        """
        debug("unhandled ?message")
        pass #TODO: implement

    def _command_messages(self, player, args):
        """
        ?messages
         read any messages left for you
        """
        debug("unhandled ?messages")
        pass #TODO: implement

    def _command_bshutdown(self, player, args):
        """
        ?bshutdown
         terminates the billing server
        """
        warn("%s issued ?bshutdown" % player)
        self.biller.stop()