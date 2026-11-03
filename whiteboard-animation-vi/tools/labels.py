"""Add cut-paper text cards to a video, with a paper-slap sound per card.
Usage: python tools/labels.py in.mp4 sfx_in.wav sfx_out.wav out.mp4 cards.json
cards.json: [{"lines": ["This is Klara."], "x": 255, "y": 175, "t": 0.45, "size": 50, "paper": [236,228,214], "ink": [20,20,20], "angle": 4}, ...]
"""
import sys, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
import json
vid, wav_in, wav_out, out, spec = sys.argv[1:6]
W, H = map(int, subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','csv=p=0',vid],capture_output=True,text=True).stdout.strip().split(','))
FPS = 30
FONT = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
rng = np.random.default_rng(3)

def label(lines, size, paper, ink, angle):
    f = ImageFont.truetype(FONT, size)
    pad, lh = int(size*.45), int(size*1.08)
    tw = max(f.getbbox(l)[2] for l in lines); th = lh*len(lines)
    w, h = tw+2*pad, th+int(pad*1.4)
    m = 30; im = Image.new('RGBA', (w+2*m, h+2*m), (0,0,0,0))
    j = lambda: rng.uniform(-size*.12, size*.12)   # torn-paper corners
    poly = [(m+j(), m+j()), (m+w+j(), m+j()), (m+w+j(), m+h+j()), (m+j(), m+h+j())]
    sh = Image.new('L', im.size, 0); ImageDraw.Draw(sh).polygon([(x+5,y+7) for x,y in poly], fill=90)
    im.putalpha(0); im = Image.new('RGBA', im.size, (0,0,0,0))
    im.paste((0,0,0,255), mask=sh.filter(ImageFilter.GaussianBlur(6)))
    pm = Image.new('L', im.size, 0); ImageDraw.Draw(pm).polygon(poly, fill=255)
    tex = (np.array(paper)[None,None,:] + rng.normal(0,5,(im.size[1],im.size[0],1))).clip(0,255).astype(np.uint8)
    im.paste(Image.fromarray(tex,'RGB'), mask=pm)
    d = ImageDraw.Draw(im)
    for i,l in enumerate(lines): d.text((m+pad, m+int(pad*.55)+i*lh), l, font=f, fill=ink)
    return im.rotate(angle, resample=Image.BICUBIC, expand=True)

L = [  # (image, center x, center y, start time)
 (label(['This is Klara.'], 50, (236,228,214), (20,20,20), 4), 255, 175, 0.45),
 (label(['Klara is', 'oppressed.'], 58, (24,24,24), (236,228,214), -3), 250, 390, 2.35)]

def ease(u): return 1-(1-u)**3
dec = subprocess.Popen(['ffmpeg','-loglevel','error','-i',vid,'-f','rawvideo','-pix_fmt','rgb24','-'], stdout=subprocess.PIPE)
enc = subprocess.Popen(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
     '-i',wav_out,'-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',out], stdin=subprocess.PIPE)
# audio first: add paper slaps
SR, a = wavfile.read(wav_in); a = a.astype(np.float32)/32767
for _,_,_,t0 in L:
    n = int(.25*SR); tt = np.arange(n)/SR
    slap = sosfilt(butter(2,[600,5000],'bandpass',fs=SR,output='sos'), np.random.default_rng(1).standard_normal(n))*np.exp(-tt*28)
    thump = np.sin(2*np.pi*110*tt)*np.exp(-tt*35)*.6
    i0 = int((t0+.1)*SR); a[i0:i0+n] += .55*(slap/np.abs(slap).max()+thump)[:len(a)-i0]
wavfile.write(wav_out, SR, (a/np.abs(a).max()*.8*32767).astype(np.int16))
i = 0
while True:
    buf = dec.stdout.read(W*H*3)
    if len(buf) < W*H*3: break
    fr = Image.frombytes('RGB', (W,H), buf); t = i/FPS
    for im,cx,cy,t0 in L:
        u = (t-t0)/0.18
        if u <= 0: continue
        u = min(u,1); s = 1.35-0.35*ease(u)
        im2 = im.resize((int(im.width*s), int(im.height*s)), Image.BICUBIC)
        if u < 1: im2.putalpha(im2.getchannel('A').point(lambda v: int(v*ease(u))))
        fr.paste(im2, (int(cx-im2.width/2), int(cy-im2.height/2)), im2)
    enc.stdin.write(fr.tobytes()); i += 1
enc.stdin.close(); enc.wait(); print('frames', i)
