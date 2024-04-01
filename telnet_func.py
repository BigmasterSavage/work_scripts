import pexpect
import ipaddress
import logging
import re



logger = logging.getLogger()


class TelnetAuthException(Exception): # Exception for SNMP request
    def __init__(self,ip,login,error):
        self.message = f'{ip}: Error authentification {login}: {error}'
    def __str__(self):
        return self.message


class Telnet_conn:

    def __init__(self,ip,login,password,promt,next_page,start_command=None):
        self.ip = ip
        self.login = login
        self.password = password
        logger.info(f'{self.ip} : Connecting via Telnet as {login}')
        self.connection = self.authentification()
        self.promt = promt
        self.next_page = next_page
        self.start_command = start_command
        if start_command:
            logger.info(f'Send command: {start_command}')
            self.telnet_send_command(start_command)

    

    def authentification(self):
        logger.info(f'Connection to {self.ip}')
        logger.info(f'{self.ip} : Login as {self.login}')
        connection = pexpect.spawn(f'telnet {self.ip}')
        connection.expect('[Uu]ser[Nn]ame:')
        connection.sendline(self.login)
        connection.expect('[Pp]ass[Ww]ord:')
        connection.sendline(self.password)
        index_out = connection.expect(['#','>',pexpect.TIMEOUT])
        if index_out != 2:
            logger.info(f'{self.ip} : Authentification access!')
            return connection
        else:
            print(connection.before.decode('utf-8'))
            raise TelnetAuthException
        
    def telnet_send_command(self,command): 
        logger.info(f'{self.ip} : Send command {command}')
        self.connection.sendline(command)
        out = ''
        while True:
            index = self.connection.expect([self.promt,pexpect.TIMEOUT,self.next_page])
            if index == 2:
                out += self.connection.before.decode('utf-8')
                self.connection.sendline('\n')
                index = self.connection.expect([self.promt,self.next_page,pexpect.TIMEOUT])              
            else:
                out += self.connection.before.decode('utf-8')
                break
        return out
    
    def close_connection(self):
        logger.info(f'{self.ip} : Close telnet connection.') 
        self.connection.close()


            
        


