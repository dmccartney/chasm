from array import array

class VIE:
    """
    Basic VIE encryption.
    
    I started to clean this up a bit, but then quickly gave up. It is twice- 
    translated encryption, it's supposed to be ugly and so it remains.  That
    said, it should work on all python installs now.
    
    There is lots of room here for performance tweaks.
    
    I wrote these with frequent reference to 
      grel  - asss -- src/core/enc_vie.c
      cycad - http://forums.minegoboom.com/viewtopic.php?p=81456
    """
    version = 0x0001 # this is the identifier for this encryption scheme
    def __init__(self, client_key, server_key):
        """ Prepares the encryption table. """
        # we're simulating c32 integer truncation, so we inspect type sizes
        self._size2 = [t for t in "lih" if array(t).itemsize == 2][0]
        self._size4 = [t for t in "lih" if array(t).itemsize == 4][0]
        r = array("B")
        self._key = k = server_key
        for i in range(260):
            t = (k * 0x834E0B5F) >> 48
            t += t >> 31
            q = 127773
            if k < 0: q *= -1
            k = ((k % q) * 16807) - (t * 2836) + 123
            if (k == 0) or (k & 0x80000000 != 0):
                k += 0x7FFFFFFF
            r.fromstring(chr(k & 0xff)+chr((k >> 8) & 0xff))
        r.byteswap()
        self._table = array(self._size4,r.tostring())

    def encrypt(self, data):
        """ Returns data encrypted. """
        l = len(data)
        data += '\x00' * (4 - (l % 4)) # 4-byte align
        result = array(self._size4)
        w = self._key
        for d,t in zip(array(self._size4,data),self._table):
            w = d ^ (t ^ w)
            result.append(w)
        return result.tostring()[:l]
    
    def decrypt(self, data):
        """ Returns data decrypted. """
        l = len(data)
        data += '\x00' * (4 - (l % 4)) # 4-byte align
        result = array(self._size4)
        w = self._key
        for d,t in zip(array(self._size4,data),self._table):
            result.append(t ^ w ^ d)
            w = d
        return result.tostring()[:l]

def main():
    """
    Preliminary comparison of this python code:
        encrypt took 0.056028 ms
        decrypt took 0.046968 ms
    With the C code from enc_vie.c:
        encrypt took 0.001192 ms
        decrypt took 0.000954 ms

    If looking for speed, this may be a good place to squeeze.
    """
    from random import randint
    from time import time
    count = 10000
    key = randint(-(2**31),(2**31)-1)
    e = VIE(0,key)
    print "key = ",key
    print "table[0]:\t %s" % \
                ' '.join([x.encode("hex") for x in e._table[:1].tostring()])
    input = "\x5a\xf1\x7a\x76\x00\x00\x00\x00\x00\x00\x00\x00"
    print "    input:\t" + ' '.join([x.encode("hex") for x in input])
    t1 = time()
    for round in xrange(count):
        encrypted = e.encrypt(input)
    t2 = time()
    print "encrypt (%d count) took %0.6f ms" % (count,(t2-t1)*1000.0)
    print "encrypted:\t" + ' '.join([x.encode("hex") for x in encrypted])
    t1 = time()
    for round in xrange(count): 
        decrypted = e.decrypt(encrypted)
    t2 = time()
    print "decrypt (%d count) took %0.6f ms" % (count,(t2-t1)*1000.0)
    print "decrypted:\t" + ' '.join([x.encode("hex") for x in decrypted])
    assert decrypted == input

if __name__ == '__main__':
    main()
