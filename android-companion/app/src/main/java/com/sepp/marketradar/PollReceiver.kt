package com.sepp.marketradar

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class PollReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        val prefs=context.getSharedPreferences("marketradar", Context.MODE_PRIVATE); val base=prefs.getString("url","") ?: ""; val token=prefs.getString("token","") ?: ""
        if (base.isBlank() || token.isBlank()) return
        val pending=goAsync()
        thread {
            try {
                val c=URL(base.trimEnd('/')+"/api/android/v1/notifications").openConnection() as HttpURLConnection
                c.requestMethod="GET"; c.connectTimeout=7000; c.readTimeout=10000; c.setRequestProperty("X-MarketRadar-Token",token)
                val body=(if(c.responseCode<400)c.inputStream else c.errorStream).bufferedReader().use{it.readText()}
                val count=Regex("\\\"notifications\\\"").findAll(body).count()
                if(count>0) notify(context,"MarketRadar", "$count notification item(s) require attention")
            } catch (_: Exception) {} finally { pending.finish() }
        }
    }
    private fun notify(context: Context,title:String,body:String) {
        val nm=context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(NotificationChannel("marketradar","MarketRadar",NotificationManager.IMPORTANCE_HIGH))
        val pi=PendingIntent.getActivity(context,1601,Intent(context,MainActivity::class.java),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val n=android.app.Notification.Builder(context,"marketradar").setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle(title).setContentText(body).setAutoCancel(true).setContentIntent(pi).build(); nm.notify(1601,n)
    }
}
