"""
TODO: doc squad manager / db scheme
TODO: commands -- list, grant, kick, password, dissolve 

tables--
    ss_squads:
        *id
        name
        password
        owner_player_id*

    ss_squad_members:
        *id
        squad_id*
        player_id*
        join_date

"""

from hashlib import sha256

class Manager(object):
    """ This manages squad creation, ownership, and membership. """
     
    def __init__(self, biller):
        self.biller = biller
        command_handlers = {
            "squadcreate"     : self._command_create,
            "squaddissolve"   : self._command_dissolve,
            "squadpassword"   : self._command_password,
            "squadkick"       : self._command_kick,
            "squadgrant"      : self._command_grant,
            "squadlist"       : self._command_list,
            "squadjoin"       : self._command_join,
            "squadleave"      : self._command_leave, 
            "squadowner"      : self._command_owner,
            "squad"           : self._command_squad,
            }
        for command, handler in command_handlers.iteritems():
            self.biller.command.set_handler(command, handler)

# these are commands for the owner (or would-be owner)
    def _command_create(self, player, args):
        """ ?squadcreate=name:password = Create a new squad """
        if len(args) < 3:
            player.message("invalid specification of squad name and password")
            return
        try:
            squad_name, squad_password = args.split(':',1)
        except ValueError:
            player.message("invalid specification of squad name and password")
            return
        if self._create_squad(player, squad_name, squad_password):
            player.message("squad successfully created.")
        else:
            # TODO: specify whether it already exists or had some other problem
            player.message("unable to create squad")
    
    def _command_dissolve(self, player, args):
        """ ?squaddissolve = completely get rid of squad """
        # set all members to squadless, then ???
        pass # TODO: implement
    
    def _command_password(self, player, args):
        """ ?squadpassword=(password) = set squad password """
        pass # TODO: implement
    
    def _command_kick(self, player, args):
        """ ?squadkick=(player name) = kick player off of current squad """
        pass # TODO: implement
    
    def _command_grant(self, player, args):
        """ ?squadgrant (player name) = gives ownership to that player """
        pass # TODO: implement
    
    def _command_list(self, player, args):
        """ 
        ?squadlist = lists all players on current squad
        ?squadlist (squad name) = list all players on specified squad
        """
        if len(args) > 0:
            squad_name = args
        
        pass # TODO: implement

# these are for squad members (or would-be members)
    def _command_join(self, player, args):
        """ ?squadjoin=name:password = joins an existing squad """
        if len(args) < 3:
            player.message("invalid specification of squad name and password")
            return
        try:
            squad_name, squad_password = args.split(':',1)
        except ValueError:
            player.message("invalid specification of squad password")
            return
        if player.set_squad(squad_name, squad_password):
            player.message("squad successfully joined.")
        else:
            # TODO: specify whether squad DNE or just bad password
            player.message("no such squad or bad password")

    def _command_leave(self, player, args):
        """ ?squadleave = leaves current squad """
        cursor = self.biller.db.cursor()
        cursor.execute("""
            INSERT INTO ss_squad_members ( squad_id, player_id, join_date )
            VALUES ( NULL, %s, NOW() )
        """, (player.user_id))
        player.message("now you are not on a squad")
    
# these are public commands
    def _command_owner(self, player, args):
        """ ?squadowner (squad name) = reports the name of squad's owner """
        if len(args) < 1:
            player.message("you must specify a squad name")
            return
        squad_name = args
        cursor = self.biller.db.cursor()
        cursor.execute("""
            SELECT player.name 
            FROM ss_squads as squad
            LEFT JOIN ss_players as player
                ON player.id = squad.owner_player_id
            WHERE squad.name = %s
        """, (squad_name))
        res = cursor.fetchone()
        if res is None:
            player.message("unable to find squad named '%s'" % squad_name)
        else:
            player.message("owner is %s" % res[0])

    def _command_squad(self, player, args):
        """ ?squad (player name) = reports the player's current squad """
        if len(args) < 1:
            player.message("you must specify a player name")
            return
        player_name = args
        cursor = self.biller.db.cursor()
        cursor.execute("""
            SELECT
                squads.name                    as squad
            FROM
                ss_players as players
            LEFT JOIN ss_squad_members
                ON ss_squad_members.player_id = players.id
            LEFT JOIN ss_squads as squads
                ON squads.id = (SELECT inner_members.squad_id
                                FROM ss_squad_members as inner_members
                                WHERE inner_members.player_id = players.id
                                ORDER BY inner_members.join_date DESC LIMIT 1)
            WHERE
                players.name = %s
            LIMIT 1
        """, (player_name))
        res = cursor.fetchone()
        if res is None or res[0] is None:
            player.message("no squad for player '%s'" % player_name)
        else:
            player.message("squad for %s: %s" % (player_name, res[0]))

    def _create_squad(self, owner, squad_name, password):
        """ This attempts to create a squad. It returns True on success. """
        cursor = self.biller.db.cursor()
        cursor.execute("""
            INSERT INTO ss_squads ( name, password, owner_player_id )
            VALUES ( %s, %s, %s )
        """, (squad_name, sha256(password).hexdigest(), owner.user_id))
        return cursor.rowcount == 1
