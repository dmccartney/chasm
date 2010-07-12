
from hashlib import sha256 # we use this to hash all passwords in the DB
from datetime import datetime
from logging import debug, info, warn
from threading import Lock
from subspace.billing import z2b_packet, b2z_packet

class Manager:
    """     
    This manages connected zones.
    Zones do three things:
     - connect,
     - announce their abilities, and
     - disconnect
    This zone.Manager keeps track of what zones are connected.  It handles all
    Z2B packets that indicate these zone actions.  It does not handle any 
    player actions. (Recall: "server" or "zone" is the idiomatic name for the
    zone server, and "biller" refers to the billing server.)  Player actions 
    with the biller are handled by player.Manager not this zone.Manager.
    """
    def __init__(self, biller):
        self.biller = biller
        # self._zones will contain {zone_address:Zone}
        self._zones = {}
        packet_handlers = {
            z2b_packet.ZoneConnect._id     : self._handle_zone_connect,
            z2b_packet.ZoneAbilities._id   : self._handle_zone_abilities,
            z2b_packet.ZoneDisconnect._id  : self._handle_zone_disconnect,
            }
        self.biller.add_packet_handlers(**packet_handlers)

    def get_zone(self, zone_address):
        """ 
        This returns the Zone with the given address.
        If no zone exists at that address, it returns None.
        """
        return self._zones.get(zone_address,None)

    def logout_all_zones(self):
        """
        This logs out every zone.
        It is called, for example, when the biller stops.
        """
        debug("treating all zones as logged out")
        for zone in self._zones.itervalues():
                zone.logout()
        self._zones = {}

    def _handle_zone_connect(self, zone_address, raw_packet):
        p = z2b_packet.ZoneConnect(raw_packet)
        zone_name = p.zone_name.rstrip('\x00')
        pwd = p.password.rstrip('\x00')
        zone = Zone(self.biller, zone_address, zone_name, pwd)
        if zone.login():
            debug("zone connection succeeded: name='%s' -- sending ident" % \
                                                        (zone.name))
            ident = b2z_packet.BillingIdentity(identity=self.biller.identity)
            self.biller.send(zone.address, ident)
            self._zones[zone.address] = zone
        else:
            warn("zone connection failed: name='%s', pass='%s' -- %s:%d" % \
                                    ((zone.name, zone.password)+zone_address ))
            self.biller.disconnect_zone(zone_address)
        # TODO: verify zone password, respond etc.

    def _handle_zone_disconnect(self, zone_address, raw_packet):
        p = z2b_packet.ZoneDisconnect(raw_packet)
        zone = self.get_zone(zone_address)
        if zone is not None:
            debug("zone disconnecting: %s" % zone)
            zone.logout()
            del self._zones[zone_address]
        else:
            warn("zone disconnect from unknown address: %s:%d" % zone_address)
        # TODO: verify zone password, respond etc.
    
    def _handle_zone_abilities(self, zone_address, raw_packet):
        p = z2b_packet.ZoneAbilities(raw_packet)
        debug("server has_multicast_chat=%r, has_demographics=%r" % \
              (p.has_multicast_chat(),
               p.has_demographics()))

class Zone:
    """ This is a zone connected to the billing server. """
    
    def __init__(self, biller, address, name, password):
        self.biller = biller
        self.address = address
        self.name = name
        self.password = password
        # these are set upon login()
        self.id = None
        self.logged_in = False
        # these are set in _initialize_session and used in _finalize_session
        self.session_id = None
        self.login_time = None

    def __str__(self):
        """ This gives a more helpful printable view of the zone. """
        s = "name=%s, address=%s:%d" % ((self.name,
                                         self.address[0],
                                         self.address[1]))
        if self.logged_in:
            s = "id="+str(self.id)+","+ s
        return "Zone("+s+")"

    def login(self):
        if self._load_zone():
            self.logged_in = True
            self._initialize_session()
            debug("zone %s login success" % self)
            return True
        else:
            warn("zone login failure")
            return False

    def logout(self):
        if self.logged_in: # this should be superfluous
            self._finalize_session()
        self.biller.players.logout_entire_zone(self)
        self.biller.disconnect_zone(self.address)

    def _load_zone(self):
        """ 
        This fetches the zone from the database.  It returns False if there is 
        no match (either bad password or non-existent zone).  Or it returns
        True if the zone was successfully loaded.
        """ 
        cursor = self.biller.db.cursor()
        cursor.execute(""" 
            SELECT
                ss_zones.id
            FROM
                ss_zones
            WHERE
                ss_zones.name = %s and 
                ss_zones.password = %s
        """, (self.name, sha256(self.password).hexdigest()) )
        zone_result = cursor.fetchone()
        if zone_result is None:
            return False
        else:
            self.id = zone_result[0]
            self._initialize_session()
            return True

    def _initialize_session(self):
        """ 
        This inserts a new session into the zone session log, storing the
        current time as login_time.  It then retrieves the session_id so that,
        later on, _finalize_session() can use this session_id to update the
        session record with the elapsed time of this session.
        """
        self.login_time = datetime.now()
        cursor = self.biller.db.cursor()
        cursor.execute(""" 
            INSERT 
            INTO ss_zone_sessions (zone_id, session_date) 
            VALUES (%s, %s)
        """, (self.id,
              self.login_time ))
        self.session_id = cursor.lastrowid
    
    def _finalize_session(self):
        """ This updates the session record with the elapsed time. """
        if self.logged_in:
            session_length = datetime.now() - self.login_time
            try:
                cursor = self.biller.db.cursor()
                cursor.execute("""
                    UPDATE ss_zone_sessions
                    SET seconds = %s
                    WHERE id = %s
                """, (session_length.seconds, self.session_id))
                debug("session stored for zone %s of %d seconds" % \
                      (self.name, session_length.seconds))
            except:
                warn("Failure recording zone session for %s (session_id=%d)" % \
                     (self.name, self.session_id))
        else:
            debug("not finalizing zone session, not logged_in")