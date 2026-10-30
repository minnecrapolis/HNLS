import ast
import copy
import importlib.util
import json
from pathlib import Path
import queue
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import numpy as np
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'src/controller/server'))
from libs import remote_pixels as remote
from libs.remote_protocol import Assembler, packets, MAX_LEDS
spec=importlib.util.spec_from_file_location('remote_receiver',BASE/'src/receiver/receiver.py')
receiver=importlib.util.module_from_spec(spec)
sys.path.insert(0,str(BASE/'src/receiver'));spec.loader.exec_module(receiver)
KEY='ab'*32

class FakePixels:
    def __init__(self,settings):self.settings=settings;self.frames=[];self.closed=False
    def show(self,frame):self.frames.append(frame)
    def close(self):self.show(bytes(self.settings['count']*3));self.closed=True

class ProtocolTests(unittest.TestCase):
    def test_mtu_bounded_maximum_frame_reassembles_reversed_with_duplicates(self):
        frame=bytes(n%256 for n in range(MAX_LEDS*3));parts=list(packets(frame,KEY.encode(),b'12345678',7));a=Assembler(KEY.encode(),b'12345678',MAX_LEDS)
        self.assertTrue(all(len(p)<1400 for p in parts))
        for p in parts[:0:-1]:self.assertIsNone(a.feed(p,1.))
        self.assertIsNone(a.feed(parts[-1],1.01));self.assertEqual(a.feed(parts[0],1.02),frame)
        self.assertIsNone(a.feed(parts[0],1.03))
    def test_bad_auth_session_sequence_partial_and_timeout_rejected(self):
        frame=bytes(1200*3);a=Assembler(KEY.encode(),b'12345678',1200)
        parts=list(packets(frame,KEY.encode(),b'12345678',3))
        self.assertIsNone(a.feed(parts[0][:-1]+b'X',0))
        self.assertIsNone(a.feed(list(packets(frame,b'wrong',b'12345678',3))[0],0))
        self.assertIsNone(a.feed(list(packets(frame,KEY.encode(),b'87654321',3))[0],0))
        self.assertIsNone(a.feed(parts[0],1.))
        for p in parts[1:]:self.assertIsNone(a.feed(p,1.2))
        for p in packets(frame,KEY.encode(),b'12345678',4):result=a.feed(p,1.3)
        self.assertEqual(result,frame)
        for p in parts:self.assertIsNone(a.feed(p,1.4))
    def test_wrong_frame_size_and_invalid_input_never_complete(self):
        a=Assembler(KEY.encode(),b'12345678',7)
        for data in (b'',b'x'*2000):self.assertIsNone(a.feed(data,0))
        p=next(packets(bytes(24),KEY.encode(),b'12345678',0));self.assertIsNone(a.feed(p,0))
        for frame in (b'',bytes(22),bytes(MAX_LEDS*3+3)):
            with self.assertRaises(ValueError):list(packets(frame,KEY.encode(),b'12345678',0))

