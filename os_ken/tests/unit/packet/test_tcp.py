# Copyright (C) 2012-2015 Nippon Telegraph and Telephone Corporation.
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

import unittest
import logging
import struct
from struct import *
from os_ken.ofproto import inet
from os_ken.lib.packet import tcp
from os_ken.lib.packet.ipv4 import ipv4
from os_ken.lib.packet import packet_utils
from os_ken.lib import addrconv


LOG = logging.getLogger('test_tcp')


class Test_tcp(unittest.TestCase):
    """ Test case for tcp
    """
    src_port = 6431
    dst_port = 8080
    seq = 5
    ack = 1
    offset = 6
    bits = 0b101010
    window_size = 2048
    csum = 12345
    urgent = 128
    option = b'\x01\x02\x03\x04'

    t = tcp.tcp(src_port, dst_port, seq, ack, offset, bits,
                window_size, csum, urgent, option)

    buf = pack(tcp.tcp._PACK_STR, src_port, dst_port, seq, ack,
               offset << 4, bits, window_size, csum, urgent)
    buf += option

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_init(self):
        self.assertEqual(self.src_port, self.t.src_port)
        self.assertEqual(self.dst_port, self.t.dst_port)
        self.assertEqual(self.seq, self.t.seq)
        self.assertEqual(self.ack, self.t.ack)
        self.assertEqual(self.offset, self.t.offset)
        self.assertEqual(self.bits, self.t.bits)
        self.assertEqual(self.window_size, self.t.window_size)
        self.assertEqual(self.csum, self.t.csum)
        self.assertEqual(self.urgent, self.t.urgent)
        self.assertEqual(self.option, self.t.option)

    def test_parser(self):
        r1, r2, _ = self.t.parser(self.buf)

        self.assertEqual(self.src_port, r1.src_port)
        self.assertEqual(self.dst_port, r1.dst_port)
        self.assertEqual(self.seq, r1.seq)
        self.assertEqual(self.ack, r1.ack)
        self.assertEqual(self.offset, r1.offset)
        self.assertEqual(self.bits, r1.bits)
        self.assertEqual(self.window_size, r1.window_size)
        self.assertEqual(self.csum, r1.csum)
        self.assertEqual(self.urgent, r1.urgent)
        self.assertEqual(self.option, r1.option)
        self.assertEqual(None, r2)

    def test_serialize(self):
        offset = 5
        csum = 0

        src_ip = '192.168.10.1'
        dst_ip = '192.168.100.1'
        prev = ipv4(4, 5, 0, 0, 0, 0, 0, 64,
                    inet.IPPROTO_TCP, 0, src_ip, dst_ip)

        t = tcp.tcp(self.src_port, self.dst_port, self.seq, self.ack,
                    offset, self.bits, self.window_size, csum, self.urgent)
        buf = t.serialize(bytearray(), prev)
        res = struct.unpack(tcp.tcp._PACK_STR, bytes(buf))

        self.assertEqual(res[0], self.src_port)
        self.assertEqual(res[1], self.dst_port)
        self.assertEqual(res[2], self.seq)
        self.assertEqual(res[3], self.ack)
        self.assertEqual(res[4], offset << 4)
        self.assertEqual(res[5], self.bits)
        self.assertEqual(res[6], self.window_size)
        self.assertEqual(res[8], self.urgent)

        # test __len__
        # offset indicates the number of 32 bit (= 4 bytes)
        # words in the TCP Header.
        # So, we compare len(tcp) with offset * 4, here.
        self.assertEqual(offset * 4, len(t))

        # checksum
        ph = struct.pack('!4s4sBBH',
                         addrconv.ipv4.text_to_bin(src_ip),
                         addrconv.ipv4.text_to_bin(dst_ip), 0, 6, offset * 4)
        d = ph + buf
        s = packet_utils.checksum(d)
        self.assertEqual(0, s)

    def test_serialize_option(self):
        # prepare test data
        offset = 0
        csum = 0
        option = [
            tcp.TCPOptionMaximumSegmentSize(max_seg_size=1460),
            tcp.TCPOptionSACKPermitted(),
            tcp.TCPOptionTimestamps(ts_val=287454020, ts_ecr=1432778632),
            tcp.TCPOptionNoOperation(),
            tcp.TCPOptionWindowScale(shift_cnt=9),
        ]
        option_buf = (
            b'\x02\x04\x05\xb4'
            b'\x04\x02'
            b'\x08\x0a\x11\x22\x33\x44\x55\x66\x77\x88'
            b'\x01'
            b'\x03\x03\x09'
        )
        prev = ipv4(4, 5, 0, 0, 0, 0, 0, 64,
                    inet.IPPROTO_TCP, 0, '192.168.10.1', '192.168.100.1')

        # test serializer
        t = tcp.tcp(self.src_port, self.dst_port, self.seq, self.ack,
                    offset, self.bits, self.window_size, csum, self.urgent,
                    option)
        buf = t.serialize(bytearray(), prev)
        r_option_buf = buf[tcp.tcp._MIN_LEN:tcp.tcp._MIN_LEN + len(option_buf)]
        self.assertEqual(option_buf, r_option_buf)

        # test parser
        (r_tcp, _, _) = tcp.tcp.parser(buf)
        self.assertEqual(str(option), str(r_tcp.option))

    def test_malformed_tcp(self):
        m_short_buf = self.buf[1:tcp.tcp._MIN_LEN]
        self.assertRaises(Exception, tcp.tcp.parser, m_short_buf)

    def test_default_args(self):
        prev = ipv4(proto=inet.IPPROTO_TCP)
        t = tcp.tcp()
        buf = t.serialize(bytearray(), prev)
        res = struct.unpack(tcp.tcp._PACK_STR, buf)

        self.assertEqual(res[0], 1)
        self.assertEqual(res[1], 1)
        self.assertEqual(res[2], 0)
        self.assertEqual(res[3], 0)
        self.assertEqual(res[4], 5 << 4)
        self.assertEqual(res[5], 0)
        self.assertEqual(res[6], 0)
        self.assertEqual(res[8], 0)

        # with option, without offset
        t = tcp.tcp(option=[tcp.TCPOptionMaximumSegmentSize(1460)])
        buf = t.serialize(bytearray(), prev)
        res = struct.unpack(tcp.tcp._PACK_STR + '4s', buf)

        self.assertEqual(res[0], 1)
        self.assertEqual(res[1], 1)
        self.assertEqual(res[2], 0)
        self.assertEqual(res[3], 0)
        self.assertEqual(res[4], 6 << 4)
        self.assertEqual(res[5], 0)
        self.assertEqual(res[6], 0)
        self.assertEqual(res[8], 0)
        self.assertEqual(res[9], b'\x02\x04\x05\xb4')

        # with option, with long offset
        t = tcp.tcp(offset=7, option=[tcp.TCPOptionWindowScale(shift_cnt=9)])
        buf = t.serialize(bytearray(), prev)
        res = struct.unpack(tcp.tcp._PACK_STR + '8s', buf)

        self.assertEqual(res[0], 1)
        self.assertEqual(res[1], 1)
        self.assertEqual(res[2], 0)
        self.assertEqual(res[3], 0)
        self.assertEqual(res[4], 7 << 4)
        self.assertEqual(res[5], 0)
        self.assertEqual(res[6], 0)
        self.assertEqual(res[8], 0)
        self.assertEqual(res[9], b'\x03\x03\x09\x00\x00\x00\x00\x00')

    def test_json(self):
        jsondict = self.t.to_jsondict()
        t = tcp.tcp.from_jsondict(jsondict['tcp'])
        self.assertEqual(str(self.t), str(t))


