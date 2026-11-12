"""Canlı bildirim çubuğu (geri sayım + tablo + durum çubuğunda kalan dakika) için yerel Android kodu ekler.
Kullanım:  python3 scripts/patch_native_bar.py          -> ekler
           python3 scripts/patch_native_bar.py remove  -> geri alır (yedek derleme için)"""
import os,sys,shutil
A="android/app/src/main/"
PKG="com/ezanvaktim/app/"
J=A+"java/"+PKG
MAN=A+"AndroidManifest.xml"
BK_MAN="android/.orig_manifest.xml";BK_ACT="android/.orig_MainActivity.java"
FILES=[J+"Bar.java",J+"BarReceiver.java",J+"PrayerBarPlugin.java",A+"res/layout/notif_bar.xml"]

if len(sys.argv)>1 and sys.argv[1]=="remove":
    if os.path.exists(BK_MAN):shutil.copy(BK_MAN,MAN)
    if os.path.exists(BK_ACT):shutil.copy(BK_ACT,J+"MainActivity.java")
    for f in FILES:
        if os.path.exists(f):os.remove(f)
    print("canlı bildirim çubuğu kaldırıldı");sys.exit(0)

shutil.copy(MAN,BK_MAN)
if os.path.exists(J+"MainActivity.java"):shutil.copy(J+"MainActivity.java",BK_ACT)
os.makedirs(J,exist_ok=True);os.makedirs(A+"res/layout",exist_ok=True)

open(J+"MainActivity.java","w",encoding="utf-8").write('''package com.ezanvaktim.app;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(PrayerBarPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
''')

open(J+"PrayerBarPlugin.java","w",encoding="utf-8").write('''package com.ezanvaktim.app;

import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "PrayerBar")
public class PrayerBarPlugin extends Plugin {
    @PluginMethod
    public void update(PluginCall call) {
        String events = call.getString("events", "[]");
        Integer mode = call.getInt("mode", 1);
        Bar.save(getContext(), events, mode == null ? 1 : mode.intValue());
        Bar.refresh(getContext());
        call.resolve();
    }
}
''')

open(J+"BarReceiver.java","w",encoding="utf-8").write('''package com.ezanvaktim.app;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class BarReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        Bar.refresh(context);
    }
}
''')

