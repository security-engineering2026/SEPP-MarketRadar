package com.sepp.marketradar

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.*
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : android.app.Activity() {
    private lateinit var urlBox: EditText
    private lateinit var tokenBox: EditText
    private lateinit var status: TextView
    private val prefs by lazy { getSharedPreferences("marketradar", Context.MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(28, 28, 28, 28) }
        val title = TextView(this).apply { text = "MarketRadar Android Companion"; textSize = 22f }
        urlBox = EditText(this).apply { hint = "Gateway URL e.g. http://192.168.1.10:8765"; setText(prefs.getString("url", "")) }
        tokenBox = EditText(this).apply { hint = "Android API token"; setText(prefs.getString("token", "")); inputType = 0x81 }
        val save = Button(this).apply { text = "Save & Refresh"; setOnClickListener { saveAndRefresh() } }
        val approve = Button(this).apply { text = "Approve first pending application"; setOnClickListener { approveFirst() } }
        status = TextView(this).apply { text = "Not connected"; textSize = 16f }
        root.addView(title); root.addView(urlBox); root.addView(tokenBox); root.addView(save); root.addView(approve); root.addView(status)
        setContentView(root)
        schedulePoll()
        if (!urlBox.text.isNullOrBlank() && !tokenBox.text.isNullOrBlank()) refresh()
    }

    private fun saveAndRefresh() {
        prefs.edit().putString("url", urlBox.text.toString().trim().trimEnd('/')).putString("token", tokenBox.text.toString().trim()).apply(); schedulePoll(); refresh()
    }

    private fun schedulePoll() {
        val am = getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val i = Intent(this, PollReceiver::class.java)
        val pi = PendingIntent.getBroadcast(this, 1600, i, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        am.setInexactRepeating(AlarmManager.RTC_WAKEUP, System.currentTimeMillis()+60_000, 15*60_000L, pi)
    }

    private fun refresh() { request("/api/android/v1/dashboard") { text -> runOnUiThread { status.text = text.take(6000) } } }

    private fun approveFirst() {
        request("/api/android/v1/dashboard") { body ->
            val id = Regex("\\\"opportunity_id\\\"\\s*:\\s*(\\d+)").find(body)?.groupValues?.getOrNull(1)
            if (id == null) { runOnUiThread { status.text = "No pending application found" }; return@request }
            post("/api/android/v1/applications/approve", "{\"opportunity_id\":$id}") { approval ->
                val aid = Regex("\\\"approval_id\\\"\\s*:\\s*\\\"([^\"]+)\\\"").find(approval)?.groupValues?.getOrNull(1)
                if (aid == null) { runOnUiThread { status.text = approval }; return@post }
                post("/api/android/v1/applications/execute", "{\"opportunity_id\":$id,\"approval\":{\"approval_id\":\"$aid\"}}") { result -> runOnUiThread { status.text = result.take(6000) } }
            }
        }
    }

    private fun request(path: String, done: (String)->Unit) = thread { try { done(http("GET", path, null)) } catch (e: Exception) { runOnUiThread { status.text = "ERROR: ${e.message}" } } }
    private fun post(path: String, body: String, done: (String)->Unit) = thread { try { done(http("POST", path, body)) } catch (e: Exception) { runOnUiThread { status.text = "ERROR: ${e.message}" } } }

    private fun http(method: String, path: String, body: String?): String {
        val base = prefs.getString("url", "") ?: ""; val token = prefs.getString("token", "") ?: ""
        require(base.isNotBlank() && token.isNotBlank()) { "Gateway URL/token required" }
        val c = URL(base + path).openConnection() as HttpURLConnection
        c.requestMethod = method; c.connectTimeout = 7000; c.readTimeout = 10000; c.setRequestProperty("X-MarketRadar-Token", token); c.setRequestProperty("Content-Type", "application/json")
        if (body != null) { c.doOutput = true; c.outputStream.use { it.write(body.toByteArray()) } }
        val stream = if (c.responseCode < 400) c.inputStream else c.errorStream
        return stream.bufferedReader().use { it.readText() }
    }
}
