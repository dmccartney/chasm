"""
This module implements the storage and maintenance of players in the biller.
TODO: doc db layout

"""
from hashlib import sha256 # we use this to hash all passwords in the DB
from datetime import datetime, timedelta
from logging import debug, info, warn
from subspace.billing import z2b_packet, b2z_packet

class Manager:
    """ 
    This manages all player activities.  
    It keeps track of what players are logged in, and where.  It handles all
    Z2B packets received from the zone that indicate a player action.  This
    does not handle any zone actions.  (Recall: "zone" is the conventional name
    for the zone server, and "biller" refers to the billing server.)
    """

    def __init__(self, biller):
        self.biller = biller
        # self._players will contain {zone_address:{id:Player(), ..}, ..}
        # this is the ephemeral 'id' that zones use for player sessions
        self._players = {} 
        packet_handlers = {
            z2b_packet.PlayerLogin._id          : self._handle_player_login,
            z2b_packet.PlayerLogout._id         : self._handle_player_logout,
            #z2b_packet.PlayerDemographics._id  : None,
            z2b_packet.PlayerPrivate._id        : self._handle_player_private,
            z2b_packet.PlayerBanner._id         : self._handle_player_banner,
            z2b_packet.PlayerScore._id          : self._handle_player_score,
            z2b_packet.PlayerCommand._id        : self._handle_player_command,
            z2b_packet.PlayerChannel._id        : self._handle_player_channel,
            }
        self.biller.add_packet_handlers(**packet_handlers)
        command_handlers = {
            "find"          : self._command_find,
            "password"      : self._command_password,
            }
        for command, handler in command_handlers.iteritems():
            self.biller.command.set_handler(command, handler)

    def get_player(self, zone, id):
        """ 
        This returns a Player in zone having the provided id.
        It returns None if the specified id does not exist in that zone. 
        """
        return self._players.get(zone.address,{}).get(id)
    
    def find_players_on_squad(self, squad_name):
        """
        This returns a list of all players who are members of squad_name.
        """
        results = []
        squad_name_upper = squad_name.upper()
        zones = self._players.values()
        for zone in zones:
            for player in zone.values():
                if player.squad.upper() == squad_name_upper:
                    results.append(player)
        return results
    
    def find_player_by_name(self, name, zone=None):
        """
        This returns a Player in the zone having the provided name.
        It returns None if the specified name does not exist in that zone.
        If zone is None, then this searches in every connected zone.
        """
        if zone is None:
            zone_addresses = self._players.keys()
        else:
            zone_addresses = [zone.address]
        for address in zone_addresses:
            players = self._players.get(address,{}).values()
            for player in players:
                if player.name.upper() == name.upper():
                    return player
        return None
    
    def logout_entire_zone(self, zone):
        """
        This logs out every player in the specified zone.
        It is called, for example, when a zone disconnects without sending 
        individual player logout packets.  Among other things, this ensures 
        that all initialized player sessions are finalized.
        """
        if zone.address in self._players:
            players = self._players[zone.address].values()
            for player in players:
                player.logout()
            del self._players[zone.address]

    def forget_player(self, zone, id):
        """ 
        This removes the player with id from the zone.
        NOTE: this does not "kick" the player from the zone -- it just makes us
        forget about him, or treat him as having left.  So any later actions
        that use his ephemeral zone-specific ID will fail.
        """
        if zone.address in self._players and id in self._players[zone.address]:
            del self._players[zone.address][id]
    
    def _command_password(self, player, args):
        """ ?password=pw = changes account password to pw """
        debug("%s is trying to set password to %s" % (player, args))
        if len(args) < 1:
            player.message("you failed to specify the new password")
            return
        new_password = args
        if player.set_password(new_password):
            player.message("new password set")
        else:
            player.message("unable to set new password")

    def _command_find(self, player, args):
        """ ?find (player name) = reports player's current zone  """
        debug("%s is trying to find %s" % (player, args))
        # TODO: implement
        target_name = args
        found_player = self.find_player_by_name(target_name)
        if found_player is None:
            # TODO: lookup last session for player of that name, if any
            player.message("%s is not online." % target_name)
        else:
            player.message("%s is in %s" % (target_name, 
                                            found_player.zone.name))

    def _handle_player_login(self, zone_address, raw_packet):
        zone = self.biller.zones.get_zone(zone_address)
        p = z2b_packet.PlayerLogin(raw_packet)
        name = p.name.rstrip('\x00')
        pwd = p.password.rstrip('\x00')
        self._attempt_login(p.is_new_user == 1, zone, p.player_id, name, pwd)
    
    def _attempt_login(self, new_user, zone, player_id, name, password):
        resp = b2z_packet.PlayerLoginResponse(player_id=player_id)
        player = Player(self.biller, zone, player_id, name, password)
        debug("player logging in with name=%s, password=%s" % (name, password))
        resp.name = name
        if not player.login(create_new=new_user):
            debug("player login failed")
            resp.response = b2z_packet.PlayerLoginResponse.BAD_PASSWORD
            if not new_user and player.name_is_available():
                debug("not new user but player name is available")
                resp.response = b2z_packet.PlayerLoginResponse.PROMPT_NEW_USER
        else:
            debug("player login success")
            resp.response = b2z_packet.PlayerLoginResponse.SUCCESS
            if player.is_new_player:
                resp.response = b2z_packet.PlayerLoginResponse.REG_FORM
            for m in ["user_id", "name", "squad", "usage", "banner"]:
                if getattr(player, m) is not None:
                    setattr(resp, m, getattr(player, m))
            for m in ["year", "month", "day", "hour", "minute", "second"]:
                if getattr(player.creation_date, m) is not None:
                    setattr(resp, m, getattr(player.creation_date, m))
            scores = {}
            for m in ["kills", "deaths", "goals", "kill_points", "flag_points"]:
                if getattr(player, m) is not None:
                    scores[m] = getattr(player,m)
            resp.score(**scores)
            # remember this player if it's not a duplicate
            players_in_zone = self._players.setdefault(zone.address,{})
            if player.id in players_in_zone:
                warn("%s has duplicate player id in %s" % (player, zone))
            else:
                players_in_zone[player.id] = player
                debug("%s has entered %s" % (player, zone))
        self.biller.send(zone.address, resp)

    def _handle_player_logout(self, zone_address, raw_packet):
        """ This removes the player who has logged out. """
        zone = self.biller.zones.get_zone(zone_address)
        p = z2b_packet.PlayerLogout(raw_packet)
        player = self.get_player(zone, p.player_id)
        if player is not None:
            player.logout()

    def _handle_player_score(self, zone_address, raw_packet):
        zone = self.biller.zones.get_zone(zone_address)
        p = z2b_packet.PlayerScore(raw_packet)
        player = self.biller.players.get_player(zone, p.player_id)
        if player is None:
            warn("received score update for unknown player_id "+
                 "(maybe a straggler from before the zone reconnected)")
        else:
            debug("%s scores (k=%d, d=%d, g=%d, ks=%d, fs=%d)" % \
                  (player, p.kills, p.deaths, p.goals, 
                   p.kill_points, p.flag_points))
            player.update_score(p)

    def _handle_player_banner(self, zone_address, raw_packet):
        """ This stores a banner from the player in the zone at address. """
        zone = self.biller.zones.get_zone(zone_address)
        p = z2b_packet.PlayerBanner(raw_packet)
        player = self.get_player(zone, p.player_id)
        if player is not None:
            player.set_banner(p.banner)
            debug("received banner for %s in %s" % (player, zone))
        else:
            warn("received banner update from unknown player %d in %s" % \
                        (p.player_id, zone))
    
    def _handle_player_private(self, zone_address, raw_packet):
        # TODO: spam check
        zone = self.biller.zones.get_zone(zone_address)
        p = z2b_packet.PlayerPrivate(raw_packet)
        raw_msg = p.message()
        # p.player_id does not contain the player_id, instead it is 0xffffffff
        # so we parse the private chat for the name
        sender, receiver, msg = self._parse_remote_message(raw_msg)
        if None in [sender, receiver, msg]:
            warn("unable to parse message, ignoring: %s" % raw_msg)
            return
        sender_player = self.find_player_by_name(sender, zone)
        if sender_player is None:
            warn("unknown player_id=%d in %s ignoring sent message: %s" % \
                 (p.player_id, zone, raw_msg))
        else:
            if receiver[0] == '#':
                squad_name = receiver[1:]
                self.biller.message.squad(sender_player, squad_name, msg)
            else:
                receiver_player = self.find_player_by_name(receiver)
                if receiver_player is None:
                    debug("%s is offline, unable to send message from %s" % \
                            (receiver, sender_player))
                    self.biller.message.info(sender_player, 
                                             "%s is not online." % receiver)
                else:
                    self.biller.message.remote(sender_player, receiver_player,
                                               msg)
    
    def _parse_remote_message(self, raw_message):
        """
        Given a raw message of ":receiver:(sender)>message", this returns
        a tuple of 3 strings: sender, receiver, and message.
        
        If this fails, it returns None for all 3. 
        """
        if raw_message[0] != ':':
            return None,None,None
        receiver, rest = raw_message[1:].split(':',1)
        if rest[0] != '(':
            return None, None, None
        sender, message = rest[1:].split(')>',1)
        return sender, receiver, message

    def _handle_player_channel(self, zone_address, raw_packet):
        zone = self.biller.zones.get_zone(zone_address)
        p = z2b_packet.PlayerChannel(raw_packet)
        print p
        debug("player sent channel message")
        pass #TODO

    def _handle_player_command(self, zone_address, raw_packet):
        """
        This takes a player's command packet, cleans up the command text, finds
        the issuing Player and passes it off to the command dispatcher.
        """
        zone = self.biller.zones.get_zone(zone_address)
        p = z2b_packet.PlayerCommand(raw_packet)
        issued_command = p.message()
        player = self.get_player(zone, p.player_id)
        if player is None:
            warn("ignoring command ('%s'): unknown player_id=%d in %s" % \
                 (issued_command, p.player_id, zone))
            return
        debug("player %s issued command %s" % (player.name, issued_command))
        self.biller.command.handle(zone.address, player, issued_command)