class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.now=10.;self.r=receiver.Receiver(KEY,FakePixels,lambda:self.now)
        self.state=self.r.start_session({'count':7,'order':'GRB'},'192.168.1.10')
    def send(self,frame,seq=1,peer='192.168.1.10'):
        return [self.r.feed(p,peer) for p in packets(frame,KEY.encode(),bytes.fromhex(self.state['session']),seq)]
    def test_logical_rgb_untouched_and_watchdog_blackout_after_last_complete_frame(self):
        frame=b'\xff\x40\x00'*7
        self.assertEqual(self.send(frame),[True]);self.assertEqual(self.r.pixels.frames[-1],frame)
        self.assertTrue(self.r.status()['receiving']);self.now+=1.1;self.r.tick()
        self.assertEqual(self.r.pixels.frames[-1],bytes(21));self.assertFalse(self.r.status()['receiving'])
        self.send(frame,seq=2);self.assertTrue(self.r.status()['receiving'])
    def test_invalid_source_and_partial_frames_do_not_reset_watchdog(self):
        self.send(bytes([1]*21));self.now+=.9
        self.assertEqual(self.send(bytes(21),seq=2,peer='192.168.1.11'),[False])
        self.now+=.2;self.r.tick();self.assertTrue(self.r.blackout)
    def test_new_session_blacks_out_and_invalidates_old_sender(self):
        self.send(b'\xff'*21);old=self.state
        new=self.r.start_session({'count':7,'order':'GRB'},'192.168.1.11')
        self.assertNotEqual(old['session'],new['session']);self.assertEqual(self.r.pixels.frames[-1],bytes(21))
        self.assertEqual(self.send(b'\xff'*21,seq=2),[False])
    def test_reconfigure_releases_previous_output_and_reinitializes_color_order(self):
        previous=self.r.pixels
        self.r.start_session({'count':50,'order':'RGB'},'192.168.1.10')
        self.assertTrue(previous.closed);self.assertEqual(self.r.pixels.settings,{'count':50,'order':'RGB'})
    def test_settings_saved_and_cancelled_command_not_applied(self):
        with tempfile.TemporaryDirectory() as d:
            self.r.settings_file=Path(d)/'settings.json';self.r.start_session({'count':100,'order':'GRB'},'192.168.1.10')
            self.assertEqual(json.loads(self.r.settings_file.read_text())['count'],100)
            done,cancel=threading.Event(),threading.Event();cancel.set()
            self.r.commands.put(({'count':200,'order':'RGB'},'ip',done,{},cancel));self.r.process_commands()
            self.assertTrue(done.is_set());self.assertEqual(self.r.settings['count'],100)
    def test_bad_settings_fail_before_output_change(self):
        original=self.r.pixels
        for data in ({'count':0,'order':'RGB'},{'count':True,'order':'RGB'},{'count':2501,'order':'RGB'},{'count':10,'order':'RGBW'},None):
            with self.assertRaises(ValueError):self.r.start_session(data,'peer')
        self.assertIs(self.r.pixels,original)
    def test_pixel_packing_delegates_grb_to_native_library_once(self):
        strip=Mock();ws=NS(PixelStrip=Mock(return_value=strip),WS2811_STRIP_GRB=123)
        with patch.dict(sys.modules,{'rpi_ws281x':ws}):
            pixels=receiver.Pixels({'count':7,'order':'GRB'});pixels.show(bytes([255,64,0])*7);pixels.close()
        self.assertEqual(strip.setPixelColor.call_args_list[7].args,(0,0xff4000))
        self.assertEqual(ws.PixelStrip.call_args.kwargs['strip_type'],123);self.assertEqual(ws.PixelStrip.call_args.args,(7,21))

class PairingTests(unittest.TestCase):
    def setUp(self):
        from test_gpio_strings import configuration
        self.config=configuration();self.e=NS(_config=self.config,save_config=Mock(),put_into_notification_queue=Mock())
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.path=Path(temp.name)/'remote_pis.json'
        p=patch.object(remote,'store_path',return_value=self.path);p.start();self.addCleanup(p.stop)
        p=patch.object(remote,'call',return_value={'protocol':'mlsc-remote-1','hostname':'LED-SLAVE'});self.call=p.start();self.addCleanup(p.stop)
    def add(self,**kwargs):
        return remote.add_remote(self.e,{'source':'device_0','host':'192.168.1.34','key':KEY,'count':425,'name':'LED-SLAVE','order':'GRB',**kwargs})
    def test_pair_creates_remote_device_preserves_primary_and_only_starts_new_output(self):
        before=copy.deepcopy(self.config['device_configs']['device_0']);result=self.add();d=self.config['device_configs'][result['device']]
        self.assertEqual(before,self.config['device_configs']['device_0']);self.assertEqual(d['output_type'],'output_udp')
        self.assertEqual(d['output']['output_udp'],{'udp_client_ip':'192.168.1.34','udp_client_port':8944})
        self.assertEqual(d['effects']['effect_song_show']['bass_color'],'#ff4000');self.assertEqual(d['device_groups'],{})
        self.assertEqual(d['led_strip'],'ws2811_strip_grb');self.assertEqual(d['led_count'],425)
        self.assertEqual(self.path.stat().st_mode&0o777,0o600)
        self.e.put_into_notification_queue.assert_called_once();self.assertEqual(self.e.put_into_notification_queue.call_args.args[1],result['device'])
        self.assertNotIn(KEY,json.dumps(remote.list_remote(self.e)))
        remote.validate_devices(self.config)
    def test_invalid_inputs_and_failed_connection_do_not_touch_config_or_credentials(self):
        before=copy.deepcopy(self.config)
        for kw in ({'host':'8.8.8.8'},{'host':'localhost'},{'host':'http://192.168.1.34'},{'key':None},{'count':2501},{'order':'RGBW'},{'brightness':True},{'name':'<bad>'},{'source':[]}):
            with self.assertRaises(ValueError):self.add(**kw)
        self.call.side_effect=ValueError('offline')
        with self.assertRaises(ValueError):self.add()
        self.assertEqual(self.config,before);self.assertFalse(self.path.exists())
    def test_duplicate_rejected_and_save_failure_restores_credentials(self):
        self.e.save_config.side_effect=OSError('full')
        with self.assertRaises(OSError):self.add()
        self.assertEqual(remote.load(),{});self.assertEqual(len(self.config['device_configs']),1)
        self.e.save_config.side_effect=None;result=self.add()
        with self.assertRaisesRegex(ValueError,'already'):self.add(name='Other')
        remote.forget(result['device']);self.assertEqual(remote.load(),{})
    def test_remote_edits_reject_bad_count_color_endpoint_and_unrelated_local_gpio_is_allowed(self):
        result=self.add();key=result['device'];original=copy.deepcopy(self.config['device_configs'][key])
        for values in ({'led_count':3000},{'led_strip':'ws2812_strip'},{'output_type':'output_raspi'},{'fps':100}):
            self.config['device_configs'][key].update(values)
            with self.assertRaises(ValueError):remote.validate_devices(self.config)
            self.config['device_configs'][key]=copy.deepcopy(original)
        self.config['device_configs'][key]['output']['output_udp']['udp_client_ip']='192.168.1.99'
        with self.assertRaises(ValueError):remote.validate_devices(self.config)
    def test_node_resolution_is_specific_and_legacy_udp_keeps_existing_behavior(self):
        result=self.add();d=self.config['device_configs'][result['device']];device=NS(config=self.config,device_config=d)
        self.assertEqual(remote.node_for(device)['host'],'192.168.1.34')
        self.assertIsNone(remote.node_for(NS(config=self.config,device_config=self.config['device_configs']['device_0'])))

