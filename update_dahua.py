import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
import base64
import hashlib
import re
import argparse
import ipaddress
#url = "http://user:mdp@ip:80/cgi-bin/........."
#password=password.encode(encoding="ascii",errors="ignore")
##ExtraFormat[0] Pour flux secondaire##
##MainFormat[0] Pour flux primaire##
## Numero Cam commence à 0 ##
import subprocess
from datetime import datetime
import pytz

#CREER LISTE ADRESSE IP QUAND CAM IP
def expand_ip_range(ip_range):
    ip_list = []
    match = re.match(r'^(\d+\.\d+\.\d+\.)\{([\d,]+)\}$', ip_range)
    
    if match:
        prefix = match.group(1)
        numbers = match.group(2).split(',')
        
        for num in numbers:
            ip_list.append(prefix + num)
    
    return ip_list

#TROUVER PORT OUVERT SUR DVR OU CAM IP
def scan_ports(target_ip):
    open_ports = []

    # Exécute la commande Nmap avec les options spécifiées
    command = ['nmap', target_ip, '-p', '1-65535', '--open']
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    # Vérifie si l'exécution de la commande a réussi
    if process.returncode == 0:
        lines = output.decode('utf-8').split('\n')
        for line in lines:
            if '/tcp' in line:
                port = int(line.split('/')[0])
                open_ports.append(port)
                print(f"Port {port} is open")
        return open_ports
    else:
        print(f"Erreur lors de l'exécution de la commande Nmap: {error.decode('utf-8')}")
        return None

#LE PORT EST IL UN PORT HTTP ?
def is_http_port(camera_ip, username, password, port):
    url = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=getConfig&name=Encode[1].ExtraFormat[0]"
    url2 = f'http://www.google.com:{port}' 
    try:
        r = requests.get(url, stream=True, auth=HTTPDigestAuth(username, password), timeout=5)
        r.raise_for_status()
        print("test fonctionnel avec port  "+str(port))
        return True  # La connexion a réussi, donc c'est potentiellement un port HTTP
    except (requests.exceptions.RequestException):
        try:
            r = requests.get(url2, stream=True, auth=HTTPDigestAuth(username, password), timeout=5)
            r.raise_for_status()
            print("test fonctionnel avec port  "+str(port))
            return True
        except:   
            print("erreur avec port "+str(port))
            return False  # La connexion a échoué


def print_results(compression_types,resolution_types,fps_types,bitrate_types):
    print('Compression_types : ', compression_types)
    print('Resolution_types: ', resolution_types)
    print('Fps_types : ', fps_types)
    print('Bitrate_types: ', bitrate_types.replace(",","-"))
def print_results_cam(compression_types,resolution_types,fps_types,bitrate_types,channel, bitratecontrol):
    print('channel : ', channel)
    print('Compression_types : ', compression_types)
    print('Resolution_types: ', resolution_types)
    print('Fps_types : ', fps_types)
    print('bitrate control : ', bitratecontrol)
    print('Bitrate_types: ', bitrate_types.replace(",","-"))



#TROUVER NOMBRE DE CAM SUR UN DVR / SI CAM IP NE PAS PRENDRE EN COMPTE
def numberCam(camera_ip, username, password):
        open_ports=scan_ports(camera_ip)
        print(open_ports)
        potential_http_ports = []
        for port in open_ports:
            try:
                if is_http_port(camera_ip, username, password, port):
                    potential_http_ports.append(port)
                    break  # Sortir de la boucle dès qu'un port HTTP potentiel est trouvé
            except:
                print(f"L'itération pour le port {port} a pris trop de temps (plus de 30 secondes).")
        if potential_http_ports:
            print(f"Le ports HTTP potentiel est: {potential_http_ports[0]}")
        else:
            print("Aucun port HTTP potentiel trouvé.")
        url = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=getConfig&name=Ptz"
        r = requests.get(url, stream=True, auth=HTTPDigestAuth(username, password))
        t=r.text
        matches = re.findall(r'table\.Ptz\[(\d+)\]', t)
        # Obtenir le dernier chiffre trouvé
        if matches:
            dernier_chiffre = int(matches[-1])
            return [dernier_chiffre+1,port]
        else:
            print("nombre de camera introuvable")
            return [1,port]
                       
                      
