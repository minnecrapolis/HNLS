import ast,copy,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'src/controller/server/libs';sys.path.insert(0,str(LIB.parent))
from libs import color_ranges as m
from libs.outputs.output import Output

def fixture(order='GRB',count=750,kind='output_raspi'):
 d={'device_name':'Second Strip','led_strip':'ws2811_strip_'+order.lower(),'led_count':count,'led_brightness':25,'output_type':kind}
 return {'device_configs':{'device_1':d}}
class RangeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.file=Path(self.temp.name)/'ranges.json';self.p=patch.object(m,'path',return_value=self.file);self.p.start();self.addCleanup(self.p.stop);m.CACHE.update(at=-1,stamp=None,devices={});self.config=fixture();self.d=self.config['device_configs']['device_1']
 def save(self,rows):return m.save('device_1',rows,self.config)
 def test_all_36_default_and_segment_orders_produce_correct_physical_rgb(self):
  frame=np.array([[255,0,0,17],[0,255,0,83],[0,0,255,211]],dtype=np.uint8)
  for default in m.ORDERS:
   self.d['led_strip']='ws2811_strip_'+default.lower()
   for order in m.ORDERS:
    with self.subTest(default=default,order=order):
     self.save([{'first':1,'last':4,'order':order}]);adjusted=m.apply(frame,'device_1',self.d)
     wire=adjusted[['RGB'.index(c) for c in default]];observed=np.zeros_like(frame)
     for index,channel in enumerate(order):observed['RGB'.index(channel)]=wire[index]
     np.testing.assert_array_equal(observed,frame)
 def test_601_to_650_is_exactly_fifty_pixels_and_source_unchanged(self):
  self.save([{'first':601,'last':650,'order':'RGB'}]);frame=np.tile(np.array([[255],[0],[0]],dtype=np.uint8),(1,750));before=frame.copy();out=m.apply(frame,'device_1',self.d)
  np.testing.assert_array_equal(out[:,:600],frame[:,:600]);np.testing.assert_array_equal(out[:,650:],frame[:,650:]);np.testing.assert_array_equal(out[:,600:650],np.tile([[0],[255],[0]],(1,50)));np.testing.assert_array_equal(frame,before)
 def test_no_ranges_and_same_order_are_no_copy_identity(self):
  frame=np.ones((3,750));self.assertIs(m.apply(frame,'device_1',self.d),frame);self.save([{'first':1,'last':750,'order':'GRB'}]);self.assertIs(m.apply(frame,'device_1',self.d),frame)
 def test_adjacent_ranges_different_orders_and_gaps(self):
  self.save([{'first':651,'last':700,'order':'BGR'},{'first':601,'last':650,'order':'RGB'}]);frame=np.tile([[10],[30],[90]],(1,750));out=m.apply(frame,'device_1',self.d);self.assertFalse(np.array_equal(out[:,600:650],out[:,650:700]));np.testing.assert_array_equal(out[:,700:],frame[:,700:]);self.assertEqual(m.read()['devices']['device_1'][0]['first'],601)
 def test_overlaps_out_of_bounds_bad_order_bool_and_unknown_device_rejected(self):
  self.save([{'first':601,'last':650,'order':'RGB'}]);before=self.file.read_bytes()
  bad=[[{'first':0,'last':50,'order':'RGB'}],[{'first':700,'last':800,'order':'RGB'}],[{'first':True,'last':50,'order':'RGB'}],[{'first':1,'last':50,'order':'RGBW'}],[{'first':1,'last':50,'order':'RGB'},{'first':50,'last':60,'order':'GRB'}]]
  for rows in bad:
   with self.assertRaises(ValueError):self.save(rows)
  with self.assertRaises(ValueError):m.save('missing',[],self.config)
  self.assertEqual(before,self.file.read_bytes())
 def test_alias_or_rgbw_requires_explicit_supported_type_but_can_clear(self):
  self.save([{'first':1,'last':50,'order':'RGB'}]);self.d['led_strip']='ws2812_strip'
  with patch.dict(sys.modules,{'_rpi_ws281x':None}),self.assertRaises(ValueError):self.save([{'first':1,'last':50,'order':'RGB'}])
  self.save([]);self.assertEqual(m.read()['devices']['device_1'],[])
 def test_settings_private_persistent_and_delete_cleans_reused_device_id(self):
  self.save([{'first':601,'last':650,'order':'RGB','name':' Last set '}]);self.assertEqual(self.file.stat().st_mode&0o777,0o600);self.assertEqual(m.view(self.config)['outputs'][0]['ranges'][0]['name'],'Last set');m.forget('device_1');self.assertNotIn('device_1',m.read()['devices'])
 def test_failed_write_does_not_change_previous_settings(self):
  self.save([{'first':601,'last':650,'order':'RGB'}]);before=self.file.read_bytes()
  with patch.object(Path,'replace',side_effect=OSError('disk error')),self.assertRaises(OSError):self.save([])
  self.assertEqual(self.file.read_bytes(),before)
 def test_bad_reload_retains_last_good_mapping(self):
  self.save([{'first':1,'last':50,'order':'RGB'}]);frame=np.tile([[255],[0],[0]],(1,750));first=m.apply(frame,'device_1',self.d);self.file.write_text('{broken');m.CACHE['at']=-1;np.testing.assert_array_equal(m.apply(frame,'device_1',self.d),first)
 def test_count_reduction_is_clipped_without_worker_failure_and_reported_in_ui(self):
  self.save([{'first':601,'last':650,'order':'RGB'}]);self.d['led_count']=600;frame=np.ones((3,600));self.assertIs(m.apply(frame,'device_1',self.d),frame);self.assertTrue(m.view(self.config)['outputs'][0]['error'])
 def test_unknown_base_or_rgbw_after_change_blacks_only_mapped_range(self):
  self.save([{'first':601,'last':650,'order':'RGB'}]);self.d['led_strip']='sk6812_strip_grbw';frame=np.ones((4,750))*40;out=m.apply(frame,'device_1',self.d);np.testing.assert_array_equal(out[:,600:650],0);np.testing.assert_array_equal(out[:,:600],40)
 def test_native_ws2812_alias_is_resolved_from_driver_constants_without_gpio(self):
  self.d['led_strip']='ws2812_strip';ws=NS(WS2812_STRIP=23,WS2811_STRIP_RGB=12,WS2811_STRIP_GRB=23)
  with patch.dict(sys.modules,{'_rpi_ws281x':ws}):
   self.assertEqual(m.base_order(self.d),'GRB');self.save([{'first':601,'last':650,'order':'RGB'}]);out=m.apply(np.tile([[255],[0],[0]],(1,750)),'device_1',self.d);np.testing.assert_array_equal(out[:,600],[0,255,0])
  self.d['output_type']='output_udp';self.assertIsNone(m.base_order(self.d),'UDP generic alias must not pretend it uses native order')
 def test_device_identity_wins_over_equal_duplicate_configuration(self):
  duplicate=copy.deepcopy(self.d);self.config['device_configs']={'device_0':duplicate,'device_1':self.d};device=NS(config=self.config,device_config=self.d);self.save([{'first':1,'last':50,'order':'RGB'}]);out=Output(device).prepare_frame(np.tile([[255],[0],[0]],(1,750)));np.testing.assert_array_equal(out[:,0],[0,255,0])
 def test_native_packing_remains_rgb_and_compensation_runs_once(self):
  self.save([{'first':601,'last':650,'order':'RGB'}]);frame=np.tile([[255],[0],[0]],(1,750));base=Output(NS(config=self.config,device_config=self.d))
  tree=ast.parse((LIB/'outputs/output_raspi.py').read_text());node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='show');scope={'np':np};exec(compile(ast.Module(body=[node],type_ignores=[]),'native.py','exec'),scope)
  ws=NS(ws2811_led_set=Mock(),ws2811_render=Mock(return_value=0),WS2811_SUCCESS=0);output=NS(prepare_frame=base.prepare_frame,_led_count=750,_led_strip=self.d['led_strip'],channel=object(),_leds=object())
  with patch.dict(sys.modules,{'_rpi_ws281x':ws}):scope['show'](output,frame)
  calls=ws.ws2811_led_set.call_args_list;self.assertEqual(calls[0].args[2],255<<16);self.assertEqual(calls[600].args[2],255<<8);self.assertEqual(len(calls),750)
 def test_remote_transport_receives_precompensated_logical_channels_once(self):
  self.d['output_type']='output_udp';self.save([{'first':601,'last':650,'order':'RGB'}]);base=Output(NS(config=self.config,device_config=self.d));remote=Mock();output=NS(prepare_frame=base.prepare_frame,_remote=remote)
  tree=ast.parse((LIB/'outputs/output_udp.py').read_text());node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='show');scope={};exec(compile(ast.Module(body=[node],type_ignores=[]),'udp.py','exec'),scope);scope['show'](output,np.tile([[255],[0],[0]],(1,750)));remote.show.assert_called_once();np.testing.assert_array_equal(remote.show.call_args.args[0][:,600],[0,255,0])
 def test_delete_cleans_ranges_and_cleanup_failure_does_not_delete_device(self):
  import __future__
  tree=ast.parse((LIB/'webserver/blueprints/device_executer.py').read_text());node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='delete_device');scope={'DeviceNotFound':object()};exec(compile(ast.Module(body=[node],type_ignores=[]),'delete.py','exec',flags=__future__.annotations.compiler_flag),scope)
  self.save([{'first':601,'last':650,'order':'RGB'}]);ex=NS(_config=self.config,save_config=Mock(),refresh_device=Mock(),all_devices_id='all_devices')
  with patch.object(m,'forget',side_effect=OSError('bad settings')),self.assertRaises(OSError):scope['delete_device'](ex,'device_1')
  self.assertIn('device_1',self.config['device_configs']);ex.save_config.assert_not_called()
  with patch.dict(sys.modules,{'libs.remote_pixels':NS(forget=Mock())}):scope['delete_device'](ex,'device_1')
  self.assertNotIn('device_1',self.config['device_configs']);self.assertNotIn('device_1',m.read()['devices'])
 def test_api_endpoints_require_login(self):
  tree=ast.parse((LIB/'webserver/blueprints/device_api.py').read_text())
  for name in ['color_ranges_get','color_ranges_save']:
   node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name);self.assertTrue(any(isinstance(d,ast.Name) and d.id=='login_required' for d in node.decorator_list))
if __name__=='__main__':unittest.main()
