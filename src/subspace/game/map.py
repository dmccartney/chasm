# Some helpful sources --
#  * asss/src/core/mapdata.c  
#  * http://bitbucket.org/grelminar/asss/src/tip/doc/extended-lvl-format.txt
#
 
from struct import Struct
from StringIO import StringIO
from mmap import mmap, ACCESS_READ
from zlib import compress, decompress
from os import path

#from PIL import Image

class LVL:
    """Class for Handling Subspace Level Files (*.lvl)."""

    def __init__(self, full_path):
        """Loads the specified LVL file"""
        self.full_path = full_path
        _, self.filename = path.split(full_path)
        self.tile_list = []
        #self.tileset = {} # trade speed for grace (dict in lieu of array) 
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
        
    def decompress(self, data):
        with open(self.name, "wb") as f:
            f.write(decompress(data))
            
    def compress(self):
        with open(self.name, "rb") as f:
            return compress(f.read())
    
    def parse(self):
        bmfh = Struct("<2cLLL") # bmp header (b,m,fsize,res1,offbits)
        elvlh = Struct("<4sLL") # elvl header (magic, totalsize, real)
        
        with open(self.name) as f:
            d = mmap(f.fileno(), 0, access=ACCESS_READ)
            # check for bmp tileset
            (b,m,bmp_fsize,res1,offbits) = bmfh.unpack(d.read(bmfh.size))
            if b == 'B' and m == 'M': # there is a tileset bmp
                tdata_offset = bmp_fsize; # tile data starts after bmp
                #self._process_tileset(Image.open(f).copy())
            else: # no tileset, tile/elvl data starts immediately
                res1 = tdata_offset = 0;
            # check for elvl data
            d.seek(res1)
            (e_magic, e_size, e_res) = elvlh.unpack(d.read(elvlh.size))
            if e_magic[::-1] == 'elvl': # there is elvl data
                self._process_elvl(d.read(e_size - elvlh.size))
                if tdata_offset == 0: # if there was no bmfh
                    tdata_offset += e_size # tiles start after elvl chunks
            # done with any bmp or elvl, d[tdata_offset:] is tile data
            d.seek(tdata_offset)
            self._process_tile_list(d.read(d.size() - d.tell()))
            d.close()

    def _process_elvl(self, raw_data):
        """ Reads raw_elvl_chunks as a list of packed elvl chunks """
        elvl_chunkh = Struct("<4sL") # chunk header (type, size)
        data = StringIO(raw_data)
        elvl_chunk = data.read(elvl_chunkh.size)
        while len(elvl_chunk) == elvl_chunkh.size:
            # read chunk header
            (chunk_type, chunk_size) = \
                elvl_chunkh.unpack(elvl_chunk) # u32,u32 (type, size)
            chunk_data = data.read(chunk_size)
            chunk_id = chunk_type[::-1] # reverse it
            if chunk_id in self.elvl_handlers:
                self.elvl_handlers[chunk_id](chunk_data)
            else:
                self.elvl_unhandled.setdefault(
                    chunk_type,[]).append(chunk_data)
            elvl_chunk = data.read(elvl_chunkh.size)

    def _process_tile_list(self, raw_tile_list):
        """ Takes raw_tile_data as packed list of tiles on the LVL """
        tile = raw_tile_list
        while len(tile) >= 4:
            self._process_single_tile(tile[:4])
            tile = tile[4:]

    def _process_single_tile(self, tile_data):
        """ Takes tile_data as single packed tile on the LVL """
        tile_structure = Struct("<L")
        t = tile_structure.unpack(tile_data)[0] # unpack u32
        self.tile_list.append((
            t & 0x03FF, # x
            (t >> 12) & 0x03FF, # y
            t >> 24)) # type

    def _process_elvl_TSET(self, tset_data):
        """ Handles an elvl TSET chunk """
        pass # TODO

    # TODO: a REGN would be better captured in its own class
    def _process_elvl_REGN(self, regn_data):
        """ Handles an elvl REGN chunk """
        regn_chunkh = Struct("<4sL") # chunk header (type, size)
        data = StringIO(regn_data)
        regn_chunk = data.read(regn_chunkh.size)
        while len(regn_chunk) == regn_chunkh.size:
            (chunk_type, chunk_size) = \
                regn_chunkh.unpack(regn_chunk) # u32,u32 (type, size)
            if chunk_size > 0:
                chunk_data = data.read(chunk_size)
            else:
                chunk_data = None
            chunk_id = chunk_type[::-1]
            print "Handling REGN:%s" % (chunk_type)
            self.regn_handlers[chunk_id](chunk_data)
            regn_chunk = data.read(regn_chunkh.size)

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

    def _process_tileset(self, raw_tileset):
        """ Cuts up raw_tileset as a PIL.Image of the LVL tileset """
        for i in range(190):
            tx,ty = 16*(i % 19), 16*(i // 19)
            self.tileset[i+1] = raw_tileset.crop((tx,ty,tx+16,ty+16))

