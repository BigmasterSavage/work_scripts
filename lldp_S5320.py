import pexpect
import re
import subprocess
import time


class User_Input:

    telnet_host = input("Введите IP адрес узла: ")
    username = input("Username: ")
    password = input("Password: ")


class Huawei_S5320(User_Input):

    lldp_output = None
    port_info_list = None
    device_info = None

    def get_lldp_neighbor_info(self, prompt='>'):
        """
        Получение вывода LLDP
        """
        try:
            # Подключение Telnet
            telnet = pexpect.spawn(f'telnet {self.telnet_host}', timeout=30)
            telnet.expect('Username:')
            telnet.sendline(self.username)
            telnet.expect('Password:')
            telnet.sendline(self.password)
            # LLDP
            telnet.expect(prompt)
            telnet.sendline('display lldp neighbor')
            full_output = ""
            more_trigger = '---- More ----'
            while True:
                index = telnet.expect([prompt, more_trigger, pexpect.EOF, pexpect.TIMEOUT])
                # Считываем вывод
                full_output += telnet.before.decode()
                if index == 0:  # Если достигли приглашения командной строки, выходим из цикла
                    break
                elif index == 1:  # Если видим '---- More ----', нажимаем пробел для продолжения
                    telnet.send(' ')
                else:  # В таймаута также прерываем цикл
                    break
            # Закрытие соединения
            telnet.sendline('quit')
            telnet.close()
            self.lldp_output = full_output
            return full_output
        except Exception as e:
            return f"Ошибка: {e}"

    def extract_system_info(self):
        """
        Получение полей с информацией из вывода LLDP
        """
        # Регулярные выражения для извлечения нужной информации для всех портов
        port_info_pattern = (
            r'(\w+Ethernet[0-9/]+)\s+has.*?'  # Порт
            r'System name\s*:\s*(.+?)\s*'  # Имя системы
            r'System.*?'  # Пропуск несвязанной информации
            r'Management address value\s*:\s*(\S+)'  # Адрес управления
        )
        all_port_info = re.findall(port_info_pattern, self.lldp_output, re.DOTALL)
        # Формирование списка словарей для каждого порта
        port_info_list = []
        for port_info in all_port_info:
            port_info_dict = {
                "Port": port_info[0],
                "System Name": port_info[1],
                "Management Address": port_info[2]
            }
            port_info_list.append(port_info_dict)
        self.port_info_list = port_info_list
        return port_info_list

    def query_snmp_for_ips(self):
        """
        Опрос устройств по SNMP для получения корректной информации об устройствах
        """
        device_info = {}
        for port_info in self.port_info_list:
            port = port_info.get("Port")
            ip_address = port_info.get("Management Address")
            if ip_address:
                try:
                    result = subprocess.check_output(["snmpwalk", "-v", "2c", "-c", "orange", ip_address, ".1.3.6.1.2.1.1.1"])
                    # Добавляем информацию о устройстве в словарь
                    if port not in device_info:
                        device_info[port] = {}
                    device_info[port][ip_address] = result.decode()
                except subprocess.CalledProcessError as e:
                    print(f"Ошибка при опросе {ip_address}: {e}")
                    if port not in device_info:
                        device_info[port] = {}
                    device_info[port][ip_address] = "Ошибка опроса"
        self.device_info = device_info
        return device_info


class Des_3200 (Huawei_S5320):

    devices_list = []
    test_interfaces_info = {}

    def distribute_info(self, info):
        """
        Поиск подходящих устройств
        """
        for interface, details in info.items():
            for ip, description in details.items():
                if "DES-3200" in description:
                    self.devices_list.append({interface: {'IP': ip, 'Description': description}})

    def create_test_interfaces(self):
        """
        Создание тестовых интерфейсов
        """
        for device in self.devices_list:
            for interface, device_info in device.items():
                ip = device_info['IP']
                # Подключение к устройству через telnet
                child = pexpect.spawn(f"telnet {ip}")
                child.expect('UserName:')
                child.sendline(str(self.username))
                child.expect('PassWord:')
                child.sendline(str(self.password))

                # Выполнение команд создания интерфейса
                child.sendline('create vlan test tag 2666')
                child.sendline('create ipif test_ipif 0.0.0.0/0 test')
                child.sendline('config ipif test_ipif dhcp')
                child.sendline('logout')

        time.sleep(30)  # Ждем, пока тестовые интерфейсы получат IP

    def collect_interfaces_info(self):
        """
        Сбор информации о тестовых интерфейсах
        """
        for device in self.devices_list:
            for interface, device_info in device.items():
                ip = device_info['IP']
                child = pexpect.spawn(f"telnet {ip}")
                child.expect('UserName:')
                child.sendline(str(self.username))
                child.expect('PassWord:')
                child.sendline(str(self.password))

                # Собираем вывод
                child.sendline('show ipif test_ipif')
                while True:
                    index = child.expect(['prompt_regex', pexpect.TIMEOUT, pexpect.EOF, 'SPACE n Next Page'])
                    if index == 0:
                        # Если нашли приглашение командной строки, прерываем цикл
                        break
                    elif index == 3:
                        # Если видим 'SPACE n Next Page', отправляем пробел
                        child.send(' ')
                    else:
                        # В случае таймаута также прерываем цикл
                        break
                output = child.before.decode()

                # Обработка вывода для получения IP-адреса
                ip_address = 'No IP'
                for line in output.split('\n'):
                    ip_match = re.search(r'([0-9\.\/]+)\s+\(DHCP\)', line)
                    if ip_match:
                        ip_address = ip_match.group(1)
                        break
                # Добавляем инфу в self.test_interfaces_info
                self.test_interfaces_info[ip] = {'Received IP': 'Yes' if ip_address != 'No IP' else 'No', 'IP Address': ip_address}

                child.sendline('logout')

    def remove_test_interfaces(self):
        """
        Удаление тестовых интерфейсов
        """
        for device in self.devices_list:
            for interface, device_info in device.items():
                ip = device_info['IP']
                child = pexpect.spawn(f"telnet {ip}")
                child.expect('UserName:')
                child.sendline(str(self.username))
                child.expect('PassWord:')
                child.sendline(str(self.password))
                child.sendline('delete ipif test_ipif')
                child.sendline('delete vlan test')
                child.sendline('logout')




#---------ВЫПОЛНЕНИЕ-----------------
huawei = Des_3200()
huawei.get_lldp_neighbor_info()
huawei.extract_system_info()
huawei.query_snmp_for_ips()
for key, value in huawei.device_info.items():
    print(f"{key}: {value}")
input("\nEnter - показать выборку свитчей (пока только DES-3200)...")
huawei.distribute_info(huawei.device_info)
for device in huawei.devices_list:
    print(device)
input("\nEnter - создать тестовые интерфейсы...")
huawei.create_test_interfaces()
huawei.collect_interfaces_info()
for interface, info in huawei.test_interfaces_info.items():
    print(f"{interface}: {info}")
input("\nEnter - удалить тестовые интерфейсы...")
huawei.remove_test_interfaces()