def getinfoCam(camera_ip, username, password, channel_id, cam):
    print(camera_ip)
    number = numberCam(camera_ip, username, password)
    port = number[1]
    nbCam = int(number[0])
    if cam == "yes":
        nbCam = 1

    format_type = "ExtraFormat[0]" if channel_id == "all_sub" else "MainFormat[0]"

    for x in range(nbCam):
        sub = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=getConfig&name=Encode[{x}].{format_type}"
        r = requests.get(sub, stream=True, auth=HTTPDigestAuth(username, password))
        print(r.status_code)
        if r.status_code == 401:
            print("Unauthorized")
        if r.status_code == 200:
            print("-----")
            try:
                target_line_compression = next(line for line in r.text.split('\n') if f'table.Encode[{x}].{format_type}.Video.Compression' in line)
                compression_types = target_line_compression.split('=')[1].strip()
                target_line_resolution = next(line for line in r.text.split('\n') if f'table.Encode[{x}].{format_type}.Video.resolution' in line)
                resolution_types = target_line_resolution.split('=')[1].strip()
                target_line_fps = next(line for line in r.text.split('\n') if f'table.Encode[{x}].{format_type}.Video.FPS' in line)
                fps_types = target_line_fps.split('=')[1].strip()
                target_line_bitrate = next(line for line in r.text.split('\n') if f'table.Encode[{x}].{format_type}.Video.BitRate' in line)
                bitrate_types = target_line_bitrate.split('=')[1].strip()
                bitrate_control = next(line for line in r.text.split('\n') if f'table.Encode[{x}].{format_type}.Video.BitRateControl' in line)
                bitrate_ctrl = bitrate_control.split('=')[1].strip()
                print_results_cam(compression_types, resolution_types, fps_types, bitrate_types, str(x + 1), bitrate_ctrl)
            except StopIteration:
                continue

def getAllSettings(camera_ip, username, password):
    number = numberCam(camera_ip, username, password)
    port = number[1]
    url = f"http://{camera_ip}:{port}/cgi-bin/encode.cgi?action=getConfigCaps"
    url_user = f"http://{camera_ip}:{port}/cgi-bin/userManager.cgi?action=getUserInfoAll"
    
    # Obtenir les configurations et les informations utilisateur
    r = requests.get(url, stream=True, auth=HTTPDigestAuth(username, password))
    r_user = requests.get(url_user, stream=True, auth=HTTPDigestAuth(username, password))
    
    print(r.status_code)
    if r.status_code == 401:
        print("Unauthorized")
    elif r.status_code == 200:
        print(f"Pour IP {camera_ip}")
        print("INFO USER :")
        
        text_user = r_user.text
        
        # Définition de l'expression régulière pour extraire les noms, les groupes et les AuthorityList
        patterns = {
            'names': re.compile(r"users\[(\d+)\]\.Name=(\w+)"),
            'groups': re.compile(r"users\[(\d+)\]\.Group=(\w+)"),
            'authorities': re.compile(r"users\[(\d+)\]\.AuthorityList\[\d+\]=(\w+)")
        }
        
        # Recherche des noms, des groupes et des AuthorityList
        data = {key: {} for key in patterns.keys()}
        
        for key, pattern in patterns.items():
            for match in pattern.finditer(text_user):
                user_index, value = match.groups()
                if key == 'authorities':
                    data[key].setdefault(int(user_index), []).append(value)
                else:
                    data[key][int(user_index)] = value
        
        # Affichage des résultats
        for user_index in data['names'].keys():
            print(f"User {user_index}")
            print(f"Name: {data['names'][user_index]}")
            print(f"Group: {data['groups'][user_index]}")
            print(f"Droit: {data['authorities'][user_index]}")
            print()
        
        print("-----------")
        
        # Définition des formats et des paramètres à extraire
        formats = ['MainFormat[0]', 'ExtraFormat[0]']
        params = ['CompressionTypes', 'ResolutionTypes', 'FPSMax', 'BitRateOptions']
        
        # Fonction pour extraire et afficher les paramètres
        def extract_and_print_params(text, format_type):
            try:
                for param in params:
                    target_line = next(line for line in text.split('\n') if f'caps.{format_type}.Video.{param}' in line)
                    value = target_line.split('=')[1].strip()
                    print(f"{param.replace('Types', '').replace('Options', '')} : {value}")
                print("-----------")
            except StopIteration:
                print(f"Erreur d'extraction pour {format_type}")
        
        # Extraire et afficher les paramètres pour chaque format
        extract_and_print_params(r.text, 'MainFormat[0]')
        extract_and_print_params(r.text, 'ExtraFormat[0]')

