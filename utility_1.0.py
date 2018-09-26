import sys
import os
import codecs
import time
import hashlib
import base64
import binascii

# header strings
DummyString = "_PH_\0\0\0\0\0\0\0\0\0\0\0\0"
TagString = "_DCSI_"			         #1:6
HeaderFormatVersion  = 0x02		    #7
HeaderLength = 0x00				 #8
Reserved1 = 0x00                 #9
TargetEntity = 0x00              #10   07h = BC, 08h = IM
TPSL = 0x00                      #11
TPNS = "G5_\0\0\0\0\0\0"         #12:20
TBSL = 0x00                      #21
TBNS = ''                        #22:42
FIRMWAREVERSIONSTRING = "00"     #43:44
FIRMWAREBRANCHSTRING = "\0\0"    #45:46
FIRMWAREBUILDSTRING = time.strftime("%y%m%d")           #47:52
IMAGELENGTH = 0                  #53:56
IMAGE_MD5_HASH = "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"              #57:72
PADDING_BYTE = '\xFF\xFF\xFF\xFF'        #73:76
HEADER_CHECKSUM = '\0\0\0\0'           #77:80
# header strings #

JTAG_FILE_NAME = ''
CRC_FILE_NAME = ''

# validate arguments 
#let non-numerical values
#if ((sys.argv[2].isdecimal() and len(sys.argv[2]) == 2) == False):
if ((len(sys.argv[2]) == 2) == False):
    print('firmware version is invalid')
    exit()
if ((sys.argv[3].isdecimal() and len(sys.argv[3]) == 2) == False):
    print('release type is invalid')
    exit()
if ((sys.argv[4].isdecimal() and len(sys.argv[4]) == 2) == False):
    print('image version is invalid')
    exit()

#PADD out sub version if needed	(I'm using %BUILD_NUMBER% from Jenkins), this will roll over when the build number exceeds 999
#an option would be to bump the minor number up, leave this for later....
if ((len(sys.argv[5]) == 1) == True):
	print('Padd out 1')
	sys.argv[5] = '00'+sys.argv[5]

if ((len(sys.argv[5]) == 2) == True):
	print('Padd out 2')
	sys.argv[5] = '0'+sys.argv[5]

if ((len(sys.argv[5]) >= 3) == True):
	sys.argv[5] = sys.argv[5][-3:]


#end PADD

if ((sys.argv[5].isdecimal() and len(sys.argv[5]) == 3) == False):
    print('sub image version is invalid')
    exit()
# validate arguments

#write null at 0x200 offset in input file
try:
    file_o = open(sys.argv[1],"rb")
    f = file_o.read()
    file_o.close()
except IOError:
    print ("Error: can\'t find file or read data")
    exit()

f = f[:0x200] + b'\0\0\0\0\0\0\0\0' + f[0x208:]

# write version number from arguments
f = f[:0x1AE] + sys.argv[2].encode("latin") + b'.' + sys.argv[3].encode("latin") + b'.' + sys.argv[4].encode("latin") + b'.' + sys.argv[5].encode("latin") + f[0x1BA:]

# validating input file to get filename
try:
    file = open(sys.argv[1],"rb")
    file.seek(510,0)        #507-8
    BC_IM_DETECT = file.read(2)
    file.seek(507,0)
    BL_SB_OP_DETECT = file.read(2)
    file.close()
except IOError:
    print ("Error: can\'t find file or read data")
    exit()
    
BC_IM_DETECT = BC_IM_DETECT.decode('utf-8')
if(BC_IM_DETECT == 'BC'):
    TargetEntity = 0x07
    TBNS = 'Block_Controller_____'
elif(BC_IM_DETECT == 'IM'):
    TargetEntity = 0x08
    TBNS = 'Infrastructure_Module'
else:
    print("Invalid file found, check input file.")
    exit()

BL_SB_OP_DETECT = BL_SB_OP_DETECT.decode('utf-8')
if(BL_SB_OP_DETECT == 'BL' or BL_SB_OP_DETECT == 'SB' or BL_SB_OP_DETECT == 'OP'):
    print(BC_IM_DETECT + '_' + BL_SB_OP_DETECT + ' image found')