class HTTPAndSenderIntegration(unittest.TestCase):
    def test_real_http_auth_udp_sender_receiver_blackout_and_reconnect(self):
        r=receiver.Receiver(KEY,FakePixels)
        http=receiver.Server(('127.0.0.1',0),receiver.handler_for(r))
        udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);udp.bind(('127.0.0.1',0));udp.settimeout(.01)
        stopped=threading.Event()
        def loop():
            while not stopped.is_set():
                r.process_commands()
                try:p,a=udp.recvfrom(2048);r.feed(p,a[0])
                except socket.timeout:pass
                r.tick()
        thread=threading.Thread(target=loop);thread.start()
        web=threading.Thread(target=http.serve_forever);web.start()
        sender=None
        try:
            with patch.object(remote,'validate_host',return_value='127.0.0.1'),patch.object(remote,'HTTP_PORT',http.server_port),patch.object(remote,'UDP_PORT',udp.getsockname()[1]):
                node={'host':'127.0.0.1','key':KEY}
                with self.assertRaisesRegex(ValueError,'key was rejected'):remote.call({**node,'key':'0'*64})
                config={'led_count':425,'led_strip':'ws2811_strip_grb','led_brightness':50}
                sender=remote.RemoteSender(node,config);array=np.tile(np.array([[200],[64],[0]]),(1,425))
                deadline=time.monotonic()+3
                while not r.frames and time.monotonic()<deadline:sender.show(array);time.sleep(.02)
                self.assertGreater(r.frames,0);self.assertEqual(r.pixels.frames[-1],bytes([100,32,0])*425)
                # Changing receiver session simulates receiver reboot/another session;
                # sender notices and establishes a fresh session without master restart.
                initial=r.session
                remote.call(node,'/session',{'count':425,'order':'GRB'})
                foreign=r.session;self.assertNotEqual(initial,foreign)
                deadline=time.monotonic()+5
                while (r.session==foreign or r.blackout) and time.monotonic()<deadline:sender.show(array);time.sleep(.03)
                self.assertNotEqual(r.session,foreign);self.assertFalse(r.blackout)
                sender.close();sender.thread.join(1);sender=None
                deadline=time.monotonic()+1.4
                while r.pixels.frames[-1]!=bytes(425*3) and time.monotonic()<deadline:time.sleep(.02)
                self.assertEqual(r.pixels.frames[-1],bytes(425*3))
        finally:
            if sender:sender.close();sender.thread.join(6)
            stopped.set();thread.join(2);http.shutdown();web.join(2);http.server_close();udp.close();r.close()

