
class WeaponTypes:
        """ Some constants to help translate .type """
        NoWeapon, Bullet, BouncingBullet, Bomb, \
        ProximityBomb, Repel, Decoy, Burst, Thor = range(9)
        NAMES = ["No Weapon", "Bullet", "Bouncing Bullet", "Bomb", 
                  "Proximity Bomb", "Repel", "Decoy", "Burst", "Thor"]

def has_weapon(raw_weapon_info):
        """ 
        This quickly checks if the type is non-zero.
        It is a convenience function for weapon packet handlers to call before
        parsing the whole weapon_info component via WeaponInfo(). 
        """
        return raw_weapon_info & 0x1f <> 0
            
class WeaponInfo:
    """
    This handles interpretation of the 16 bits of weapon info.
    This weapon info is in 
        c2s_packet.PositionWeapon.weapon_info
        s2c_packet.PlayerPositionWeapon.weapon_info
    It can both interpret via init() and construct via raw(), the condensed
    16-bits.
    
    You can give it a raw 16 bits to tease out the components 
    >>> w_info = WeaponInfo(0b100000000001)
    >>> w_info.type, w_info.multifire
    (1, 1)
    >>> WeaponInfo.Types.NAMES[w_info.type]
    "Bullet"
    
    Or use it to build the 16 bits
    >>> w_info = WeaponInfo()
    >>> w_info.type = 1
    >>> w_info.multifire = 1
    >>> w_info.level = 1
    >>> bin(w_info.raw())
    "0b100000000001"
    
    To quickly check if weapon_info.type == Types.NoWeapon (i.e. to see if you
    need to bother parsing the whole thing), see the has_weapon() method of
    both c2s_packet.PositionWeapon and s2c_packet.PlayerPositionWeapon
    """

    type = 0 # 0 - 8 (see class Types)
    level = 0 # this is the weapon level (valid when type is in (1,2,3,4))
    # the next 3 are only meaningful if it's a bomb (when type is in (3,4))
    shrap_bounce = 0 # whether the shrapnel will bounce off walls etc.
    shrap_level = 0 # the bullet weapon level of the shrapnel
    shrap_count = 0 
    # this is only valid if the weapon type is in (1,2)
    multifire = 0
    
    PART_SIZES = [ # the number of bits per item
        ("type",5), ("level",2), ("shrap_bounce",1),
        ("shrap_level",2), ("shrap_count",5), ("multifire",1)]
    
    def __init__(self, raw_weapon_info = None):
        if raw_weapon_info is not None:
            self._parse_weapon_info(raw_weapon_info)
    
    def __str__(self):
        if self.type is WeaponTypes.NoWeapon:
            return "No Weapon"
        if self.type in (WeaponTypes.Repel, WeaponTypes.Decoy, \
                         WeaponTypes.Burst, WeaponTypes.Thor):
            return WeaponTypes.NAMES[self.type]
        if self.type in (WeaponTypes.Bomb, WeaponTypes.ProximityBomb):
            return "L%d %s (%d %sL%d Shrapnel)" % (self.level + 1,
                                 WeaponTypes.NAMES[self.type],
                                 self.shrap_count,
                                 "Bouncing " if self.shrap_bounce == 1 else "",
                                 self.shrap_level + 1)
        else:
            return "L%d %s%s" % (self.level + 1, 
                                 "Multifire " if self.multifire else "",
                                 WeaponTypes.NAMES[self.type])

    def _parse_weapon_info(self, raw_weapon_info):
        for name, length in self.PART_SIZES:
            value = raw_weapon_info & ((1 << length) - 1)
            setattr(self, name, value)
            raw_weapon_info >>= length
    
    def raw(self):
        raw_weapon_info = 0
        for name, length in self.PART_SIZES[::-1]:
            raw_weapon_info <<= length
            raw_weapon_info |= getattr(self, name) & ((1 << length) - 1)
        return raw_weapon_info

def test_weapon_info():
    # first, test parsing a raw weapon_info of 0x8001
    raw_weapon_info = 0x8001
    interpreted_w_info = WeaponInfo(raw_weapon_info)
    print interpreted_w_info
    
    # next, test logical construction of same
    constructed_w_info = WeaponInfo()
    constructed_w_info.type = 1
    constructed_w_info.multifire = 1
    print constructed_w_info
    
    assert constructed_w_info.raw() == interpreted_w_info.raw()

if __name__ == '__main__':
    print WeaponInfo(0x0005)
    test_weapon_info()