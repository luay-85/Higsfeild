"""Synthesize marker/brush/chime sound effects that follow on-screen drawing activity.
Usage: python tools/sfx.py video.mp4 out.wav
"""
import sys, subprocess, numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
vid, out = sys.argv[1], sys.argv[2]
W, H, FPS, SR = 270, 337, 30, 48000
raw = subprocess.run(['ffmpeg','-loglevel','error','-i',vid,'-vf',f'scale={W}:{H}','-f','rawvideo','-pix_fmt','gray','-'],capture_output=True).stdout
fr = np.frombuffer(raw,np.uint8).reshape(-1,H,W).astype(np.float32)
act = np.r_[0, np.abs(np.diff(fr,axis=0)).mean(axis=(1,2))]
act = np.convolve(act/(np.percentile(act,95)+1e-6), np.ones(3)/3, 'same').clip(0,1.3)
n = len(fr); dur = n/FPS; N = int(dur*SR); t = np.arange(N)/SR
env = np.interp(t, np.arange(n)/FPS, act)
rng = np.random.default_rng(7)
ink_end = dur*0.70*0.45; fill_end = dur*0.70
def bp(x,lo,hi): return sosfilt(butter(4,[lo,hi],'bandpass',fs=SR,output='sos'),x)
def strokes(rate, jitter):  # rhythmic stroke envelope
    ph = np.cumsum(rate*(1+jitter*np.interp(t,np.linspace(0,dur,40),rng.uniform(-1,1,40))))/SR
    return np.clip(np.sin(2*np.pi*ph),0,1)**0.6
def fade(a,b,w=0.08): return np.clip((t-a)/w,0,1)*np.clip((b-t)/w,0,1)
noise = rng.standard_normal(N)
marker = bp(noise,1800,7000)*(0.55+0.45*strokes(7,0.4))
squeak = np.sin(2*np.pi*np.cumsum(2400+300*np.sin(2*np.pi*3*t))/SR)*0.06*strokes(7,0.4)**3
ink = (marker+squeak)*fade(0.03,ink_end)
brush = bp(noise,350,2600)*(0.35+0.65*strokes(3.2,0.3))
fill = brush*fade(ink_end,fill_end,0.12)*0.8
mix = ink*np.clip(env,0.3,1.2) + fill*np.clip(env,0.55,1.2)*1.4
for f0,g in ((1046.5,1),(1568,0.5),(2093,0.25)):  # finish chime
    d = np.clip(t-fill_end,0,None)
    mix += 0.18*g*np.sin(2*np.pi*f0*d)*np.exp(-d*3.5)*(t>=fill_end)
mix += 0.004*bp(noise,80,400)  # room tone
mix = mix/np.abs(mix).max()*0.7
wavfile.write(out, SR, (mix*32767).astype(np.int16))
print(f'frames={n} ink_end={ink_end:.2f}s fill_end={fill_end:.2f}s')
