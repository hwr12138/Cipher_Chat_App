from socket import *
from routes.api import users, chat_sessions, online_user
import socket
import base64
import hashlib
import threading
import json
import pymongo

server_ip = "127.0.0.1"
server_port = 8000
max_conn = 10
global_clients = {"clients": [], "addresses": [], "_id": []}
in_global = {"clients": [], "addresses": [], "_id": []}
print('chatsession::::::', chat_sessions)

def get_headers(data):
    '''process the header for client connection and convert it into readable json'''
    header_dict = {}
    data = str(data, encoding='utf-8')
    header, body = data.split('\r\n\r\n', 1)
    header_list = header.split('\r\n')
    for i in range(0, len(header_list)):
        if i == 0:
            if len(header_list[i].split(' ')) == 3:
                header_dict['method'], header_dict['url'], header_dict['protocol'] = header_list[i].split(' ')
        else:
            k, v = header_list[i].split(':', 1)
            header_dict[k] = v.strip()
    return header_dict

def send_msg(conn, msg_bytes):
    '''take in string msg and send message bytes through conn'''
    import struct
    token = b"\x81"
    length = len(msg_bytes)
    if length < 126:
        token += struct.pack("B", length)
    elif length <= 0xFFFF:
        token += struct.pack("!BH", 126, length)
    else:
        token += struct.pack("!BQ", 127, length)
    msg = token + msg_bytes
    conn.send(msg)
    return True

def broadcast(session_id, user, message):
    '''broadcast the message to the right group of people based on their session id'''
    print('clients:', global_clients)
    if session_id == 'global':
        for i in range(len(global_clients['clients'])):
            ind = 0
            for session in chat_sessions.find():
                if global_clients['_id'][i] in session['members']:
                    ind = 1
            if ind == 0:
                send_msg(global_clients['clients'][i], bytes(user+': '+message, encoding='utf-8'))
    else:
        broadcast_in_session(session_id, user, message)
        
def broadcast_in_session(session_id, user, message):
    '''the broadcast function for in session communication'''
    session = chat_sessions.find_one({'id': session_id})
    print('sesssssssssss:', session)
    for member in session['members']:
        print('memb', member)
        for i in range(len(global_clients['_id'])):
            if member == global_clients['_id'][i]:
                send_msg(global_clients['clients'][i], bytes(user+': '+message, encoding='utf-8'))

class ClientThread(threading.Thread):
    '''a client thread, can have multiple threads for multiple clients (each client has one thread)'''
    def __init__(self, client, address):
        '''init a client thread object'''
        super(ClientThread, self).__init__()
        self.client = client
        self.address = address

    def run(self):
        '''run the client thread and accept incoming messages, also redirect them to the right sessions'''
        print("new client joined the socket")
        data = self.client.recv(1024)
        headers = get_headers(data)
        print(headers)
        response_tpl = "HTTP/1.1 101 Switching Protocols\r\n" \
                     "Upgrade:websocket\r\n" \
                     "Connection: Upgrade\r\n" \
                     "Sec-WebSocket-Accept: %s\r\n" \
                     "WebSocket-Location: ws://%s%s\r\n\r\n"
        magic_string = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        value = headers['Sec-WebSocket-Key'] + magic_string
        ac = base64.b64encode(hashlib.sha1(value.encode('utf-8')).digest())
        response_str = response_tpl % (ac.decode('utf-8'), headers['Host'], headers['url'])
        self.client.send(bytes(response_str, encoding='utf-8')) # build connection
        print('glob clients:', global_clients)
        # get user id know who the client is
        try:
            info = self.client.recv(8096)
        except Exception as e:
            info = None
        body = self.process_body(info)        
        body = json.loads(body)
        print('client is', body)
        clientId = body['_id']
        global_clients['_id'].append(clientId)
        # start listening
        while 1:
            try:
                info = self.client.recv(8096)
            except Exception as e:
                info = None
            if not info:
                break
            print('info:', info)
            body_str = self.process_body(info)
            print(body_str)
            body = json.loads(body_str)
            print(body)
            if "__closeConn__" == body['message'] or body_str == "": #网页端已经断开连接了，因为网页端发不了空白
                print('breaking:', body)
                global_clients['clients'].remove(self.client)
                global_clients['addresses'].remove(self.address)
                global_clients['_id'].remove(clientId)
                session = chat_sessions.find_one({'id': body['sessionId']})
                if session: # session already exists
                    print(session)
                    v = []
                    for mem in list(session['members']):
                        print(mem)
                        if mem != body['user']:
                            v.append(mem)
                    new = {"$set": {'members': v}}
                    print('newwwwwww:', new)
                    chat_sessions.update_one({'members': session['members']}, new)
                break
            broadcast(body['sessionId'], body['user'], body['message'])
    
    def process_body(self, info):
        '''process the byte incoming messages and decode them into readable messages'''
        payload_len = info[1] & 127
        if payload_len == 126:
            extend_payload_len = info[2:4]
            mask = info[4:8]
            decoded = info[8:]
        elif payload_len == 127:
            extend_payload_len = info[2:10]
            mask = info[10:14]
            decoded = info[14:]
        else:
            extend_payload_len = None
            mask = info[2:6]
            decoded = info[6:]
        bytes_list = bytearray()
        for i in range(len(decoded)):
            chunk = decoded[i] ^ mask[i % 4]
            bytes_list.append(chunk)
        msg = str(bytes_list, encoding='utf-8')
        result = ""
        for i in range(len(msg)):
            result = result + chr(ord(msg[i]) - 5);
        return result

class ChatServer(threading.Thread):
    '''the chat server that we run in the backend'''
    def __init__(self, ip='127.0.0.1', port=8088):
        '''init a chatserver object'''
        super(ChatServer, self).__init__()
        self.addr = (ip, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        '''run the chat server and maintain list of clients'''
        self.sock.bind(self.addr)
        self.sock.listen()
        print("Socket server is listening on ", self.addr)
        while True:
            client, address = self.sock.accept()
            print('addr:', address)
            global_clients['clients'].append(client)
            global_clients['addresses'].append(address)
            client_thread = ClientThread(client, address)
            client_thread.start()

    def stop(self):
        '''stop the server'''
        for s in global_clients.values():
            s.close()
        self.sock.close()
