from struct import Struct
from logging import debug, warn
from zlib import compress, decompress, crc32
from os import path

# I removed tileset loading to avoid the dependency, for now
#from PIL import Image

class LVL:
    """Class for Handling Subspace Level Files (*.lvl)."""

    def __init__(self, full_path=None):
        """Loads the specified LVL file"""
        self.full_path = full_path
        _, self.filename = path.split(full_path)
        # tile_list as { x1: { y:t, .. }, x2: { y:t, .. } }
        # tile = tile_list[x][y] -- we might instead use x,y as key, TODO: opt
        self.tile_list = {} 
        #self.tileset = {} 
        self.elvl_unhandled = {} # { TYPE:[data1, ...], ... }
        self.elvl_handlers = {
            "TILE" : self._process_tile_list,
            "TSET" : self._process_elvl_TSET,
            "ATTR" : self._process_elvl_ATTR,
            "REGN" : self._process_elvl_REGN,
            }
        self.regn_handlers = {
            "rNAM" : self._process_regn_rNAM, # a name for the region
            "rTIL" : self._process_regn_rTIL, # tile data, defines the region
            "rBSE" : self._process_regn_rBSE, # whether the region is a base
            "rNAW" : self._process_regn_rNAW, # no antiwarp
            "rNWP" : self._process_regn_rNWP, # no weapons
            "rNFL" : self._process_regn_rNFL, # no flag drops
            "rAWP" : self._process_regn_rAWP, # auto-warp
            "rPYC" : self._process_regn_rPYC, # code executed on entry/exit
            }
        self._compressed = None
        self.crc32 = None
        self.file_size = None

    def load(self):
        bmfh = Struct("<ccLLL") # bmp header (b,m,fsize,res1,offbits)
        elvlh = Struct("<4sLL") # elvl header (magic, totalsize, real)
        with open(self.full_path) as f:
            d = f.read()
            self.crc32 = crc32(d) & 0xffffffff
            self.file_size = len(d)
            p = 0
            # check for bmp tileset
            if len(d) < bmfh.size:
                debug("lvl file size too small to contain bmp (%d < %d)" % \
                                (len(d),bmfh.size))
                p = 0
            else:
                (b,m,bmp_fsize,res1,offbits) = bmfh.unpack_from(d[:bmfh.size])
                if b == 'B' and m == 'M': # there is a tileset bmp
                    p = bmp_fsize; # tile data starts after bmp
                    #self._process_tileset(Image.open(f).copy())
                    # for now, we don't load tileset
                else: # no tileset, tile/elvl data starts immediately
                    p = 0
            # check for elvl data
            if len(d) < elvlh.size:
                debug("lvl file size too small to contain elvl (%d < %d)" % \
                                (len(d),elvlh.size))
            else:
                (e_magic, e_size, e_res) = elvlh.unpack_from(d[p:p+elvlh.size])
                if e_magic[::-1] == 'elvl': # there is elvl data
                    p += elvlh.size
                    e_size -= elvlh.size # we already got the elvlh off of the e
                    self._process_elvl(d[p:p + e_size])
                    p += e_size # tiles start after elvl chunks
            # done with any bmp or elvl, d[p:] is tile data
            self._process_tile_list(d[p:])

    def checksum(self, key=0x46692017):
        """ I'm uncertain when the tile-wise checksum is ever used. """
        return self.crc32
        #csum = key
        #for x in range(key % 31,1024,31):
        #    for y in range(key % 32,1024,32):
        #        if x in self.tile_list and y in self.tile_list[x] \
        #          and self.tile_list[x][y] in range(0,160)+[171]:
        #            csum += (key ^ self.tile_list[x][y]) & 0xffffffff
        #return csum                        

    def decompress_to_file(self, data):
        with open(self.full_path, "wb") as f:
            f.write(decompress(data))
            
    def compress_from_file(self, forcing_refresh = False):
        """
        This uses caching to avoid re-reading and re-compressing.
        To skip the cache, set forcing_refresh = True
        """
        if forcing_refresh or self._compressed is None:
            with open(self.full_path, "rb") as f:
                self._compressed = compress(f.read())
        return self._compressed

    def _process_elvl(self, data):
        """ Reads raw_elvl_chunks as a list of packed elvl chunks """
        elvl_chunk_header = Struct("<4sL") # chunk header (type, size)
        while len(data) >= elvl_chunk_header.size:
            # read chunk header
            (chunk_type, chunk_size) = elvl_chunk_header.unpack_from(data)
            chunk_total_size = chunk_size + elvl_chunk_header.size
            if chunk_total_size > len(data):
                warn("invalid elvl specifier (requested=%d > actual=%d)" % \
                            (chunk_total_size, len(data)))
                break
            else:
                chunk_data = data[elvl_chunk_header.size:chunk_total_size]
                id = type[::-1] # fix the endian
                if id in self.elvl_handlers:
                    self.elvl_handlers[id](chunk_data)
                else:
                    self.elvl_unhandled.setdefault(id,[]).append(chunk_data)
                data = data[chunk_total_size:]

    def _process_tile_list(self, raw_tile_list):
        """ Takes raw_tile_data as packed list of tiles on the LVL """
        tile = raw_tile_list
        while len(tile) >= 4:
            self._process_single_tile(tile[:4])
            tile = tile[4:]

    def _process_single_tile(self, tile_data):
        """ Takes tile_data as single packed tile on the LVL """
        tile_structure = Struct("<L")
        t = tile_structure.unpack_from(tile_data)[0] # unpack u32
        x = t & 0x03FF
        y = (t >> 12) & 0x03FF
        tile = t >> 24
        self.tile_list.setdefault(x,{})[y] = tile

    def _process_elvl_TSET(self, tset_data):
        """ Handles an elvl TSET chunk """
        pass # TODO

    # TODO: a REGN would be better captured in its own class
    def _process_elvl_REGN(self, data):
        """ Handles an elvl REGN chunk """
        regn_chunk_header = Struct("<4sL") # chunk header (type, size)
        while len(data) >= regn_chunk_header.size:
            (chunk_type, chunk_size) = \
                regn_chunk_header.unpack_from(data) # u32,u32 (type, size)
            total_chunk_size = chunk_size + regn_chunk_header.size
            if total_chunk_size > len(data):
                warn("invalid regn specifier (requested=%d actual=%d)" % \
                            (total_chunk_size,len(data)))
                break
            else:
                chunk_data = data[regn_chunk_header.size:total_chunk_size]
                chunk_id = chunk_type[::-1]
                if chunk_id in self.regn_handlers:
                    self.regn_handlers[chunk_id](chunk_data)
                    data = data[regn_chunk_header.size:]
                else:
                    debug("unhandled regn=%s" % chunk_id)

    def _process_regn_rNAM(self,rnam_data):
        """ Handles rNAM -- a name for the region """
        pass # TODO

    def _process_regn_rTIL(self,rtil_data):
        """ Handles rTIL -- tile data, defines the region """
        pass # TODO

    def _process_regn_rBSE(self,rbse_data):
        """ Handles rBSE -- whether the region is a base """
        pass # TODO

    def _process_regn_rNAW(self,rnaw_data):
        """ Handles rNAW -- no antiwarp """
        pass # TODO

    def _process_regn_rNWP(self,rnwp_data): 
        """ Handles rNWP -- no weapons """
        pass # TODO

    def _process_regn_rNFL(self,rnfl_data):
        """ Handles rNFL -- no flag drops """
        pass # TODO

    def _process_regn_rAWP(self,rawp_data):
        """ Handles rAWP -- auto-warp """
        pass # TODO

    def _process_regn_rPYC(self,rpyc_data):
        """ Handles rPYC -- code executed on entry/exit """
        pass # TODO

    def _process_elvl_ATTR(self, attr_data):
        """ Handles an elvl ATTR chunk """
        (key,eql,val) = str(attr_data).partition('=')
        if eql == '=': # partition worked
            pass # TODO: do something useful with 'key' and 'val'

# for now, we don't need to load the tileset image
#    def _process_tileset(self, raw_tileset):
#        """ Cuts up raw_tileset as a PIL.Image of the LVL tileset """
#        for i in range(190):
#            tx,ty = 16*(i % 19), 16*(i // 19)
#            self.tileset[i+1] = raw_tileset.crop((tx,ty,tx+16,ty+16))

def main():
    import logging
    logging.basicConfig(level=logging.DEBUG,
            format="%(levelname)-6.6s:<%(threadName)15.15s > %(message)s")
    f = "aswz.lvl"
    lvl = LVL(f)
    lvl.load()
    checksum_key = 0x00000000
    debug("loaded %s, checksum(key=0x%08x) is 0x%08x, tilecount=%d" % \
            (f,checksum_key,lvl.checksum(checksum_key),len(lvl.tile_list)))

if __name__ == '__main__':
    main()
