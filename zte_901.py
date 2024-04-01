import subprocess
import re
import pexpect
from jinja2 import Environment, FileSystemLoader


class User_Input:

    ip_address = input("IP address:")
    b2c_svlan = input("B2C_IPOE_VLAN:")
    b2b_svlan = input("B2B_IPOE_VLAN:")



class SNMP(User_Input):

    snmp_untag_numbers = []
    snmp_tag_numbers = []
    untag_ports = []
    tag_ports = []

    def snmp_untag_ports(self):
        untag_search = subprocess.getoutput(f"snmpwalk -v 2c -c orange {self.ip_address} .1.3.6.1.4.1.3902.3.102.4.1.1.13 | grep {self.b2c_svlan}").split('\n')
        for line in untag_search:
            if line.strip():
                match = re.search(r'(\d+)(?=\s*=\s*STRING)', line)
                if match:
                    self.snmp_untag_numbers.append(match.group(1))

    def untag_ports_list(self):
        for i in self.snmp_untag_numbers:
            try:
                snmp_ports_output = subprocess.getoutput(f"snmpwalk -v 2c -c orange {self.ip_address} .1.3.6.1.4.1.3902.3.102.4.1.1.1.{i}")
                for line in snmp_ports_output.split('\n'):
                    if line.strip():
                        port_match = re.search(r'((?:gei|xgei)-\d+/\d+/\d+/\d+)', line)
                        if port_match:
                            self.untag_ports.append(port_match.group(1))
                            break
            except subprocess.CalledProcessError as e:
                print(f"Не получилось сделать запрос: {e}")

    def snmp_tag_ports(self):
        tag_search = subprocess.getoutput(f"snmpwalk -v 2c -c orange {self.ip_address} .1.3.6.1.4.1.3902.3.102.4.1.1.12 | grep {self.b2c_svlan}").split('\n')
        for line in tag_search:
            if line.strip():
                match = re.search(r'(\d+)(?=\s*=\s*STRING)', line)
                if match:
                    self.snmp_tag_numbers.append(match.group(1))

    def tag_ports_list(self):
        for i in self.snmp_tag_numbers:
            try:
                snmp_ports_output = subprocess.getoutput(f"snmpwalk -v 2c -c orange {self.ip_address} .1.3.6.1.4.1.3902.3.102.4.1.1.1.{i}")
                for line in snmp_ports_output.split('\n'):
                    if line.strip():
                        port_match = re.search(r'((?:gei|xgei)-\d+/\d+/\d+/\d+)', line)
                        if port_match:
                            self.tag_ports.append(port_match.group(1))
                            break
            except subprocess.CalledProcessError as e:
                print(f"Не получилось сделать запрос: {e}")




ports = SNMP()
device = subprocess.check_output(["snmpwalk", "-v", "2c", "-c", "orange", ports.ip_address, ".1.3.6.1.2.1.1.1"]).decode('utf-8')
if "ZTE 5928E-FI" in device:
    ports.snmp_untag_ports()
    ports.untag_ports_list()
    ports.snmp_tag_ports()
    ports.tag_ports_list()

    ip_address = User_Input.ip_address
    vlan_id = User_Input.b2b_svlan
    untag_ports = ports.untag_ports
    tag_ports = ports.tag_ports
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('tmpQinQ.jn2')
    rendered_text = template.render(ip=ip_address,vlan_id=vlan_id, untag_ports=untag_ports, tag_ports=tag_ports)
    print(rendered_text)

else:
    print("СКРИПТ ТОЛЬКО ДЛЯ УЗЛОВ ZTE-5928E-FI!")