def setResolution(camera_ip, username, password, channel_id, resolution, cam):
    number = numberCam(camera_ip, username, password)
    port = number[1]
    nbCam = int(number[0])
    if cam == "yes":
        nbCam = 1

    def set_resolution_for_camera(camera_index, format_type):
        resolution_com = f"Encode[{camera_index}].{format_type}.Video.resolution"
        url_resolution = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{resolution_com}={resolution}"
        r = requests.put(url_resolution, stream=True, auth=HTTPDigestAuth(username, password))
        print(r.status_code)
        if r.status_code == 401:
            print("Unauthorized")
        elif r.status_code == 200:
            print(f"Resolution pour camera {camera_index + 1} mise à {resolution}")
        elif r.status_code == 400 and format_type == "ExtraFormat[0]":
            print(f"Resolution trop haute pour camera {camera_index + 1}, mise à 704x576")
            url_resolution = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{resolution_com}=704x576"
            r = requests.put(url_resolution, stream=True, auth=HTTPDigestAuth(username, password))
            if r.status_code == 200:
                print(f"Resolution pour camera {camera_index + 1} mise à 704x576")
            else:
                print(f"Erreur : {r.status_code} - {r.text}")
        else:
            print(f"Erreur : {r.status_code} - {r.text}")

    if "all" in channel_id.lower():
        for x in range(nbCam):
            print(x + 1)
            if "sub" in channel_id.lower():
                set_resolution_for_camera(x, "ExtraFormat[0]")
            elif "main" in channel_id.lower():
                set_resolution_for_camera(x, "MainFormat[0]")
    else:
        channel_index = int(channel_id) - 1
        set_resolution_for_camera(channel_index, "ExtraFormat[0]")

      
    
def setFps(camera_ip, username, password, channel_id, fps, cam):
    number = numberCam(camera_ip, username, password)
    port = number[1]
    nbCam = int(number[0])
    if cam == "yes":
        nbCam = 1

    def set_fps_for_camera(camera_index, format_type):
        fps_cam = f"Encode[{camera_index}].{format_type}.Video.FPS"
        url_fps = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{fps_cam}={fps}"
        r = requests.put(url_fps, stream=True, auth=HTTPDigestAuth(username, password))
        print(r.status_code)
        if r.status_code == 401:
            print("Unauthorized")
        elif r.status_code == 200:
            print(f"FPS pour camera {camera_index + 1} mise à {fps}")
        elif r.status_code == 400:
            print("Pas bon format !")
        else:
            print(f"Erreur : {r.status_code} - {r.text}")

    if "all" in channel_id.lower():
        for x in range(nbCam):
            print(x + 1)
            if "sub" in channel_id.lower():
                set_fps_for_camera(x, "ExtraFormat[0]")
            elif "main" in channel_id.lower():
                set_fps_for_camera(x, "MainFormat[0]")
    else:
        channel_index = int(channel_id) - 1
        set_fps_for_camera(channel_index, "ExtraFormat[0]")



