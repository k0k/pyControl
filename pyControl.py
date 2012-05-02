#!/bin/env python

"""
Just another python script to send commands to any host via ssh.
Copyright (C) 2008 Wilmer Jaramillo M. <wilmer@fedoraproject.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/license

Command line options:
-f |--file		file with ips address.
-v |--verbose		show much more info.

INSTALL:
You only must install paramiko module using the next command as root:
# easy_install paramiko
"""

__version__ = "0.3"
__copyright__ = "Wilmer Jaramillo M."
__date__ = "(#) May 25 2008"
copyright = "Version %s / %s, %s" % (__version__, __copyright__, __date__)

import os
import re
import sys
import time
import getopt
import popen2
import paramiko  
# RHEL4 - import sqlite
from pysqlite2 import dbapi2 as sqlite
from socket import error as SocketError
from paramiko import SSHClient, AutoAddPolicy

''' Declaraciones de variables de conexion '''
client_port = 22
client_user = '<ROOT_ACCOUNT>'
client_password = '<PASS>'

''' Variables de estado '''
host_auth_failed_count, host_found_count, host_not_found_count, host_refused_count, ip_count = (0, 0, 0, 0, 0)
host_found, host_not_found, host_refused = ([], [], [])
verbose='False'
flag, ips_f = ('', '')
sqlite_f = 'pycontrol.sqlite'
# Comandos para ejecutar en las maquinas remotas
commands=('ps ax', 'ls -a')

''' Declaracion de funciones. '''
def func_verbose():
	""" 
	Cuando se ejecuta este script con la opcion -v genera la salida completa de los
	comandos a ejecutar, en caso contrario solo los print
	"""
	for line in stdout:
		print 'ssh-> ' + line.strip('\n')

def usage():
	""" Muestra informacion y ayuda de ejecucion """
	print '%s %s' % (os.path.basename(sys.argv[0]),copyright)
	print 'Usage: %s -f[--file] -h[--help] -v[--verbose]'  % os.path.basename(sys.argv[0])
	sys.exit(0)

def root_check():
	if not os.geteuid() == 0:
		print "[Acceso Denegado]: Necesita ser \"root\" para ejecutar %s" % os.path.basename(sys.argv[0])
		sys.exit(0)

def sqlite_connect():
	global sql, dbConnect
	dbConnect = sqlite.connect(sqlite_f)
	sql = dbConnect.cursor()

def files_check():
	if ips_f == '':
		usage()
	if not os.path.isfile(ips_f):
		print '[-] El archivo %s no existe' % ips_f
		sys.exit(1)
	if not os.path.isfile(sqlite_f):
		print '[-] El archivo %s no existe.' % sqlite_f
		print '-> Generando tablas en %s...' % sqlite_f,
		sqlite_connect()
		sql.execute('''CREATE TABLE host_f(iphost VARCHAR(15))''')
		sql.execute('''CREATE TABLE host_r(iphost VARCHAR(15))''')
		dbConnect.commit()
		print 'listo.\n'

''' Opciones '''
try:
	opts, args = getopt.getopt(sys.argv[1:], "hf:v", ["help", "file="])
except getopt.GetoptError:
	''' Muestra informacion y sale: '''
	usage()
	sys.exit(1)
for o, a in opts:
	if o == "-v":
		verbose = True
        if o in ("-h", "--help"):
       		usage()
		sys.exit(0)
        if o in ("-f", "--file"):
       		ips_f = a


''' Archivo de bitacora	'''
paramiko.util.log_to_file('pycontrol.log')
root_check()
files_check()
sqlite_connect()
for ip in open(ips_f).readlines():
	''' Cuenta el numero de direcciones en el archivo '''
	ip_count += 1
	ip = ip.replace('\n', '')
	''' Se verifica el nro de octetos y que sean numeros,
	    TODO: verificar que el rango de cada octeto sea de 1-254 '''
	if re.match("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
		try:
			print '--> Conectando a %s...' % ip
			client = paramiko.SSHClient()
			client.set_missing_host_key_policy(AutoAddPolicy())
			client.connect(ip, port=client_port, timeout=5, username=client_user, password=client_password)
			''' Almacena la ip en listas y se cuenta el error para generar informacion de estado.
			    python no llega a este seccion del programa si hay una exception '''
			host_found.append(ip)
			sql.execute("INSERT INTO host_f values ('%s')" % ip) 
			dbConnect.commit()
			
			''' Seccion de ejecucion de comandos '''
			for x in enumerate(commands):
				print '----> Ejecutando comando Nro. %s: %s' % (x[0], x[1])
				stdin, stdout, stderr = client.exec_command(x[1])
				if verbose == True:
					func_verbose()
		except paramiko.SSHException:
			''' Almacena la ip en listas y se cuenta el error para generar informacion de estado '''
       			print '[-] --->> %s: Conexion rechazada: Error desconocido.' % ip
	    		host_refused.append(ip)
			sql.execute("INSERT INTO host_r values ('%s')" % ip) 
		except	paramiko.AuthenticationException:
			print '[-] --->> Conexion rechazada: Claves invalidas'
	    		host_refused.append(ip)
			sql.execute("INSERT INTO host_r values ('%s')" % ip) 
		except SocketError:
			print '[-] --->> Conexion rechazada: Servicio no disponible en %s' % ip
	    		host_refused.append(ip)
			sql.execute("INSERT INTO host_r values ('%s')" % ip) 
    		except	paramiko.BadHostKeyException:
	    		print '--->> Conexion rechazada: Las llaves(keys) no pueden ser verificadas.'
	    		host_refused.append(ip)
			sql.execute("INSERT INTO host_r values ('%s')" % ip) 
#		finally:
		    	# client.close()

	dbConnect.commit()
sql.close()
# Eliminar las siguientes lineas despues de ajustar la resolucion de ips
print '\n---'
a = ["%s" % w for w in host_found]
b = ["%s" % w for w in host_refused]
print 'IPS Encontradas: %s' % a
print 'IPS NO Encontradas: %s' % b
print '\n%s estaciones procesadas.' % ip_count
print '%s Cantidad de estaciones encontradas.' % len((host_found))
print '%s Cantidad de estaciones rechazadas.' % len((host_refused))
sys.exit(0)
