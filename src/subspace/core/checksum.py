"""
aborted implementation of checksums

TODO: make these work

    written with frequent reference to 
      grel  - asss -- src/core/enc_vie.c
      catid - merv -- src/checksum.cpp
      cycad - http://forums.minegoboom.com/viewtopic.php?p=81456
"""
def exe_checksum(key):
    """ nonfunctional (vie exe checksum) """
    exe_samples = {
        0xc98ed41f : 
            [(0x0003e1bc,0x42435942),(0x1d895300,0x6b5c4032),
             (0x00467e44,0x516c7eda),(0x8b0c708b,0x6b3e3429),
             (0x560674c9,0xf4e6b721),(0xe90cc483,0x80ece15a),
             (0x728bce33,0x1fc5d1e6),(0x8b0c518b,0x24f1a96e),
             (0x030ae0c1,0x8858741b)],
        0x9c15857d : 
            [(0x0424448b,0xcd0455ee),(0x00000727,0x8d7f29cd)],
        0x824b9278 : 
            [(0x00006590,0x8e16169a),(0x8b524914,0x82dce03a),
             (0xfa83d733,0xb0955349),(0xe8000003,0x7cfe3604)],
        0xe3f8d2af : 
            [(0x2de85024,0xbed0296b),(0x587501f8,0xada70f65)],
        0xcb54d8a0 : 
            [(0x0f000001,0x330f19ff),(0x909090c3,0xd20f9f9f),
             (0x53004add,0x5d81256b),(0x8b004b65,0xa5312749),
             (0xb8004b67,0x8adf8fb1),(0x8901e283,0x8ec94507),
             (0x89d23300,0x1ff8e1dc),(0x108a004a,0xc73d6304),
             (0x0043d2d3,0x6f78e4ff)],
        0x045c23f9 :
            [(0x47d86097,0x7cb588bd),(0x00009286,0x21d700f8),
             (0xdf8e0fd9,0x42796c9e),(0x8b000003,0x3ad32a21)],
        0xb229a3d0 : 
            [(0x0047d708,0x010b0a91)],
        0x466e55a7 :
            [(0xc7880d8b,0x44ce7067),(0x000000e4,0x923a6d44),
             (0x640047d6,0xa62d606c),(0x2bd1f7ae,0x2f5621fb),
             (0x8b0f74ff,0x2928b332)],
        0x62cf369a : [] }

    f = lambda part,(a,o): (part + (a | key)) ^ (o & key)
    return sum(reduce(f,d,offset) \
               for offset,d in exe_samples.iteritems()) & 0xffffffff

def lvl_checksum(self):
    pass # TODO: implement

def settings_checksum(key):
    pass # TODO: implement

def main():
    key = 0x12345678
    print "exe checksum(key=0x%08x) = 0x%08x" % (0,exe_checksum(0))
    print "exe checksum(key=0x%08x) = 0x%08x" % (key & 0xffffffff,
                                                 exe_checksum(key))

if __name__ == '__main__':
    main()