def setBitrate(camera_ip, username, password, channel_id, bitrate,cam):
    number=numberCam(camera_ip, username, password)
    port=number[1]
    nbCam=int(number[0])
    if cam == "yes":
        nbCam = 1
    if "all" in channel_id:
        for x in range(nbCam):
            print(x+1)
        
            if channel_id.lower()=="all_sub":   
                bitrate_cam=f"Encode[{x}].ExtraFormat[0].Video.BitRate"
                url_bitrate = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{bitrate_cam}={bitrate}"
                r = requests.put(url_bitrate, stream=True, auth=HTTPDigestAuth(username, password)) 
                print(r.status_code)
                if r.status_code==401:
                    print("Unauthorized")
                if r.status_code == 200:
                                print("BitRate pour camera "+str(x+1)+" mise à "+str(bitrate))
                elif r.status_code == 400:
                    print("Pas bon format !")
                else : 
                    print(f"Erreur : {r.status_code} - {r.text}")
                    
            elif channel_id.lower()=="all_main":   
                bitrate_cam=f"Encode[{x}].MainFormat[0].Video.BitRate"
                url_bitrate = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{bitrate_cam}={bitrate}"
                r = requests.put(url_bitrate, stream=True, auth=HTTPDigestAuth(username, password)) 
                print(r.status_code)
                if r.status_code==401:
                    print("Unauthorized")
                if r.status_code == 200:
                                print("BitRate pour camera "+str(x+1)+" mise à "+str(bitrate))
                elif r.status_code == 400:
                    print("Pas bon format !")
                else : 
                    print(f"Erreur : {r.status_code} - {r.text}")
    else:
            channel_id=int(channel_id)-1
            bitrate_cam=f"Encode[{channel_id}].ExtraFormat[0].Video.BitRate"
            url_bitrate = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{bitrate_cam}={bitrate}"
            print(url_bitrate)
            
            r = requests.put(url_bitrate, stream=True, auth=HTTPDigestAuth(username, password)) 
            print(r.status_code)
            if r.status_code==401:
                    print("Unauthorized")
            if r.status_code == 200:
                            print("BitRate pour camera "+str(channel_id)+" mise à "+str(bitrate)) 
            elif r.status_code == 400:
                    print("Pas bon format !")
            else : 
                    print(f"Erreur : {r.status_code} - {r.text}")
