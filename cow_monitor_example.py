"""
    Copyright (c) 2018 Amar Abane (a_abane@hotmail.fr). All rights reserved.
    This file is part of PyNDN802.15.4.
    This code is an example consumer application for monitoring cows movements with NDN over IEEE802.15.4.
"""

import sys
import time
from datetime import datetime
from pyndn import Name
from pyndn import Face
from pyndn import Interest
from pyndn import Data
from pyndn import ContentType
from pyndn import DelegationSet
from pyndn import KeyLocatorType
from pyndn import DigestSha256Signature
from pyndn import Sha256WithRsaSignature
from pyndn import Sha256WithEcdsaSignature
from pyndn import HmacWithSha256Signature
from pyndn.security import KeyType
from pyndn.security import KeyChain
from pyndn.security.identity import IdentityManager
from pyndn.security.identity import MemoryIdentityStorage
from pyndn.security.identity import MemoryPrivateKeyStorage
from pyndn.security.policy import SelfVerifyPolicyManager
from pyndn.util import Blob


key = Blob(bytearray([
       0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15,
      16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
    ]))

class Counter(object):
    def __init__(self, f, face):
        self._callbackCount = 0
        self._file = f
        self._face = face


    def onData(self, interest, data):
        self._file.write('\t'+str(datetime.now().strftime('%X.%f')))
        self._file.write('\t'+str(len(data.wireEncode())))
        self._file.write('\t'+str(len(data.getContent())))
        self._file.write('\t'+str(1))
        print("Received Data: ")
        print(data.getName().toUri())
        print(data.getContent())


	    if KeyChain.verifyDataWithHmacWithSha256(data, key):
            dump("Signature verification: VERIFIED")
        else:
            dump("Signature verification: FAILED")

        self._callbackCount += 1

    def onTimeout(self, interest):
        self._file.write('\t'+str(datetime.now().strftime('%X.%f')))
        self._file.write('\t0')
        self._file.write('\t0')
        self._file.write('\t0')
        print("Tiemout for: ")
        print(interest.getName().toUri())
        self._face.expressInterest(interest, self.onData, self.onTimeout)

        self._callbackCount += 1

def main():
    face = Face()
    current_nbr = 1
    max_nbr = 10
    PGI = 5

    f = open('measurements/app_measurments.txt','a')    
    f.seek(0)
    f.truncate()
    
    cow = 0
    v = 0
    counter = Counter(f, face)
    while current_nbr <= max_nbr:
        name = Name("farm1/cows")
        name.append("1")
        name.append("mvmnt")        
        name.appendSegment(v)
        interest = Interest(name)                
        counter._callbackCount = 0
        f.write('\n'+str(datetime.now().strftime('%X.%f')))
        face.expressInterest(interest, counter.onData, counter.onTimeout)
        
        while counter._callbackCount < 1 :
            face.processEvents()
            time.sleep(0.01)

        time.sleep(PGI)
        current_nbr+=1
        v+=1

    face.shutdown()
    f.close()

main()



