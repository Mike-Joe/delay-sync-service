import datetime
import sys
import os
import threading
import socket
import time
import uuid
import struct

# https://bluesock.org/~willkg/dev/ansi.html
ANSI_RESET = "\u001B[0m"
ANSI_RED = "\u001B[31m"
ANSI_GREEN = "\u001B[32m"
ANSI_YELLOW = "\u001B[33m"
ANSI_BLUE = "\u001B[34m"

_NODE_UUID = str(uuid.uuid4())[:8]


def print_yellow(msg):
    print(f"{ANSI_YELLOW}{msg}{ANSI_RESET}")


def print_blue(msg):
    print(f"{ANSI_BLUE}{msg}{ANSI_RESET}")


def print_red(msg):
    print(f"{ANSI_RED}{msg}{ANSI_RESET}")


def print_green(msg):
    print(f"{ANSI_GREEN}{msg}{ANSI_RESET}")


def get_broadcast_port():
    return 35498


def get_node_uuid():
    return _NODE_UUID


class NeighborInfo(object):
    def __init__(self, delay, ip=None, tcp_port=None):
        # Ip and port are optional, if you want to store them.
        self.delay = delay
        # self.last_timestamp = last_timestamp
        self.ip = ip
        self.tcp_port = tcp_port
        self.broadcast_count = 0

    def display(self):
        i = 31
        print(  "\u001B[{}m".format(i) + "\u001B[{}m".format(4) + "broadcast_count" + "\u001B[0m" +
        "\u001B[{}m".format(3)+" " + str(self.broadcast_count) + "\u001B[0m")
        i+=1
        print(  "\u001B[{}m".format(i) + "\u001B[{}m".format(4) + "delay" + "\u001B[0m" +
        "\u001B[{}m".format(3)+" " + str(self.delay) + "\u001B[0m")
        # i+=1
        # print(  "\u001B[{}m".format(i) + "\u001B[{}m".format(4) + "last time stamp" + "\u001B[0m" +
        # "\u001B[{}m".format(3)+" " + str(self.last_timestamp) + "\u001B[0m")
        i+=1
        print(  "\u001B[{}m".format(i) + "\u001B[{}m".format(4) + "ip:port" + "\u001B[0m" +
        "\u001B[{}m".format(3)+" " + self.ip + ":" + str(self.tcp_port) + "\u001B[0m")
        


############################################
#######  Y  O  U  R     C  O  D  E  ########
############################################


# Don't change any variable's name.
# Use this hashmap to store the information of your neighbor nodes.
neighbor_information = {}
# Leave the server socket as global variable.

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("", 0))
server.listen()

# Leave broadcaster as a global variable.
broadcaster = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
p = get_broadcast_port()
broadcaster.bind(("", p))


# Setup the UDP socket
node_uuid = get_node_uuid()


def send_broadcast_thread():

    while True:
        # TODO: write logic for sending broadcasts.
        tcp_port = server.getsockname()[1]
        sent_broadcast_message = node_uuid.encode('utf-8') + " ON ".encode('utf-8') + struct.pack('!H', tcp_port)
        port = get_broadcast_port()
        broadcaster.sendto(sent_broadcast_message, ('<broadcast>', port))
        # my_timestamp = datetime.datetime.utcnow().timestamp()
       
        time.sleep(1)  # Leave as is.


def receive_broadcast_thread():

    """
    Receive broadcasts from other nodes,
    launches a thread to connect to new nodes
    and exchange timestamps.
    """
    while True:
        # TODO: write logic for receiving broadcasts.
        data, (ip, port) = broadcaster.recvfrom(4096)
        print_blue(f"RECV: {data} FROM: {ip}:{port}")
        unpacked_data = struct.unpack('!8s4sH', data)
        neighbour_UUID = unpacked_data[0].decode('utf-8')
        neighbour_tcp_port = unpacked_data[2]

        if neighbour_UUID != node_uuid:
            if neighbour_UUID in neighbor_information:
                broadcast_count = neighbor_information[neighbour_UUID].broadcast_count
                neighbor_information[neighbour_UUID].broadcast_count += 1
            else:
                broadcast_count = 0
            if neighbour_UUID not in neighbor_information or broadcast_count % 10 == 0:
                thread_recv_tcp = daemon_thread_builder(exchange_timestamps_thread, (neighbour_UUID, ip, neighbour_tcp_port))
                thread_send_tcp = daemon_thread_builder(tcp_server_thread, ( ))
                
                thread_send_tcp.start()
                thread_recv_tcp.start()
                
                

def tcp_server_thread():
    """
    Accept connections from other nodes and send them
    this node's timestamp once they connect.
    """
    neigbour_sock, neighbour_addr = server.accept()
    my_timestamp = datetime.datetime.utcnow().timestamp()
    packed = struct.pack("!d", my_timestamp)
    neigbour_sock.send(packed)
    pass
    
def exchange_timestamps_thread(other_uuid: str, other_ip: str, other_tcp_port: int):
    """
    Open a connection to the other_ip, other_tcp_port
    and do the steps to exchange timestamps.

    Then update the neighbor_info map using other node's UUID.
    """
    print_yellow(f"ATTEMPTING TO CONNECT TO {other_uuid}")
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((other_ip, other_tcp_port))
        data = client.recv(1024)
    except ConnectionError:
        print_red("connection refused") 
        exit()
    timestamp = struct.unpack("!d", data)
    # calculate delay
    my_timestamp = datetime.datetime.utcnow().timestamp()
    delay = my_timestamp - timestamp[0]

    if other_uuid in neighbor_information:
        neighbor_information[other_uuid].delay = delay
        # neighbor_information[other_uuid].last_timestamp = timestamp[0]

    else:
        neighbour_node = NeighborInfo(delay, other_ip, other_tcp_port)
        neighbor_information.update({other_uuid: neighbour_node})

    client.close()


def daemon_thread_builder(target, args=()) -> threading.Thread:
    """
    Use this function to make threads. Leave as is.
    """
    th = threading.Thread(target=target, args=args)
    th.setDaemon(True)
    return th


def entrypoint():
    thread_send_udp = daemon_thread_builder(send_broadcast_thread, ())
    thread_recv_udp = daemon_thread_builder(receive_broadcast_thread, ())

    thread_send_udp.start()
    thread_recv_udp.start()
    
    from copy import  deepcopy
    last_time = {}
    save_this_state = True
    while True:
        
        templist = list(neighbor_information.keys())
        for iterator in range(len(neighbor_information)):
            if templist[iterator] in last_time:
                if last_time[templist[iterator]].broadcast_count == neighbor_information[templist[iterator]].broadcast_count  :
                    del neighbor_information[templist[iterator]]
                    continue
        
            print("*"*10)
            print(  "\u001B[{}m".format(1) + "\u001B[{}m".format(4) + "UUID" + "\u001B[0m" +
            "\u001B[{}m".format(3)+"\u001B[{}m".format(36)+"\u001B[{}m".format(1)+" " + templist[iterator] + "\u001B[0m")
    
            neighbor_information[templist[iterator]].display()

            print("*"*10)
        
        if save_this_state:
            last_time = deepcopy(neighbor_information)
        
        save_this_state ^= True
        time.sleep(1)


############################################
############################################


def main():
    """
    Leave as is.
    """
    print("*" * 50)
    print_red("To terminate this program use: CTRL+C")
    print_red("If the program blocks/throws, you have to terminate it manually.")
    print_green(f"NODE UUID: {get_node_uuid()}")
    print("*" * 50)
    time.sleep(2)  # Wait a little bit.
    entrypoint()
    # send_broadcast_thread()


if __name__ == "__main__":
    main()