def setCompression(camera_ip, username, password, channel_id, compression,cam):
    number=numberCam(camera_ip, username, password)
    port=number[1]
    nbCam=int(number[0])
    if cam == "yes":
        nbCam = 1
    if "all" in channel_id:
        for x in range(nbCam):
            print(x+1)
        
            if channel_id.lower()=="all_sub":   
                compression_cam=f"Encode[{x}].ExtraFormat[0].Video.Compression"
                compression_cam2=f"Encode[{x}].ExtraFormat[0].Video.Profile=Main"
                url_compression = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{compression_cam}={compression}"
                url_compression_main = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{compression_cam2}"
                r = requests.put(url_compression, stream=True, auth=HTTPDigestAuth(username, password))
                r2 = requests.put(url_compression_main, stream=True, auth=HTTPDigestAuth(username, password))
                print(r.status_code)
                if r.status_code==401:
                    print("Unauthorized")
                if r.status_code == 200:
                                print("BitRate pour camera "+str(x+1)+" mise à "+str(compression))
                                print("Compression pour camera "+str(x+1)+" mise à "+str(compression))
                elif r.status_code == 400:
                    print("Pas bon format !")
                else : 
                    print(f"Erreur : {r.status_code} - {r.text}")
            elif channel_id.lower()=="all_main":   
                compression_cam=f"Encode[{x}].MainFormat[0].Video.Compression"
                compression_cam2=f"Encode[{x}].MainFormat[0].Video.Profile=Main"
                url_compression = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{compression_cam}={compression}"
                url_compression_main = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{compression_cam2}"
                r = requests.put(url_compression, stream=True, auth=HTTPDigestAuth(username, password))
                r2 = requests.put(url_compression_main, stream=True, auth=HTTPDigestAuth(username, password))
                print(r.status_code)
                if r.status_code==401:
                    print("Unauthorized")
                if r.status_code == 200:
                                print("BitRate pour camera "+str(x+1)+" mise à "+str(compression))
                                print("Compression pour camera "+str(x+1)+" mise à "+str(compression))
                elif r.status_code == 400:
                    print("Pas bon format !")
                else : 
                    print(f"Erreur : {r.status_code} - {r.text}")
    else:
            channel_id=int(channel_id)-1
            compression_cam=f"Encode[{channel_id}].ExtraFormat[0].Video.Compression"
            compression_cam2=f"Encode[{channel_id}].ExtraFormat[0].Video.Profile=Main"
            url_compression = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{compression_cam}={compression}"
            url_compression_main = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{compression_cam2}"
            r = requests.put(url_compression, stream=True, auth=HTTPDigestAuth(username, password))
            r2 = requests.put(url_compression_main, stream=True, auth=HTTPDigestAuth(username, password))
            print(r.status_code)
            if r.status_code==401:
                    print("Unauthorized")
            if r.status_code == 200:
                            print("BitRate pour camera "+str(channel_id+1)+" mise à "+str(compression))
                            print("Compression pour camera "+str(channel_id+1)+" mise à "+str(compression))
            elif r.status_code == 400:
                print("Pas bon format !")
            else : 
                print(f"Erreur : {r.status_code} - {r.text}")
def setBitrateControl(camera_ip, username, password, channel_id, Bcontrole,cam):
    number=numberCam(camera_ip, username, password)
    port=number[1]
    nbCam=int(number[0])
    if cam == "yes":
        nbCam = 1
    if "all" in channel_id:
        for x in range(nbCam):
            print(x+1)

            if channel_id.lower()=="all_sub":   
                bcontrole_cam=f"Encode[{x}].ExtraFormat[0].Video.BitRateControl"
                bcontrole=f"Encode["+str(x)+"].ExtraFormat[0].Video.BitRateControl"

                url_bcontrole = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{bcontrole}={Bcontrole}"
                r = requests.put(url_bcontrole, stream=True, auth=HTTPDigestAuth(username, password)) 
                print(r.status_code)
                if r.status_code==401:
                    print("Unauthorized")
                if r.status_code == 200:
                                print("BitRate Control pour camera "+str(x+1)+" mis à "+str(Bcontrole))
                elif r.status_code == 400:
                    print("Pas bon format !")
                else : 
                    print(f"Erreur : {r.status_code} - {r.text}")
                    
            
            elif channel_id.lower()=="all_main":   
                bcontrole=f"Encode[{x}].MainFormat[0].Video.BitRateControl"
                url_bcontrole = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{bcontrole}={Bcontrole}"
                print(url_bcontrole)
                r = requests.put(url_bcontrole, stream=True, auth=HTTPDigestAuth(username, password)) 
                print(r.status_code)
                if r.status_code==401:
                    print("Unauthorized")
                if r.status_code == 200:
                                print("BitRate Control pour camera "+str(x+1)+" mis à "+str(Bcontrole))
                elif r.status_code == 400:
                    print("Pas bon format !")
                else : 
                    print(f"Erreur : {r.status_code} - {r.text}")
    else:
            channel_id=int(channel_id)-1
            bcontrole=f"Encode[{channel_id}].ExtraFormat[0].Video.BitRateControl"
            url_bcontrole = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&{bcontrole}={Bcontrole}"
            print(url_bcontrole)
            r = requests.put(url_bcontrole, stream=True, auth=HTTPDigestAuth(username, password)) 
            print(r.status_code)
            if r.status_code==401:
                    print("Unauthorized")
            if r.status_code == 200:
                            print("BitRate Control pour camera "+str(channel_id)+" mis à "+str(Bcontrole)) 
            elif r.status_code == 400:
                    print("Pas bon format !")
            else : 
                    print(f"Erreur : {r.status_code} - {r.text}")
