from logging import debug, info, warn

class Dispatcher:
    """ 
    This handles billing commands.
    """
    
    def __init__(self, billing_server):
        self.billing = billing_server
        self._handlers = {}
        # the ?bhelp command is handled locally
        self.set_handler("bhelp", self._command_bhelp)

    def set_handler(self, command, handler):
        """ 
        This sets the handler for the specified command.
        
        >>> set_handler("chat",chat_command_handler) # ?chat and ?chat=a,b,c 
        """
        self._handlers[command] = handler

    def handle(self, zone, player, issued_command):
        """
        This does the actual handling and dispatching of the commands. 
        This accepts the player address and the command packet.  It translates 
        these into a Player, separates the command from arguments, and then
        checks if the player is authorized before dispatching the command to
        its handler.
        """
        # ensure command begins with one of these
        command_prefix = '*?'
        if issued_command[0] not in command_prefix:
            warn("ignoring command from %s in %s: command '%s' -- doesn't start with '%s'" % \
                (player.name, zone, issued_command, "' or '".join(command_prefix)))
            return
        issued_command = issued_command[1:]
        cmd, args = self._split_args(issued_command)
        debug("command parsed: %s issued %s(%s)" % (player.name, cmd, args))
        if True: # TODO: if is_authorized(cmd,address,player):
            if cmd in self._handlers:
                self._handlers[cmd](player, args)
            else:
                info("unknown command %s from %s in %s" % \
                        (cmd, player.name,zone))
        else:
            warn("player %s tried to issue unauthorized command '%s'('%s')" % \
                    (player.name, cmd, args))

    def _split_args(self, issued_command):
        cmd, args = issued_command, ""     
        separators = "= :"
        for separator in separators:
            split_command = issued_command.split(separator, 1)
            if len(split_command) > 1:
                cmd, args = split_command[0], split_command[1]
                break
        return cmd, args

    def _command_bhelp(self, player, args):
        """ ?bhelp (command) = displays help for command """
        if len(args) > 0:
            cmd = args
        else: # if no command specified, help with this command
            cmd = "bhelp"
        if cmd in self._handlers:
            player.message("command: %s" % cmd)
            player.message("  %s" % self._handlers[cmd].__doc__)
        else:
            player.message("unknown command: %s" % cmd)