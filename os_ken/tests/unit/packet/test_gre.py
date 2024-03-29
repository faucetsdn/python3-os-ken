# Copyright (C) 2016 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import sys

import unittest

from os_ken.lib import pcaplib
from os_ken.lib.packet import gre
from os_ken.lib.packet import packet
from os_ken.utils import binary_str
from os_ken.lib.packet.ether_types import ETH_TYPE_IP, ETH_TYPE_TEB

LOG = logging.getLogger(__name__)

GENEVE_DATA_DIR = os.path.join(
    os.path.dirname(sys.modules[__name__].__file__),
    '../../packet_data/pcap/')


class Test_gre(unittest.TestCase):
    """
    Test case gre for os_ken.lib.packet.gre.
    """

    version = 0
    gre_proto = ETH_TYPE_IP
    nvgre_proto = ETH_TYPE_TEB
    checksum = 0x440d
    seq_number = 10
    key = 256100
    vsid = 1000
    flow_id = 100

    gre = gre.gre(version=version, protocol=gre_proto, checksum=checksum,
                  key=key, seq_number=seq_number)

    def test_key_setter(self):
        self.gre.key = self.key
        self.assertEqual(self.gre._key, self.key)
        self.assertEqual(self.gre._vsid, self.vsid)
        self.assertEqual(self.gre._flow_id, self.flow_id)

    def test_key_setter_none(self):
        self.gre.key = None
        self.assertEqual(self.gre._key, None)
        self.assertEqual(self.gre._vsid, None)
        self.assertEqual(self.gre._flow_id, None)

        self.gre.key = self.key

    def test_vsid_setter(self):
        self.gre.vsid = self.vsid
        self.assertEqual(self.gre._key, self.key)
        self.assertEqual(self.gre._vsid, self.vsid)
        self.assertEqual(self.gre._flow_id, self.flow_id)

    def test_flowid_setter(self):
        self.gre.flow_id = self.flow_id
        self.assertEqual(self.gre._key, self.key)
        self.assertEqual(self.gre._vsid, self.vsid)
        self.assertEqual(self.gre._flow_id, self.flow_id)

    def test_nvgre_init(self):
        nvgre = gre.nvgre(version=self.version, vsid=self.vsid,
                          flow_id=self.flow_id)

        self.assertEqual(nvgre.version, self.version)
        self.assertEqual(nvgre.protocol, self.nvgre_proto)
        self.assertEqual(nvgre.checksum, None)
        self.assertEqual(nvgre.seq_number, None)
        self.assertEqual(nvgre._key, self.key)
        self.assertEqual(nvgre._vsid, self.vsid)
        self.assertEqual(nvgre._flow_id, self.flow_id)

    def test_parser(self):
        files = [
            'gre_full_options',
            'gre_no_option',
            'gre_nvgre_option',
        ]

        for f in files:
            # print('*** testing %s ...' % f)
            for _, buf in pcaplib.Reader(
                    open(GENEVE_DATA_DIR + f + '.pcap', 'rb')):
                # Checks if message can be parsed as expected.
                pkt = packet.Packet(buf)
                gre_pkt = pkt.get_protocol(gre.gre)
                self.assertTrue(isinstance(gre_pkt, gre.gre),
                    'Failed to parse Gre message: %s' % pkt)

                # Checks if message can be serialized as expected.
                pkt.serialize()

                self.assertEqual(buf, pkt.data,
                    "b'%s' != b'%s'" % (binary_str(buf), binary_str(pkt.data)))