def setDetection(camera_ip, username, password, channel_id, motionDetect, cam):
    motionDetect = motionDetect.lower()
    number = numberCam(camera_ip, username, password)
    port = number[1]
    nbCam = int(number[0])
    if cam == "yes":
        nbCam = 1

    def set_motion_detection(camera_index):
        url_detection = f"http://{camera_ip}:{port}/cgi-bin/configManager.cgi?action=setConfig&MotionDetect[{camera_index}].Enable={motionDetect}"
        r = requests.put(url_detection, stream=True, auth=HTTPDigestAuth(username, password))
        print(r.status_code)
        if r.status_code == 401:
            print("Unauthorized")
        elif r.status_code == 200:
            print(f"Detection mouvement pour camera {camera_index + 1} mise à {motionDetect}")
        elif r.status_code == 400:
            print("Pas bon format !")
        else:
            print(f"Erreur : {r.status_code} - {r.text}")

    if "all" in channel_id:
        for x in range(nbCam):
            set_motion_detection(x)
    else:
        channel_index = int(channel_id) - 1
        set_motion_detection(channel_index)

def setEncrypt(camera_ip, username, password):
    url_encrypt=f"http://{camera_ip}/cgi-bin/configManager.cgi?action=setConfig&WLan.wlan0.Enable=true"
    url_encrypt2=f"http://{camera_ip}/cgi-bin/configManager.cgi?action=setConfig&WLan.wlan0.KeyFlag=true"
    url_encrypt3=f"http://{camera_ip}/cgi-bin/configManager.cgi?action=setConfig&WLan.wlan0.Encryption=On"
    url_encrypt4=f"http://{camera_ip}/cgi-bin/configManager.cgi?action=getConfig&name=WLan"
    url_encrypt5 = f"http://{camera_ip}/cgi-bin/configManager.cgi?action=setConfig&WLan.eth2.Encryption=On"
    r = requests.put(url_encrypt, stream=True, auth=HTTPDigestAuth(username, password))
    r2 = requests.put(url_encrypt2, stream=True, auth=HTTPDigestAuth(username, password))
    r3 = requests.put(url_encrypt3, stream=True, auth=HTTPDigestAuth(username, password))
    r4 = requests.get(url_encrypt4, stream=True, auth=HTTPDigestAuth(username, password))
    print(r4.status_code)
    if r4.status_code == 200:
                    
        print(r4.text)

def get_country_time(pays):
    try:
        # Obtenez le fuseau horaire du pays à partir du code de pays
        country_timezone = pytz.country_timezones.get(pays.upper())
        if country_timezone:
            # Convertir l'heure UTC actuelle au fuseau horaire du pays
            country_time = datetime.now(pytz.timezone(country_timezone[0]))
            country_time_formatted = country_time.strftime("%Y-%m-%d%%20%H:%M:%S")
            return country_time_formatted
        else:
            return f"Impossible de trouver le fuseau horaire pour le pays avec le code {'GB'}."
    except Exception as e:
        print("Une erreur s'est produite lors de la récupération de l'heure du pays :", e)
        return None

