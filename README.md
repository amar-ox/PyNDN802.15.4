# PyNDN802.15.4
A Python-based gateway for IoT with Named Data Networking over IEEE802.15.4

## What is it?
*PyNDN802.15.4* is an implementation that allows a gateway to communication with [Named Data Networking](http://named-data.net/) 
over IEEE802.15.4 in the wireless side, and with [NFD](http://named-data.net/doc/NFD/current/) in the wired side.

This work has been initially designed for NDN-over-ZigBee communications, 
but generalized to the IEEE802.15.4 technology to run experimental NDN-specific operations.

*Work in progress...*

## It implements
* A background process that sends NDN packets from the backbone over IEEE802.15.4 radio
* A simple (experimental) packet compression procedure 

## Required software
* The NDN-Python library [PyNDN2](https://github.com/named-data/PyNDN2)
* The Python serial library [pySerial](https://github.com/pyserial/pyserial)