class Test_TCPOption(unittest.TestCase):
    # prepare test data
    input_options = [
        tcp.TCPOptionEndOfOptionList(),
        tcp.TCPOptionNoOperation(),
        tcp.TCPOptionMaximumSegmentSize(max_seg_size=1460),
        tcp.TCPOptionWindowScale(shift_cnt=9),
        tcp.TCPOptionSACKPermitted(),
        tcp.TCPOptionSACK(blocks=[(1, 2), (3, 4)], length=18),
        tcp.TCPOptionTimestamps(ts_val=287454020, ts_ecr=1432778632),
        tcp.TCPOptionUserTimeout(granularity=1, user_timeout=564),
        tcp.TCPOptionAuthentication(
            key_id=1, r_next_key_id=2,
            mac=b'abcdefghijkl', length=16),
        tcp.TCPOptionUnknown(value=b'foobar', kind=255, length=8),
        tcp.TCPOptionUnknown(value=b'', kind=255, length=2),
    ]
    input_buf = (
        b'\x00'  # End of Option List
        b'\x01'  # No-Operation
        b'\x02\x04\x05\xb4'  # Maximum Segment Size
        b'\x03\x03\x09'  # Window Scale
        b'\x04\x02'  # SACK Permitted
        b'\x05\x12'  # SACK
        b'\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00\x04'
        b'\x08\x0a'  # Timestamps
        b'\x11\x22\x33\x44\x55\x66\x77\x88'
        b'\x1c\x04\x82\x34'  # User Timeout Option
        b'\x1d\x10\x01\x02'  # TCP Authentication Option (TCP-AO)
        b'abcdefghijkl'
        b'\xff\x08'  # Unknown with body
        b'foobar'
        b'\xff\x02'  # Unknown
    )

    def test_serialize(self):
        output_buf = bytearray()
        for option in self.input_options:
            output_buf += option.serialize()
        self.assertEqual(self.input_buf, output_buf)

    def test_parser(self):
        buf = self.input_buf
        output_options = []
        while buf:
            opt, buf = tcp.TCPOption.parser(buf)
            output_options.append(opt)
        self.assertEqual(str(self.input_options), str(output_options))

    def test_json(self):
        for option in self.input_options:
            json_dict = option.to_jsondict()[option.__class__.__name__]
            output_option = option.__class__.from_jsondict(json_dict)
            self.assertEqual(str(option), str(output_option))