def setTime(camera_ip ,username, password, country):

    number=numberCam(camera_ip, username, password)
    port=number[1]
    auth = HTTPDigestAuth(username, password)
    url_before = f"http://{camera_ip}:{port}/cgi-bin/global.cgi?action=getCurrentTime"
    response_before = requests.get(url_before, auth=auth, timeout=5)
    print('Time before change :')
    print(response_before.text)
    local_now_string = get_country_time(country)
    url_time = f"http://{camera_ip}:{port}/cgi-bin/global.cgi?action=setCurrentTime&time="+local_now_string
    response_time = requests.post(url_time, auth=auth, timeout=5)
    if response_time.status_code == 200:
        print('Time change successful!')
    response_before = requests.get(url_before, auth=auth, timeout=5)
    print('New Time :')
    print(response_before.text)


def reboot_dvr(camera_ip ,username, password):

    number=numberCam(camera_ip, username, password)
    port=number[1]
    auth = HTTPDigestAuth(username, password)
    url_reboot = f"http://{camera_ip}:{port}/cgi-bin/magicBox.cgi?action=reboot"
    response_reboot = requests.get(url_reboot, auth=auth, timeout=5)
    if response_reboot.status_code == 200:
        print('The device was successfully restarted.')

def execute_actions(ip, args, cam):
    if args.r:
        setResolution(ip, args.u, args.p, args.ch, args.r, cam)
    if args.f:
        setFps(ip, args.u, args.p, args.ch, args.f, cam)
    if args.b:
        setBitrate(ip, args.u, args.p, args.ch, args.b, cam)
    if args.c:
        setCompression(ip, args.u, args.p, args.ch, args.c, cam)
    if args.m:
        setDetection(ip, args.u, args.p, args.ch, args.m, cam)
    if args.bc:
        setBitrateControl(ip, args.u, args.p, args.ch, args.bc, cam)
    if args.ch and not any([args.r, args.f, args.b, args.c, args.m, args.bc]):
        getinfoCam(ip, args.u, args.p, args.ch, cam)
    if not any([args.ch, args.r, args.f, args.b, args.c, args.m, args.bc, args.reboot]):
        getAllSettings(ip, args.u, args.p)
    if args.country:
        setTime(ip, args.u, args.p, args.country)
    if args.reboot:
        reboot_dvr(ip, args.u, args.p)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, required=True)
    parser.add_argument("--u", type=str, required=True)
    parser.add_argument("--p", type=str, required=True)
    parser.add_argument("--ch", type=str, required=False)
    parser.add_argument("--r", type=str, required=False)
    parser.add_argument("--f", type=int, required=False)
    parser.add_argument("--b", type=int, required=False)
    parser.add_argument("--c", type=str, required=False)
    parser.add_argument("--m", type=str, required=False)
    parser.add_argument("--bc", type=str, required=False)
    parser.add_argument("--country", type=str, required=False)
    parser.add_argument("--reboot", type=str, required=False)
    args = parser.parse_args()

    ip_list = expand_ip_range(args.ip) if "{" in args.ip else [args.ip]
    for ip in ip_list:
        execute_actions(ip, args, "yes" if "{" in args.ip else "no")


#ParamVideo#url = "http://admin:Veesion2023%21@172.24.14.23:80/cgi-bin/devVideoInput.cgi?action=getCaps&channel=1&streamType=2"
##url = "http://admin:Veesion2023%21@172.24.14.23:80/cgi-bin/configManager.cgi?action=getConfig&name=VideoInOptions"
### GetVideoConfigCaps ###
#Liste param video #url = "http://admin:Veesion2023%21@172.24.14.23:80/cgi-bin/encode.cgi?action=getConfigCaps"
### GetVideoEncodeConfig ###
#Bon param video #
# url = "http://admin:Veesion2023%21@172.24.14.23:80/cgi-bin/configManager.cgi?action=getConfig&name=Encode"
#VideoColor#
#url =  "http://admin:Veesion2023%21@172.24.14.23:80/cgi-bin/configManager.cgi?action=getConfig&name=VideoColor"
### SetVideoEncodeConfig ###
##head="table.Encode[15].SnapFormat[1]"
