// HNLS Windows endpoint loopback sender. Uses Windows WASAPI; no third-party DLLs.
using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Threading;

namespace HNLSAudio {
 [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class DeviceEnumerator {}
 [ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
 interface IMMDeviceEnumerator {
  [PreserveSig] int EnumAudioEndpoints(int flow, uint mask, out IntPtr devices);
  [PreserveSig] int GetDefaultAudioEndpoint(int flow, int role, out IMMDevice device);
  [PreserveSig] int GetDevice([MarshalAs(UnmanagedType.LPWStr)] string id, out IMMDevice device);
  [PreserveSig] int RegisterEndpointNotificationCallback(IntPtr callback);
  [PreserveSig] int UnregisterEndpointNotificationCallback(IntPtr callback);
 }
 [ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
 interface IMMDevice {
  [PreserveSig] int Activate(ref Guid iid, uint context, IntPtr activation, [MarshalAs(UnmanagedType.IUnknown)] out object instance);
  [PreserveSig] int OpenPropertyStore(uint access, out IntPtr properties);
  [PreserveSig] int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
  [PreserveSig] int GetState(out uint state);
 }
 [ComImport, Guid("1CB9AD4C-DBFA-4C32-B178-C2F568A703B2"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
 interface IAudioClient {
  [PreserveSig] int Initialize(int mode, uint flags, long duration, long periodicity, IntPtr format, IntPtr session);
  [PreserveSig] int GetBufferSize(out uint frames);
  [PreserveSig] int GetStreamLatency(out long latency);
  [PreserveSig] int GetCurrentPadding(out uint frames);
  [PreserveSig] int IsFormatSupported(int mode, IntPtr format, out IntPtr closest);
  [PreserveSig] int GetMixFormat(out IntPtr format);
  [PreserveSig] int GetDevicePeriod(out long normal, out long minimum);
  [PreserveSig] int Start();
  [PreserveSig] int Stop();
  [PreserveSig] int Reset();
  [PreserveSig] int SetEventHandle(IntPtr handle);
  [PreserveSig] int GetService(ref Guid iid, [MarshalAs(UnmanagedType.IUnknown)] out object service);
 }
 [ComImport, Guid("C8ADBD64-E71E-48A0-A4DE-185C395CD317"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
 interface IAudioCaptureClient {
  [PreserveSig] int GetBuffer(out IntPtr data, out uint frames, out uint flags, out ulong devicePosition, out ulong qpc);
  [PreserveSig] int ReleaseBuffer(uint frames);
  [PreserveSig] int GetNextPacketSize(out uint frames);
 }
 public static class Sender {
  static volatile bool stop;
  public static void Stop() { stop = true; }
  static void Check(int hr) { if (hr < 0) Marshal.ThrowExceptionForHR(hr); }
  public static byte[] Key(string hex) {
   if (hex == null || hex.Length != 64) throw new ArgumentException("Invalid HNLS connection key.");
   byte[] bytes = new byte[32];
   for (int n=0;n<32;n++) bytes[n]=Convert.ToByte(hex.Substring(n*2,2),16);
   return bytes;
  }
  public static byte[] Packet(byte[] key, byte[] stream, uint sequence, uint rate, byte[] pcm) {
   if (stream.Length!=16 || pcm.Length<4 || pcm.Length>1024 || pcm.Length%4!=0) throw new ArgumentException("Invalid audio packet.");
   byte[] header;
   using (var memory=new MemoryStream()) using (var writer=new BinaryWriter(memory)) {
    writer.Write(new byte[]{72,78,65,49});writer.Write(stream);writer.Write(sequence);writer.Write(rate);
    writer.Write((ushort)(pcm.Length/4));writer.Write((ushort)2);header=memory.ToArray();
   }
   byte[] body=new byte[header.Length+pcm.Length];Buffer.BlockCopy(header,0,body,0,header.Length);Buffer.BlockCopy(pcm,0,body,header.Length,pcm.Length);
   byte[] tag;using(var mac=new HMACSHA256(key)) tag=mac.ComputeHash(body);
   byte[] packet=new byte[body.Length+32];Buffer.BlockCopy(header,0,packet,0,header.Length);Buffer.BlockCopy(tag,0,packet,header.Length,32);Buffer.BlockCopy(pcm,0,packet,header.Length+32,pcm.Length);return packet;
  }
  public static short Sample(byte[] data, int offset, int bits, bool floating) {
   double value;
   if (floating) value=BitConverter.ToSingle(data,offset);
   else if (bits==16) return BitConverter.ToInt16(data,offset);
   else if (bits==24) { int sample=data[offset]|(data[offset+1]<<8)|(data[offset+2]<<16);if((sample&0x800000)!=0)sample|=unchecked((int)0xff000000);return (short)(sample>>8); }
   else if (bits==32) return (short)(BitConverter.ToInt32(data,offset)>>16);
   else throw new NotSupportedException("Choose a 16, 24 or 32 bit stereo output in Windows Sound settings.");
   if (Double.IsNaN(value)) value=0;
   return (short)Math.Max(-32768,Math.Min(32767,Math.Round(value*32768)));
  }
  public static void SelfTest(string output) {
   byte[] key=new byte[32],stream=new byte[16];for(int n=0;n<32;n++)key[n]=(byte)n;for(int n=0;n<16;n++)stream[n]=(byte)n;
   if(Sample(BitConverter.GetBytes(1f),0,32,true)!=32767 || Sample(BitConverter.GetBytes(-1f),0,32,true)!=-32768 || Sample(new byte[]{0,0,128},0,24,false)!=-32768)throw new Exception("PCM conversion failed");
   File.WriteAllBytes(output,Packet(key,stream,7,48000,new byte[]{0,128,255,127,0,0,1,0}));
  }
  public static void Run(string host, int port, string keyHex) {
   stop=false;var key=Key(keyHex);byte[] stream=new byte[16];using(var random=RandomNumberGenerator.Create())random.GetBytes(stream);
   IMMDeviceEnumerator enumerator=null;IMMDevice device=null;IAudioClient client=null;IAudioCaptureClient capture=null;IntPtr format=IntPtr.Zero;
   ConsoleCancelEventHandler cancel=delegate(object s, ConsoleCancelEventArgs e){stop=true;e.Cancel=true;};
   Console.CancelKeyPress+=cancel;
   try {
    enumerator=(IMMDeviceEnumerator)new DeviceEnumerator();Check(enumerator.GetDefaultAudioEndpoint(0,1,out device));
    Guid clientId=typeof(IAudioClient).GUID;object instance;Check(device.Activate(ref clientId,23,IntPtr.Zero,out instance));client=(IAudioClient)instance;
    Check(client.GetMixFormat(out format));int tag=(ushort)Marshal.ReadInt16(format,0);int channels=(ushort)Marshal.ReadInt16(format,2);uint rate=(uint)Marshal.ReadInt32(format,4);int align=(ushort)Marshal.ReadInt16(format,12);int bits=(ushort)Marshal.ReadInt16(format,14);
    bool floating=tag==3;
    if(tag==65534) {
     byte[] bytes=new byte[16];Marshal.Copy(IntPtr.Add(format,24),bytes,0,16);Guid sub=new Guid(bytes);
     floating=sub==new Guid("00000003-0000-0010-8000-00aa00389b71");
     if(!floating && sub!=new Guid("00000001-0000-0010-8000-00aa00389b71"))throw new NotSupportedException("Unsupported Windows audio format.");
    } else if(tag!=1 && tag!=3) throw new NotSupportedException("Choose PCM stereo in Windows Sound settings.");
    if(channels<1 || channels>2 || align!=channels*(bits/8) || (floating && bits!=32) || (!floating && bits!=16 && bits!=24 && bits!=32))throw new NotSupportedException("Select a mono or stereo Windows playback device (not surround). Then restart this sender.");
    if(rate!=44100 && rate!=48000 && rate!=88200 && rate!=96000 && rate!=192000)throw new NotSupportedException("Choose 44.1 or 48 kHz in Windows Sound settings, then restart.");
    // Shared mode, AUDCLNT_STREAMFLAGS_LOOPBACK. Use the endpoint's native mix format.
    Check(client.Initialize(0,0x20000,1000000,0,format,IntPtr.Zero));
    Guid captureId=typeof(IAudioCaptureClient).GUID;object service;Check(client.GetService(ref captureId,out service));capture=(IAudioCaptureClient)service;
    IPAddress address=null;foreach(var candidate in Dns.GetHostAddresses(host))if(candidate.AddressFamily==AddressFamily.InterNetwork){address=candidate;break;}
    if(address==null)throw new Exception("Cannot resolve the main Pi IPv4 address: "+host);
    using(var udp=new UdpClient(AddressFamily.InterNetwork)) {
     udp.Connect(address,port);Check(client.Start());uint sequence=0;
     Console.WriteLine("Sending Windows playback audio to "+host+":"+port+" at "+rate+" Hz.");
     Console.WriteLine("Play Pandora or Spotify on this Windows playback device. Q or Ctrl+C stops sending.");
     Console.WriteLine("This captures ALL audio on this playback device, including alerts. Keep its volume above zero.");
     while(!stop) {
      if(!Console.IsInputRedirected && Console.KeyAvailable && Console.ReadKey(true).Key==ConsoleKey.Q)break;
      uint available;Check(capture.GetNextPacketSize(out available));int packets=0;
      while(available>0 && !stop && packets++<64) {
       IntPtr pointer;uint frames,flags;ulong position,qpc;Check(capture.GetBuffer(out pointer,out frames,out flags,out position,out qpc));
       try {
        if(frames>rate)throw new Exception("Unexpected capture buffer size.");
        byte[] raw=new byte[checked((int)frames*align)];if((flags&2)==0)Marshal.Copy(pointer,raw,0,raw.Length);
        for(int start=0;start<(int)frames;start+=256) {
         int length=Math.Min(256,(int)frames-start);byte[] pcm=new byte[length*4];
         for(int frame=0;frame<length;frame++)for(int channel=0;channel<2;channel++) {
          int src=(start+frame)*align+Math.Min(channel,channels-1)*(bits/8);short sample=Sample(raw,src,bits,floating);int dst=frame*4+channel*2;
          pcm[dst]=(byte)(sample&255);pcm[dst+1]=(byte)((sample>>8)&255);
         }
         byte[] packet=Packet(key,stream,sequence++,rate,pcm);udp.Send(packet,packet.Length);
         if(sequence==UInt32.MaxValue)throw new Exception("Restart the sender to refresh its sequence.");
        }
       } finally {Check(capture.ReleaseBuffer(frames));}
       Check(capture.GetNextPacketSize(out available));
      }
      Thread.Sleep(5);
     }
    }
   } finally {
    Console.CancelKeyPress-=cancel;
    if(client!=null)client.Stop();if(format!=IntPtr.Zero)Marshal.FreeCoTaskMem(format);
    if(capture!=null)Marshal.ReleaseComObject(capture);if(client!=null)Marshal.ReleaseComObject(client);if(device!=null)Marshal.ReleaseComObject(device);if(enumerator!=null)Marshal.ReleaseComObject(enumerator);
   }
  }
 }
}
