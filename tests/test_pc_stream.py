import ast
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
import zipfile
import numpy as np
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'src/controller/server'))
from libs import pc_stream as m
from libs.pc_stream_runtime import PCStreamMixin
KEY=bytes(range(32));STREAM=bytes(range(16))

def pcm(value, frames=256):
    return np.full((frames,2),value,dtype='<i2').tobytes()

def packet(seq, value=1, stream=STREAM, rate=48000, frames=256):
    return m.encode_packet(KEY,stream,seq,rate,pcm(value,frames))

class BufferTests(unittest.TestCase):
    def test_exact_authenticated_stereo_and_reordering(self):
        b=m.PacketBuffer(KEY,256)
        self.assertTrue(b.feed(packet(0,11),0))
        b.feed(packet(2,33),.01);b.feed(packet(1,22),.02)
        self.assertEqual(b.read(.02),pcm(11));self.assertEqual(b.read(.02),pcm(22));self.assertEqual(b.read(.02),pcm(33))
        self.assertFalse(b.feed(packet(1,22),.03))
    def test_tamper_wrong_key_sizes_magic_rate_and_channels_rejected(self):
        b=m.PacketBuffer(KEY,256);good=packet(0)
        for bad in [b'', good[:-1],good+b'X',good[:70]+b'\x00'+good[71:],m.encode_packet(b'x'*32,STREAM,0,48000,pcm(1)),b'x'*m.MAX_PACKET]:
            self.assertFalse(b.feed(bad,0))
        self.assertIsNone(b.stream);self.assertEqual(b.last_seen,-1e9)
    def test_rejects_replay_competing_sender_and_recent_retired_stream(self):
        b=m.PacketBuffer(KEY,256);b.feed(packet(0),0)
        self.assertFalse(b.feed(packet(0),.1));self.assertFalse(b.feed(packet(0,stream=b'B'*16),.1))
        self.assertTrue(b.feed(packet(0,stream=b'B'*16),2))
        self.assertFalse(b.feed(packet(10),4))
    def test_rate_change_requires_new_stream_and_stale_audio_is_discarded(self):
        b=m.PacketBuffer(KEY,256);b.feed(packet(0),0);b.feed(packet(1),.01)
        self.assertFalse(b.feed(packet(2,rate=44100),.02));self.assertIsNone(b.read(.5));self.assertFalse(b.pcm)
        b.feed(packet(0,stream=b'B'*16,rate=44100),2);b.feed(packet(1,stream=b'B'*16,rate=44100),2)
        self.assertEqual(b.rate,44100);self.assertEqual(b.read(2),pcm(1))
    def test_loss_waits_briefly_then_skips_gap_buffer_never_grows_without_bound(self):
        b=m.PacketBuffer(KEY,256);b.feed(packet(0),0);b.feed(packet(2),.001)
        self.assertIsNone(b.read(.01));self.assertIsNotNone(b.read(.05));self.assertEqual(b.dropped,1)
        for n in range(3,3000):b.feed(packet(n),.05)
        self.assertLessEqual(len(b.pcm),48000*.16*4);self.assertLessEqual(len(b.pending),9)
    def test_real_udp_receiver_interoperability_and_closed_socket(self):
        receiver=m.Receiver(KEY,256,port=0);self.addCleanup(receiver.close)
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:
            address=('127.0.0.1',receiver.socket.getsockname()[1])
            sender.sendto(packet(0,123),address);sender.sendto(packet(1,456),address)
            data=receiver.read()
            self.assertEqual(data,pcm(123));self.assertEqual(receiver.read(),pcm(456))
    def test_private_credentials_persist_and_download_contains_only_sender_files(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'HNLS_SETTINGS_DIR':d}):
            a=m.credentials();self.assertEqual(len(a),32);self.assertEqual(a,m.credentials())
            self.assertEqual(m.settings_path().stat().st_mode&0o777,0o600)
            with zipfile.ZipFile(m.sender_bundle('192.168.1.37')) as z:
                self.assertEqual(len(z.namelist()),5)
                c=json.loads(z.read('HNLS-PC-Audio/connection.json'));self.assertEqual(c,{'host':'192.168.1.37','port':8950,'key':a.hex()})
                self.assertIn('LOOPBACK',z.read('HNLS-PC-Audio/LoopbackSender.cs').decode())
            for host in ['', 'pi/evil','bad\nname']:
                with self.assertRaises(ValueError):m.sender_bundle(host)

