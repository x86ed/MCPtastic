"""Demonstration of how to look up a radio's location via its LAN connection.
   Before running, connect your machine to the same WiFi network as the radio.
"""

import meshtastic
import meshtastic.tcp_interface

radio_hostname = "meshtastic.local"  # Can also be an IP
iface = meshtastic.tcp_interface.TCPInterface(radio_hostname)
my_node_num = iface.myInfo.my_node_num
iface.localNode.localConfig.position.gps_mode = "ENABLED"
iface.localNode.localConfig.position.fixed_position = True
iface.localNode.setFixedPosition(1, 2, 3)
iface.localNode.writeConfig("position")

iface.close()