open(J+"Bar.java","w",encoding="utf-8").write('''package com.ezanvaktim.app;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.PorterDuff;
import android.graphics.PorterDuffXfermode;
import android.graphics.Typeface;
import android.graphics.drawable.Icon;
import android.os.Build;
import android.os.SystemClock;
import android.view.View;
import android.widget.RemoteViews;
import org.json.JSONArray;
import org.json.JSONObject;

/** Bildirim çubuğundaki canlı vakit sayacı. Sayaç sistem tarafından (Chronometer) canlı akar;
 *  uygulama kapalıyken de çalışır. Alarm yalnızca vakit değişiminde ve son 1 saatte dakikada bir simgeyi günceller. */
public final class Bar {
    static final int ID = 7001;
    static final String CH = "ezan_bar";
    static final String ACT = "com.ezanvaktim.app.BAR_TICK";

    private Bar() {}

    static void save(Context c, String events, int mode) {
        c.getSharedPreferences("bar", Context.MODE_PRIVATE).edit().putString("ev", events).putInt("mode", mode).apply();
    }

    static void refresh(Context c) {
        try {
            doRefresh(c);
        } catch (Throwable t) {
            // uygulamayı asla çökertme
        }
    }

    private static void doRefresh(Context c) throws Exception {
        SharedPreferences p = c.getSharedPreferences("bar", Context.MODE_PRIVATE);
        String js = p.getString("ev", null);
        int mode = p.getInt("mode", 0);
        NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;
        if (js == null || mode == 0) {
            nm.cancel(ID);
            cancelAlarm(c);
            return;
        }
        JSONArray a = new JSONArray(js);
        long now = System.currentTimeMillis();
        long t = 0;
        String name = "", hour = "", label = "", table = "";
        for (int i = 0; i < a.length(); i++) {
            JSONObject o = a.getJSONObject(i);
            long x = o.getLong("t");
            if (x > now) {
                t = x;
                name = o.getString("n");
                hour = o.getString("h");
                label = o.getString("l");
                table = o.getString("tb");
                break;
            }
        }
        if (t == 0) {
            nm.cancel(ID);
            cancelAlarm(c);
            return;
        }
        long rem = t - now;
        int min = (int) ((rem + 59999L) / 60000L);

        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(CH, "Vakit sayacı", NotificationManager.IMPORTANCE_LOW);
            ch.setShowBadge(false);
            ch.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
            nm.createNotificationChannel(ch);
        }

        RemoteViews rv = new RemoteViews(c.getPackageName(), R.layout.notif_bar);
        if (mode == 3) {
            rv.setTextViewText(R.id.bar_title, "Sıradaki vakit: " + name + " · " + hour);
            rv.setViewVisibility(R.id.bar_chrono, View.GONE);
        } else {
            rv.setTextViewText(R.id.bar_title, label + " kalan süre");
            rv.setViewVisibility(R.id.bar_chrono, View.VISIBLE);
            rv.setChronometer(R.id.bar_chrono, SystemClock.elapsedRealtime() + rem, null, true);
            rv.setChronometerCountDown(R.id.bar_chrono, true);
        }
        if (mode == 2) {
            rv.setViewVisibility(R.id.bar_table, View.GONE);
        } else {
            rv.setTextViewText(R.id.bar_table, table);
            rv.setViewVisibility(R.id.bar_table, View.VISIBLE);
        }

        Notification.Builder b = Build.VERSION.SDK_INT >= 26 ? new Notification.Builder(c, CH) : new Notification.Builder(c);
        b.setSmallIcon(icon(min));
        b.setCustomContentView(rv);
        b.setStyle(new Notification.DecoratedCustomViewStyle());
        b.setOngoing(true);
        b.setOnlyAlertOnce(true);
        b.setShowWhen(false);
        b.setCategory(Notification.CATEGORY_STATUS);
        b.setVisibility(Notification.VISIBILITY_PUBLIC);
        if (Build.VERSION.SDK_INT < 26) b.setPriority(Notification.PRIORITY_LOW);
        Intent li = c.getPackageManager().getLaunchIntentForPackage(c.getPackageName());
        if (li != null) {
            b.setContentIntent(PendingIntent.getActivity(c, 0, li, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT));
        }
        nm.notify(ID, b.build());

        long next = rem > 3600000L ? t - 3600000L + 300L : t - (long) (min - 1) * 60000L + 300L;
        if (next <= now) next = now + 1000L;
        setAlarm(c, next);
    }

    /** 60 dakikadan az kaldığında kalan dakikayı, aksi halde hilal çizer. */
    private static Icon icon(int min) {
        int s = 96;
        Bitmap bm = Bitmap.createBitmap(s, s, Bitmap.Config.ARGB_8888);
        Canvas cv = new Canvas(bm);
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setColor(Color.WHITE);
        if (min <= 60) {
            p.setTypeface(Typeface.DEFAULT_BOLD);
            p.setTextAlign(Paint.Align.CENTER);
            p.setTextSize(70f);
            Paint.FontMetrics fm = p.getFontMetrics();
            cv.drawText(String.valueOf(min), s / 2f, s / 2f - (fm.ascent + fm.descent) / 2f, p);
        } else {
            cv.drawCircle(s / 2f, s / 2f, 40f, p);
            Paint q = new Paint(Paint.ANTI_ALIAS_FLAG);
            q.setXfermode(new PorterDuffXfermode(PorterDuff.Mode.CLEAR));
            cv.drawCircle(s / 2f + 18f, s / 2f - 10f, 36f, q);
        }
        return Icon.createWithBitmap(bm);
    }

    private static PendingIntent alarmPi(Context c) {
        Intent i = new Intent(c, BarReceiver.class);
        i.setAction(ACT);
        return PendingIntent.getBroadcast(c, ID, i, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    static void cancelAlarm(Context c) {
        AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
        if (am != null) am.cancel(alarmPi(c));
    }

    private static void setAlarm(Context c, long at) {
        AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
        if (am == null) return;
        PendingIntent pi = alarmPi(c);
        try {
            if (Build.VERSION.SDK_INT >= 31 && !am.canScheduleExactAlarms()) {
                am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi);
            } else {
                am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi);
            }
        } catch (Exception e) {
            try {
                am.set(AlarmManager.RTC_WAKEUP, at, pi);
            } catch (Exception ignored) {
            }
        }
    }
}
''')

open(A+"res/layout/notif_bar.xml","w",encoding="utf-8").write('''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:orientation="vertical"
    android:paddingTop="2dp"
    android:paddingBottom="2dp">

    <TextView
        android:id="@+id/bar_title"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:ellipsize="end"
        android:maxLines="1"
        android:textAppearance="@android:style/TextAppearance.Material.Notification.Title" />

    <Chronometer
        android:id="@+id/bar_chrono"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:textSize="28sp"
        android:textStyle="bold"
        android:textAppearance="@android:style/TextAppearance.Material.Notification.Title" />

    <TextView
        android:id="@+id/bar_table"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="2dp"
        android:maxLines="3"
        android:textAppearance="@android:style/TextAppearance.Material.Notification.Line2" />
</LinearLayout>
''')

m=open(MAN,encoding="utf-8").read()
if "BarReceiver" not in m:
    rcv='''    <receiver android:name=".BarReceiver" android:exported="true">
        <intent-filter>
            <action android:name="android.intent.action.BOOT_COMPLETED" />
            <action android:name="android.intent.action.MY_PACKAGE_REPLACED" />
        </intent-filter>
    </receiver>
    '''
    m=m.replace("</application>",rcv+"</application>",1);open(MAN,"w",encoding="utf-8").write(m)
print("canlı bildirim çubuğu eklendi")