class Player:
    """ 
    This is a player in a zone that is attached to the biller.
    TODO: overview doc and db sketch
    """
    
    def __init__(self, biller, zone, 
                            id, name, password):
        self.biller = biller
        self.zone = zone
        self.id = id # this is the id that the zone uses for this player
        self.name = name
        self.password = password
        # these will be set during authenticate_login
        self.logged_in = False
        self.user_id = None # this is a biller id (called billerid in asss)
        self.creation_date = None
        self.banner = ""
        self.squad_id = None # squad and squad_id will be None if no squad
        self.squad = None
        self.squad_owner = False
        self.usage = 0
        self.is_new_player = False
        # this is set in _initialize_session and used in _finalize_session
        self.session_id = None
    
    def __str__(self):
        """ A printable string for this player: "name(id=#)(user_id=#)" """
        s = "%s(id=%d)" % (self.name, self.id)
        if self.user_id is not None:
            s += "(user_id=%d)" % self.user_id
        return s
    
    def login(self, create_new=False):
        """ 
        Returns True on success, False on failure.
        If create_new is True then after a failed login it will attempt to
        create a new account using the player's name and password. 
        """
        if self._load_existing_account():
            return True
        elif create_new:
            debug("Login failed for %s:%s, attempting to create new." %
                  (self.name, self.password))
            return self._create_new_account()
        else:
            return False    
    
    def logout(self):
        """
        If logged in, this stores the player's session.
        It also tells the manager to forget about him.
        """
        if self.logged_in:
            self._finalize_session()
        self.biller.players.forget_player(self.zone, self.id)

    def message(self, text):
        self.biller.message.info(self, text)

    def update_score(self, score):
        """
        This updates the player's to the provided score.
        score is an object containing members
         .kills, .deaths, .goals, .kill_points, and .flag_points
        """
        cursor = self.biller.db.cursor()
        cursor.execute("""
            INSERT INTO ss_player_scores (
                player_id, zone_id ,
                kills, deaths, goals ,
                kill_points, flag_points,
                score_date
                )
            VALUES (
                %s, %s, 
                %s, %s, %s, 
                %s, %s, 
                NOW()
            )
        """, (self.user_id, self.zone.id, 
              score.kills, score.deaths, score.goals,
              score.kill_points, score.flag_points))
        debug("updated scores for player %s in %s" % (self, self.zone))
        return cursor.rowcount == 1

    def set_banner(self, banner):
        """ This stores the player's banner. Returns True on success. """
        self.banner = banner
        cursor = self.biller.db.cursor()
        cursor.execute("""
            INSERT INTO ss_player_banners ( player_id, banner, banner_date )
            VALUES ( %s, %s, NOW() )
        """, (self.user_id, self.banner))
        return cursor.rowcount == 1

    def set_squad(self, squad_name, squad_password):
        """ This sets the player's squad.  Returns True on success. """
        cursor = self.biller.db.cursor()
        cursor.execute("""
            INSERT INTO ss_squad_members (squad_id, player_id, join_date) 
            SELECT squad.id, %s, NOW() FROM ss_squads as squad 
            WHERE squad.name = %s AND squad.password = %s LIMIT 1
        """, (self.user_id, squad_name, sha256(squad_password).hexdigest()))
        return cursor.rowcount == 1

    def set_password(self, password):
        """ This updates the player's password.  Returns True on success. """
        cursor = self.biller.db.cursor()
        cursor.execute("""
            UPDATE ss_players SET password = %s WHERE id = %s LIMIT 1
        """, (sha256(password).hexdigest(), self.user_id))
        return cursor.rowcount == 1

    def send(self, packet):
        """ This sends the packet to the zone """
        self.biller.send(self.zone.address, packet)
    
    def name_is_available(self):
        """
        This checks whether this players name is available for creation.
        """
        cursor = self.biller.db.cursor()
        cursor.execute("""
            SELECT id FROM ss_players WHERE LOWER(name) = LOWER(%s)  
        """, (self.name))
        return cursor.fetchone() is None
    
    def _load_existing_account(self):
        """ 
        This fetches an existing player's account information.  It returns
        False if there is no match (either bad password or non-existent player)
        and it returns True if the player was successfully loaded.
        """ 
        # this query loads a player with the specified password
        # and, if he has one, it gets his squad name
        # and, if he has any, it returns the sum of his usage time
        # and, if he has one, it returns his most recent banner
        cursor = self.biller.db.cursor()
        cursor.execute(""" 
            SELECT
                players.id                     as user_id, 
                players.name                   as name,
                players.creation_date          as creation,
                squads.id                      as squad_id,
                squads.name                    as squad,
                COALESCE((SELECT sum(seconds)
                    FROM ss_player_sessions as sessions 
                    WHERE sessions.player_id = players.id
                                        ),0)   as usage_seconds,
                banners.banner                 as banner,
                COALESCE(scores.kills,0)       as kills,
                COALESCE(scores.deaths,0)      as deaths,
                COALESCE(scores.goals,0)       as goals,
                COALESCE(scores.kill_points,0) as kill_points,
                COALESCE(scores.flag_points,0) as flag_points
            FROM
                ss_players as players
            LEFT JOIN ss_squad_members
                ON ss_squad_members.player_id = players.id
            LEFT JOIN ss_squads as squads
                ON squads.id = (SELECT inner_members.squad_id
                                FROM ss_squad_members as inner_members
                                WHERE inner_members.player_id = players.id
                                ORDER BY inner_members.join_date DESC LIMIT 1)
            LEFT JOIN ss_player_banners as banners
                ON banners.id = (SELECT inner_banners.id 
                                FROM ss_player_banners as inner_banners
                                WHERE inner_banners.player_id = players.id
                                ORDER BY inner_banners.banner_date DESC LIMIT 1)
            LEFT JOIN ss_player_scores as scores
                ON scores.id = (SELECT inner_scores.id 
                                FROM ss_player_scores as inner_scores 
                                WHERE inner_scores.player_id = players.id and 
                                    inner_scores.zone_id = %s 
                                ORDER BY inner_scores.score_date DESC LIMIT 1)
            WHERE
                players.name = %s and 
                players.password = %s
            LIMIT 1
        """, (self.zone.id, self.name, sha256(self.password).hexdigest()) )
        player_result = cursor.fetchone()
        if player_result is None:
            return False
        else:
            self.user_id = player_result[0]
            #assert self.name == player_result[1]
            self.creation_date = player_result[2]
            self.squad_id, self.squad = player_result[3:5]
            self.usage = int(player_result[5])
            self.banner = player_result[6]
            self.kills, self.deaths, self.goals = player_result[7:10]
            self.kill_points, self.flag_points = player_result[10:12]
            #if self.banner is None:
            #    self.banner = ''
            self.logged_in = True
            self._initialize_session()
            return True

    def _create_new_account(self):
        """ 
        This attempts to create a new account.  If this fails (e.g. if the name
        is already taken) then it will return False.  Otherwise, after creating
        the new account, this invokes and returns the outcome of 
        _load_existing_account on the newly created account.
        
        So it returns True only if it successfully created and loaded the new
        account.  Else it returns False.  Thus, call this only after already
        trying (and failing) to _load_existing_account.  Then a False outcome
        will unambiguously indicate that the name already exists, and that the
        password is invalid.  (See authenticate_login()).
        """
        try:
            cursor = self.biller.db.cursor()
            cursor.execute(""" 
                INSERT INTO ss_players (name, password, creation_date) 
                VALUES                 (%s, %s, NOW())
            """, (self.name, 
                  sha256(self.password).hexdigest()))
        except IntegrityError:
            # db ensures unique name
            debug("Unable to create new account %s, name is already taken." % \
                  (self.name))
        self.biller.db.commit()
        self.is_new_player = True
        return self._load_existing_account()        

    def _initialize_session(self):
        """ 
        This inserts a new session into the player session log, storing the
        current time as login_time.  It then retrieves the session_id so that,
        later on, _finalize_session() can use this session_id to update the
        session record with the elapsed time spent in this session.
        """
        self.login_time = datetime.now()
        cursor = self.biller.db.cursor()
        cursor.execute(""" 
            INSERT 
            INTO ss_player_sessions (player_id, zone_id, session_date) 
            VALUES (%s, %s, %s)
        """, (self.user_id,
              self.zone.id,
              self.login_time ))
        self.session_id = cursor.lastrowid
    
    def _finalize_session(self):
        """ This updates the session record with the elapsed time. """
        if self.logged_in:
            session_length = datetime.now() - self.login_time
            try:
                cursor = self.biller.db.cursor()
                cursor.execute("""
                    UPDATE ss_player_sessions
                    SET seconds = %s
                    WHERE id = %s
                """, (session_length.seconds, self.session_id))
                debug("session stored for %s of %d seconds" % \
                      (self.name, session_length.seconds))
            except:
                warn("Failure recording session for %s (session_id=%d)" % \
                     (self.name, self.session_id))

def main():
    import logging
    from subspace.billing.server.biller import Biller
    from subspace.billing.server.zone import Zone
    from MySQLdb import connect, Error
    logging.basicConfig(level=logging.DEBUG,
                        format="<%(threadName)25.25s > %(message)s")
    zone_score_id = 1
    zone_password = "test"
    zone = Zone(('zone.aswz.org', 5000), zone_score_id, zone_password)
    conf = yaml.load(open('/etc/chasm/biller.conf'))
    db_conn = connect(**conf["db"])
    biller = Biller(("0.0.0.0", conf["port"]), conf["name"], db_conn)

    player = Player(biller, zone, 0, 'test_user','test_password')
    print("Logging in with (usr=%s,pwd=%s)" % (player.name, player.password))
    if player.login():
        print("success (squad=%s)" % player.squad)
        player.logout()
    else:
        print("failure")

    player.password = "wrong_password!!"
    print("Logging in with (usr=%s,pwd=%s)" % (player.name, player.password))
    if player.login():
        print("success (squad=%s)" % player.squad)
        player.logout()
    else:
        print("failure")
    db_conn.close()

if __name__ == '__main__':
    main()