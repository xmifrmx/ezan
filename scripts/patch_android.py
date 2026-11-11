import re,os
from PIL import Image
A="android/app/src/main/"
# izinler
p=A+"AndroidManifest.xml";s=open(p,encoding="utf-8").read()
perms=["POST_NOTIFICATIONS","SCHEDULE_EXACT_ALARM","RECEIVE_BOOT_COMPLETED","VIBRATE"]
add="".join(f'    <uses-permission android:name="android.permission.{x}" />\n' for x in perms if x not in s)
s=s.replace("<application",add+"    <application",1);open(p,"w",encoding="utf-8").write(s)
# minSdk 24 = Android 7.0
v="android/variables.gradle";t=open(v).read();t=re.sub(r"minSdkVersion\s*=\s*\d+","minSdkVersion = 24",t);open(v,"w").write(t)
# ikonlar
src=Image.open("scripts/icon.png").convert("RGBA")
for d,sz,fg in [("mdpi",48,108),("hdpi",72,162),("xhdpi",96,216),("xxhdpi",144,324),("xxxhdpi",192,432)]:
    o=A+f"res/mipmap-{d}/";os.makedirs(o,exist_ok=True)
    src.resize((sz,sz),Image.LANCZOS).save(o+"ic_launcher.png");src.resize((sz,sz),Image.LANCZOS).save(o+"ic_launcher_round.png")
    c=Image.new("RGBA",(fg,fg),(0,0,0,0));k=int(fg*0.62);c.paste(src.resize((k,k),Image.LANCZOS),((fg-k)//2,(fg-k)//2));c.save(o+"ic_launcher_foreground.png")
b=A+"res/values/ic_launcher_background.xml"
open(b,"w").write('<?xml version="1.0" encoding="utf-8"?>\n<resources><color name="ic_launcher_background">#0B1B3A</color></resources>\n')
print("patched")