class RuntimeTests(unittest.TestCase):
    def service(self):
        s=PCStreamMixin();s._frames_per_buffer=256;s._device_rate=48000;s._config={'general_settings':{'default_sample_rate':48000}}
        s._music_output_stream=None;s._pc_output_error=None;s._pc_active=False;s._pc_status_at=0.;s._pc_last_audio=10.
        s._music_position=0.;s._playback_epoch=3;s._show_analyzer=Mock();s._process_samples=Mock();s._publish_playback=Mock()
        s._pc_receiver=NS(read=Mock(return_value=pcm(100)),buffer=NS(rate=44100,last_seen=10.))
        return s
    def test_same_audio_to_output_and_dsp_native_rate_no_song_identity(self):
        s=self.service();output=Mock()
        with patch.dict(sys.modules,{'libs.dsp':NS(DSP=Mock()),'libs.alsa_music_output':NS(HeadphoneOutput=Mock(return_value=output))}),patch('libs.pc_stream_runtime.monotonic',return_value=10.),patch('libs.pc_stream_runtime.write_status') as status:
            s._pc_stream_routine()
            output.write.assert_called_once_with(pcm(100));np.testing.assert_array_equal(s._process_samples.call_args.args[0],np.full(256,100,dtype=np.int16))
            self.assertEqual(s._device_rate,44100);self.assertEqual(s._playback_epoch,4);s._show_analyzer.start_song.assert_called_once_with(None)
            self.assertEqual(s._config['general_settings']['default_sample_rate'],48000,'Live source does not change saved configuration')
            status.assert_called_with('pc_stream',error=None)
    def test_stall_closes_audio_and_blacks_out_without_restarting_playlist(self):
        s=self.service();s._pc_active=True;s._music_output_stream=Mock();out=s._music_output_stream;s._pc_receiver.read.return_value=None
        with patch('libs.pc_stream_runtime.monotonic',return_value=11.),patch('libs.pc_stream_runtime.write_status') as status,patch('libs.pc_stream_runtime.sleep'):
            s._pc_stream_routine()
        out.close.assert_called_once();s._publish_playback.assert_called_with(True);self.assertFalse(s._pc_active);s._process_samples.assert_not_called();status.assert_called_with('pc_stream_waiting',error=None)
    def test_start_binds_before_stopping_source_failure_preserves_current_playback(self):
        s=self.service();s._pc_receiver=None;s._cleanup_music=Mock();s._close_microphone_stream=Mock();s._source_mode='music'
        with patch('libs.pc_stream_runtime.Receiver',side_effect=OSError('port in use')),patch('libs.pc_stream_runtime.credentials',return_value=KEY),self.assertRaises(OSError):s._start_pc_stream()
        self.assertEqual(s._source_mode,'music');s._cleanup_music.assert_not_called()
    def test_explicit_stop_closes_receiver_and_blacks_out(self):
        s=self.service();s._cleanup_music=Mock()
        with patch('libs.pc_stream_runtime.write_status') as status:s._stop_pc_stream()
        self.assertEqual(s._source_mode,'playlist_idle');s._cleanup_music.assert_called_once();s._publish_playback.assert_called_once_with(True);status.assert_called_with('stopped')
    def test_switch_to_file_cleans_up_pc_socket_and_restores_default_rate(self):
        source=(BASE/'src/controller/server/libs/audio_process_service.py').read_text()
        tree=ast.parse(source);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='AudioProcessService')
        start=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_start_music')
        code=ast.unparse(start)
        self.assertIn("self._source_mode in ('music', 'pc_stream')",code)
        self.assertIn("self._device_rate = self._config['general_settings']['default_sample_rate']",code)
        cleanup=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_cleanup_music');self.assertIn('self._close_pc_stream()',ast.unparse(cleanup))
        routine=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='audio_service_routine');self.assertIn('self._pc_stream_routine()',ast.unparse(routine))

class APITests(unittest.TestCase):
    def api(self):
        tree=ast.parse((BASE/'src/controller/server/libs/webserver/blueprints/pc_stream_api.py').read_text())
        scope={'jsonify':lambda **kw:kw,'request':NS(get_json=Mock(),url_root='http://192.168.1.37:8080/'), 'send_file':Mock(return_value=NS(headers={}))}
        ex=NS(effect_executer=Mock(),music_library_executer=NS(notification_queue_out=Mock()))
        scope['Executer']=NS(instance=ex)
        for node in tree.body:
            if isinstance(node,ast.FunctionDef):
                self.assertTrue(any(isinstance(d,ast.Name) and d.id=='login_required' for d in node.decorator_list))
                node.decorator_list=[];exec(compile(ast.Module(body=[node],type_ignores=[]),'pc_api.py','exec'),scope)
        return scope,ex
    def test_start_selects_songshow_and_queues_source_without_modifying_private_outputs(self):
        scope,ex=self.api();scope['request'].get_json.return_value={'action':'start'};release=Mock()
        with patch.dict(sys.modules,{'libs.show_schedule':NS(ScheduleActions=lambda e:NS(release_studio=release))}),patch.object(m,'credentials',return_value=KEY):
            result=scope['control']()
        self.assertTrue(result['queued']);release.assert_called_once();ex.effect_executer.set_active_effect_for_all.assert_called_once_with('effect_song_show')
        item=ex.music_library_executer.notification_queue_out.put.call_args.args[0]
        self.assertEqual(item.payload,{'action':'pc_stream_start'})
    def test_bad_action_does_not_stop_or_change_playback(self):
        scope,ex=self.api();scope['request'].get_json.return_value={'action':'shell','command':'anything'}
        result,code=scope['control']();self.assertEqual(code,400);self.assertIn('error',result);ex.effect_executer.set_active_effect_for_all.assert_not_called();ex.music_library_executer.notification_queue_out.put.assert_not_called()
    def test_download_uses_lan_host_and_disables_caching(self):
        scope,ex=self.api()
        with patch.object(m,'sender_bundle',return_value=io.BytesIO(b'zip')) as bundle:response=scope['sender']()
        bundle.assert_called_once_with('192.168.1.37');self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertEqual(scope['send_file'].call_args.kwargs['download_name'],'HNLS-PC-Audio.zip')

if __name__=='__main__':unittest.main()
