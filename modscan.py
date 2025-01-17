#!/usr/bin/env python


"""

File: modscan.py
Desc: Modbus TCP Scanner
Version: 0.1

Copyright (c) 2008 Mark Bristow

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version either version 3 of the License, 
or (at your option) any later version.


This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import socket
import array
import optparse
from IPy import IP
import sys
import time

def main():

	p = optparse.OptionParser(	description=' Finds modbus devices in IP range and determines slave id.\nOutputs in ip:port <tab> sid format.',
								prog='modscan',
								version='modscan 0.1',
								usage = "usage: %prog [options] IPRange")
	p.add_option('--port', '-p', type='int', dest="port", default=502, help='modbus port DEFAULT:502')
	p.add_option('--timeout', '-t', type='int', dest="timeout", default=500, help='socket timeout (mills) DEFAULT:500')
	p.add_option('--aggressive', '-a', action ='store_true', help='continues checking past first found SID')
	p.add_option('--function', '-f', type='int', dest="function", default=17, help='MODBUS Function Code DEFAULT:17')
	p.add_option('--data', type='string', dest="fdata", help='MODBUS Function Data.  Unicode escaped "\x00\x01"')
	p.add_option('-v', '--verbose', action ='store_true', help='returns verbose output')
	p.add_option('-d', '--debug', action ='store_true', help='returns extremely verbose output')

	options, arguments = p.parse_args()

	#make sure we have at least 1 argument (IP Addresses)
	if len(arguments) == 1:

		#build basic packet for this test

		"""
		Modbus Packet Structure
		\x00\x00	\x00\x00	\x00\x00	\x11		\x00		<=================>
		Trans ID	ProtoID(0)	Length		UnitID		FunctCode	Data len(0-253byte)
		"""

		#this must be stored in a unsigned byte aray so we can make the assignment later... no string[] in python :(
		rsid = array.array('B')
		rsid.fromstring("\x00\x00\x00\x00\x00\x02\x01\x01")

		#set function
		rsid[7]=options.function

		#add function data
		if (options.fdata):
			aFData = array.array('B')

			#we must decode the escaped unicode before calling fromstring otherwise the literal \xXX will be interpreted
			aFData.fromstring(options.fdata.decode('unicode-escape') )
			rsid += aFData
			
			#update length
			rsid[5]=len(aFData)+2

		#assign IP range
		iprange=IP(arguments[0])
		
		#print friendly user message
		print "Starting Scan..."

		#primary loop over IP addresses
		for ip in iprange:
		
			#print str(ip)+" made it"
			#loop over possible sid values (1-247)
			for sid in range (1, 247):	
			
				#error messaging
				fError=0
				msg = str(ip)+":"+str(options.port)+"\t"+str(sid)
				
				#print "msg="+msg

				#Wrap connect in a try box
				try:
					#socket object instantiation
					s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

					#set socket timeout, value from cmd is in mills
					s.settimeout(float(options.timeout) / float(1000))			

					#connect requires ip addresses in string format so it must be cast
					s.connect((str(ip), options.port))

				except socket.error:
					#clean up
					fError=1
					msg += "\tFAILED TO CONNECT"
					s.close()
					break
				#end try
				

				#send query to device
				try:
					#set slave id
					rsid[6]=sid		

					#send data to device
					print "Send: "+str(rsid)
					s.send(rsid)
					
				except socket.error:
					#failed send close socket
					fError=1
					msg += "\tFAILED TO SEND"
					s.close()
					break
				#end try
				
				try:
					time.sleep(1)
					#recieve data
					data = s.recv(1024)
					
				except socket.timeout:
					fError=1
					msg += "\tFAILED TO RECV"
					break
				#end try

				#examine response
				if data:
					#parse response
					resp = array.array('B')
					resp.fromstring(data)

					if (options.debug):
						print "Recv: "+str(resp)

					#if the function matches the one sent we are all good
					if (int(resp[7]) == int(options.function)):
						print msg
						
						#in aggressive mode we keep going
						if (not options.aggressive):
							break
							
					#If the function matches the one sent + 0x80 a positive response error code is detected
					elif int(resp[7]) == (int(options.function)+128):
						#if debug output message
						msg += "\tPositive Error Response"
						if (options.debug):
							print msg							
					else:
						#if debug output message
						if (options.debug):
							print msg					
				else:
					fError=1
					msg += "\tFAILED TO RECIEVE"
					s.close()
					break
				
			#end SID for
			

			#report based on verbosity
			if (options.verbose and fError):
				print msg
			elif (options.debug):
				print msg
		#end IP for
				
		#close socket, no longer needed
		#s.shutdown(socket.SHUT_RDWR)
		s.close()
		
		print "Scan Complete."

	#bad number of arguments.  print help
	else:
		p.print_help()
	

if __name__ == '__main__':
	try : main()
	except KeyboardInterrupt:
		print "Scan canceled by user."
		print "Thank you for using ModScan"
	except :
		sys.exit()

	