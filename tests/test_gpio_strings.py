import ast
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]/'src/controller/server';sys.path.insert(0,str(ROOT))
from libs import gpio_outputs as gpio
from libs.notification_enum import NotificationEnum


def configuration():
    config=json.loads((ROOT/'libs/config_template.json').read_text());d=copy.deepcopy(config['default_device'])
    d.update(led_count=1200,led_brightness=30,led_strip='ws2811_strip_grb',output_type='output_raspi',fps=25)
    d['output']['output_raspi'].update(led_pin=21,led_channel=0)
    d['effects']['effect_song_show'].update(sync_mode='custom',sync_groups=[n//2+1 for n in range(24)],section_size=50,bass_color='#ff4000',power_color='#ff4000')
    config['device_configs']={'device_0':d};return config

READY={'ready':True,'buffer_bytes':131072,'available':True,'clock_fixed':True,'model':'Raspberry Pi 4 Model B'}

class AddStringTests(unittest.TestCase):
    def setUp(self):
        self.config=configuration();self.original=copy.deepcopy(self.config['device_configs']['device_0'])
        self.executer=NS(_config=self.config,save_config=Mock(),put_into_notification_queue=Mock())
        self.spi=patch.object(gpio,'spi_state',return_value=READY);self.spi.start();self.addCleanup(self.spi.stop)
    def add(self,**changes):
        return gpio.add_string(self.executer,{'source':'device_0','name':'Second string','count':425,'strip':'ws2811_strip_grb','brightness':10,**changes})
    def test_adds_distinct_spi_string_copies_colors_and_retains_primary_exactly(self):
        result=self.add();second=self.config['device_configs'][result['device']]
        self.assertEqual(self.config['device_configs']['device_0'],self.original)
        self.assertEqual(second['led_count'],425);self.assertEqual(second['output']['output_raspi']['led_pin'],10)
        self.assertEqual(second['output']['output_raspi']['led_channel'],0)
        self.assertEqual(second['effects']['effect_song_show']['bass_color'],'#ff4000')
        self.assertEqual(second['effects']['effect_song_show']['sync_mode'],'paired')
        self.assertEqual(second['effects']['last_effect'],'effect_song_show')
        self.executer.put_into_notification_queue.assert_called_once_with(NotificationEnum.song_show_refresh,'device_1')
    def test_same_length_keeps_custom_groups(self):
        result=self.add(count=1200);d=self.config['device_configs'][result['device']]
        self.assertEqual(d['effects']['effect_song_show']['sync_groups'],self.original['effects']['effect_song_show']['sync_groups'])
    def test_duplicate_output_is_rejected_without_saving_again(self):
        self.add();self.executer.save_config.reset_mock()
        with self.assertRaises(ValueError):self.add(name='Third string')
        self.executer.save_config.assert_not_called();self.assertEqual(len(self.config['device_configs']),2)
    def test_not_ready_and_bad_inputs_never_modify_live_config(self):
        before=copy.deepcopy(self.config)
        for data in [{'count':0},{'count':True},{'count':10001},{'brightness':101},{'source':'missing'},{'strip':'garbage'},{'name':'<script>'}]:
            with self.assertRaises(ValueError):self.add(**data)
        with patch.object(gpio,'spi_state',return_value={**READY,'ready':False}):
            with self.assertRaisesRegex(ValueError,'reboot'):self.add()
        self.assertEqual(self.config,before);self.executer.save_config.assert_not_called()
    def test_save_failure_rolls_back_new_config_entry(self):
        self.executer.save_config.side_effect=OSError('disk full')
        with self.assertRaises(OSError):self.add()
        self.assertEqual(self.config['device_configs'],{'device_0':self.original})
        self.executer.put_into_notification_queue.assert_not_called()
    def test_long_line_gets_appropriate_starting_fps(self):
        result=self.add(count=10000);d=self.config['device_configs'][result['device']]
        self.assertLessEqual(d['fps'],1/(10000*30e-6+.004))
    def test_spi_channel_and_buffer_constraints(self):
        self.add();d=self.config['device_configs']['device_1']
        d['output']['output_raspi']['led_channel']=1
        with self.assertRaisesRegex(ValueError,'channel 0'):gpio.validate_layout(self.config)
        d['output']['output_raspi']['led_channel']=0;d['led_count']=20000
        with self.assertRaisesRegex(ValueError,'buffer'):gpio.validate_layout(self.config)

class SpiPreparationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.boot=Path(temp.name)
        (self.boot/'config.txt').write_text('[all]\ndtparam=audio=on\n')
        (self.boot/'cmdline.txt').write_text('console=serial0,115200 root=PARTUUID=123 quiet spidev.bufsiz=4096\n')
        self.paths=patch.object(gpio,'boot_path',return_value=self.boot);self.paths.start();self.addCleanup(self.paths.stop)
        self.hardware=patch.object(gpio,'model',return_value='Raspberry Pi 4 Model B');self.hardware.start();self.addCleanup(self.hardware.stop)
    def test_preparation_backs_up_both_files_retains_audio_and_is_idempotent(self):
        original=(self.boot/'config.txt').read_bytes();result=gpio.prepare_spi()
        self.assertTrue(result['reboot_required']);config=(self.boot/'config.txt').read_text();command=(self.boot/'cmdline.txt').read_text()
        self.assertIn('dtparam=audio=on',config);self.assertNotIn('audio=off',config)
        self.assertIn('core_freq_min=500',config);self.assertIn('dtparam=spi=on',config)
        self.assertEqual(command.count('spidev.bufsiz='),1);self.assertIn('spidev.bufsiz=131072',command)
        self.assertEqual(next(self.boot.glob('config.txt.mlsc-spi-*.bak')).read_bytes(),original)
        gpio.prepare_spi();self.assertEqual((self.boot/'config.txt').read_text().count('# BEGIN MLSC GPIO10 SPI'),1)
    def test_partial_write_failure_restores_both_original_files(self):
        before={p.name:p.read_bytes() for p in self.boot.iterdir()};real=Path.replace
        def replace(path,target):
            if path.name=='cmdline.txt.mlsc-spi.tmp':raise OSError('write failed')
            return real(path,target)
        with patch.object(Path,'replace',replace):
            with self.assertRaises(OSError):gpio.prepare_spi()
        for name,data in before.items():self.assertEqual((self.boot/name).read_bytes(),data)
    def test_pi5_rejected_before_boot_changes(self):
        with patch.object(gpio,'model',return_value='Raspberry Pi 5 Model B'):
            with self.assertRaises(ValueError):gpio.prepare_spi()
        self.assertFalse(list(self.boot.glob('*.bak')))

class IncrementalStartTests(unittest.TestCase):
    def test_manager_starts_new_output_without_restarting_primary(self):
        tree=ast.parse((ROOT/'libs/device_manager.py').read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef));fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_sync_gpio_devices')
        created=[]
        def device(*args):
            result=Mock();created.append(result);return result
        scope={'Device':device};exec(compile(ast.Module(body=[fn],type_ignores=[]),'manager','exec'),scope)
        primary=Mock();manager=NS(_devices={'device_0':primary},_config={'device_configs':{'device_0':{},'device_1':{}}},_color_service_global=object())
        scope['_sync_gpio_devices'](manager)
        primary.start_device.assert_not_called();primary.stop_device.assert_not_called();created[0].start_device.assert_called_once()
    def test_gpio10_is_accepted_by_main_config_schema(self):
        tree=ast.parse((ROOT/'libs/webserver/schemas/config_validator_service.py').read_text());found=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Dict):
                for key,value in zip(n.keys,n.values):
                    if isinstance(key,ast.Constant) and key.value=='led_pin' and isinstance(value,ast.Dict):
                        for k,v in zip(value.keys,value.values):
                            if isinstance(k,ast.Constant) and k.value=='enum':found.append(ast.literal_eval(v))
        self.assertTrue(any(10 in pins for pins in found))


class ManagerNotificationTests(unittest.TestCase):
    def test_new_string_uses_incremental_start_and_no_existing_restart(self):
        tree=ast.parse((ROOT/'libs/device_manager.py').read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef));fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='check_config_changes')
        scope={'logger':Mock(),'NotificationEnum':NotificationEnum};exec(compile(ast.Module(body=[fn],type_ignores=[]),'manager','exec'),scope)
        manager=NS(_config={'device_configs':{'device_0':{}}},_devices={'device_0':Mock()},_studio_owns_output=False,_all_devices_ID='all_devices',_notification_queue_in=NS(empty=lambda:False,get_blocking=lambda:NS(notification_enum=NotificationEnum.song_show_refresh,device_id='device_1')),_sync_gpio_devices=Mock(),restart_device=Mock(),reinit_devices=Mock())
        manager.reload_config=lambda:setattr(manager,'_config',{'device_configs':{'device_0':{},'device_1':{}}})
        scope['check_config_changes'](manager)
        manager._sync_gpio_devices.assert_called_once();manager.restart_device.assert_not_called();manager.reinit_devices.assert_not_called()