else:
    print("Invalid file found, check input file.")
    exit()

if(BC_IM_DETECT == 'BC' and BL_SB_OP_DETECT != 'SB'):
    if(len(sys.argv) == 7 and (sys.argv[6] == 'G5' or sys.argv[6] == 'G55')):
        JTAG_FILE_NAME = BC_IM_DETECT + '_' + BL_SB_OP_DETECT + '_' + sys.argv[6] + '_JTAG.bin'
        CRC_FILE_NAME = BC_IM_DETECT + '_' + BL_SB_OP_DETECT + '_' + sys.argv[6] + '.bin'
    else:
        print('Enter argument for G5/G55')
        exit()
else: 
    JTAG_FILE_NAME = BC_IM_DETECT + '_' + BL_SB_OP_DETECT + '_JTAG.bin'
    CRC_FILE_NAME = BC_IM_DETECT + '_' + BL_SB_OP_DETECT + '.bin'
# validating input file to get filename 

#generate file without header 
try:
    #file1 = open(sys.argv[1][:-4] + '_crc_JTAG.bin',"wb")
    file1 = open(JTAG_FILE_NAME,"wb")
    file1.write(f)
    file1.close()
    #print('JTAG file generated successfully. Output file : ' + sys.argv[1][:-4] + '_crc_JTAG.bin')
    print('JTAG file generated successfully. Output file : ' + JTAG_FILE_NAME)
except IOError:
    print ("Error: can\'t find file or read data")
    exit()

#calculate CRC32 
buf = (binascii.crc32(f) & 0xFFFFFFFF)

HEADER_CHECKSUM_ = ''
HEADER_CHECKSUM = '%08X' %buf
for i, j in zip(HEADER_CHECKSUM[::2], HEADER_CHECKSUM[1::2]):
    tmp = "%c" %(int(i+j, 16))
    HEADER_CHECKSUM_ = HEADER_CHECKSUM_ + tmp
HEADER_CHECKSUM = HEADER_CHECKSUM_[::-1]
#calculate CRC32#

# calculate image length
IMAGELENGTH_ = "%08x" %(len(f))

IMAGELENGTH__ = ''
for i, j in zip(IMAGELENGTH_[::2], IMAGELENGTH_[1::2]):
    tmp = "%c" %(int(i+j, 16))
    IMAGELENGTH__ = IMAGELENGTH__ + tmp
IMAGELENGTH = IMAGELENGTH__[::-1]
# calculate image length#

# add image len & checksum in file
f = f[:0x200] + IMAGELENGTH.encode("latin") + HEADER_CHECKSUM.encode("latin") + f[0x208:]
# add image len & checksum in file

#formatting header

    
header = "%s%s%c%c%c%c%c%s%c%s%s%s%s%s%s%s%s" % (DummyString,
                                               TagString,HeaderFormatVersion,HeaderLength,Reserved1,TargetEntity,TPSL,TPNS,TBSL,TBNS,
                                               FIRMWAREVERSIONSTRING,FIRMWAREBRANCHSTRING,FIRMWAREBUILDSTRING,IMAGELENGTH,IMAGE_MD5_HASH,PADDING_BYTE,
                                               HEADER_CHECKSUM)

f = header.encode("latin") + f

# calculate MD5 hash, must be calculated at last
IMAGE_MD5_HASH = hashlib.md5(f).hexdigest()
tmp = ''
for i, j in zip(IMAGE_MD5_HASH[::2], IMAGE_MD5_HASH[1::2]):
    tmp = tmp + "%c" %(int(i+j, 16))
    
f = f[:72] + tmp.encode("latin") + f[88:]

# generate file with header
try:
    #file1 = open(sys.argv[1][:-4] + '_crc.bin',"wb")
    file1 = open(CRC_FILE_NAME,"wb")
    file1.write(f)
    file1.close()
    #print('Header added successfully. Output file : ' + sys.argv[1][:-4] + '_crc.bin')
    print('Header added successfully. Output file : ' + CRC_FILE_NAME)
except IOError:
    print ("Error: can\'t find file or read data")
    exit()

#formatting header 
