package com.example.minicpm_v_demo

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID
import java.text.SimpleDateFormat
import java.text.ParsePosition
import java.util.Locale

data class StoredInspectionRecord(
    val record: JSONObject, val synced: Boolean, val lastError: String?,
    val remoteStatus: String?, val remoteVersion: Int?
)

/** App-private durable outbox. Call syncPending only after the user taps Sync. */
class InspectionRecordStore(context: Context) : SQLiteOpenHelper(context, "inspection.db", null, 2) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE outbox(record_id TEXT PRIMARY KEY, payload TEXT NOT NULL, synced INTEGER NOT NULL DEFAULT 0, remote_status TEXT, remote_version INTEGER, last_error TEXT)")
    }
    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        require(oldVersion == 1 && newVersion == 2) { "Unsupported schema migration" }
        db.execSQL("ALTER TABLE outbox ADD COLUMN last_error TEXT")
    }

    @Synchronized
    fun saveConfirmed(record: JSONObject) {
        val fields = setOf("record_id", "captured_at", "location", "object", "visible_issue", "image_sha256", "model_id", "model_revision", "confirmed_by", "confirmed_at", "human_confirmed")
        require(record.keys().asSequence().toSet() == fields)
        require(record.opt("human_confirmed") == true)
        UUID.fromString(record.getString("record_id"))
        val labels = mapOf("location" to "位置", "object" to "对象", "visible_issue" to "可见现象",
            "captured_at" to "拍摄时间", "confirmed_by" to "确认人")
        for (field in fields - "human_confirmed") {
            require(record.opt(field) is String && record.getString(field).isNotBlank() && record.getString(field).length <= 500) {
                "${labels[field] ?: field}未填写、格式不正确或超过500字符"
            }
        }
        require(record.getString("image_sha256").matches(Regex("[0-9a-f]{64}")))
        require(isZonedTimestamp(record.getString("captured_at"))) { "Invalid capture time or missing timezone" }
        require(isZonedTimestamp(record.getString("confirmed_at"))) { "Invalid confirmation time or missing timezone" }
        val db = writableDatabase
        db.beginTransaction()
        try {
            db.rawQuery("SELECT payload FROM outbox WHERE record_id=?", arrayOf(record.getString("record_id"))).use { cursor ->
                if (cursor.moveToFirst()) {
                    require(sameRecord(JSONObject(cursor.getString(0)), record)) { "Confirmed records are immutable" }
                } else {
                    db.execSQL("INSERT INTO outbox(record_id,payload) VALUES(?,?)", arrayOf(record.getString("record_id"), record.toString()))
                }
            }
            db.setTransactionSuccessful()
        } finally { db.endTransaction() }
    }

    companion object {
        fun isZonedTimestamp(value: String): Boolean {
            if (!value.matches(Regex("""\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})"""))) return false
            val normalized = value.replace(Regex("""\.(\d{1,6})(?=Z|[+-])""")) {
                "." + it.groupValues[1].take(3).padEnd(3, '0')
            }
            val pattern = if (normalized.contains('.')) "yyyy-MM-dd'T'HH:mm:ss.SSSXXX" else "yyyy-MM-dd'T'HH:mm:ssXXX"
            val format = SimpleDateFormat(pattern, Locale.US).apply { isLenient = false }
            val position = ParsePosition(0)
            return format.parse(normalized, position) != null && position.index == normalized.length
        }
    }

    fun listRecords(): List<StoredInspectionRecord> {
        val rows = mutableListOf<StoredInspectionRecord>()
        readableDatabase.rawQuery("SELECT payload,synced,last_error,remote_status,remote_version FROM outbox ORDER BY rowid DESC", null).use { c ->
            while (c.moveToNext()) rows.add(StoredInspectionRecord(
                JSONObject(c.getString(0)), c.getInt(1) == 1,
                if (c.isNull(2)) null else c.getString(2),
                if (c.isNull(3)) null else c.getString(3),
                if (c.isNull(4)) null else c.getInt(4)
            ))
        }
        return rows
    }

    private fun sameRecord(a: JSONObject, b: JSONObject): Boolean =
        a.keys().asSequence().toSet() == b.keys().asSequence().toSet() &&
        a.keys().asSequence().all { a.get(it) == b.get(it) }

    fun pending(): List<JSONObject> {
        val result = mutableListOf<JSONObject>()
        readableDatabase.rawQuery("SELECT payload FROM outbox WHERE synced=0 ORDER BY record_id", null).use { c ->
            while (c.moveToNext()) result.add(JSONObject(c.getString(0)))
        }
        return result
    }

    /** Run off the UI thread; a failed or conflicting POST stays in the queue. */
    fun syncPending(baseUrl: String, bearerToken: String? = null): List<Pair<String, Boolean>> =
        pending().map { record ->
            val id = record.getString("record_id")
            val bytes = record.toString().toByteArray(Charsets.UTF_8)
            val connection = URL(baseUrl.trimEnd('/') + "/records").openConnection() as HttpURLConnection
            try {
                connection.requestMethod = "POST"
                connection.connectTimeout = 10000
                connection.readTimeout = 10000
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                if (bearerToken != null) connection.setRequestProperty("Authorization", "Bearer $bearerToken")
                connection.setFixedLengthStreamingMode(bytes.size)
                connection.outputStream.use { it.write(bytes) }
                require(connection.responseCode == 200 || connection.responseCode == 201)
                val ack = connection.inputStream.bufferedReader().use { JSONObject(it.readText()) }
                require(sameRecord(ack.getJSONObject("record"), record)) { "Mismatched server acknowledgment" }
                writableDatabase.execSQL("UPDATE outbox SET synced=1,remote_status=?,remote_version=?,last_error=NULL WHERE record_id=?",
                    arrayOf(ack.getString("status"), ack.getInt("version"), id))
                id to true
            } catch (e: Exception) {
                writableDatabase.execSQL("UPDATE outbox SET last_error=? WHERE record_id=?",
                    arrayOf("${e.javaClass.simpleName}: ${e.message}".take(300), id))
                id to false
            }
            finally { connection.disconnect() }
        }

    /** Explicit refresh for a synced record; never overwrites local observation fields. */
    fun refreshStatus(baseUrl: String, recordId: String, bearerToken: String? = null): JSONObject {
        UUID.fromString(recordId)
        val connection = URL(baseUrl.trimEnd('/') + "/records/" + recordId).openConnection() as HttpURLConnection
        try {
            connection.connectTimeout = 10000
            connection.readTimeout = 10000
            if (bearerToken != null) connection.setRequestProperty("Authorization", "Bearer $bearerToken")
            require(connection.responseCode == 200)
            val remote = connection.inputStream.bufferedReader().use { JSONObject(it.readText()) }
            require(remote.getJSONObject("record").getString("record_id") == recordId)
            writableDatabase.execSQL("UPDATE outbox SET remote_status=?,remote_version=? WHERE record_id=?",
                arrayOf(remote.getString("status"), remote.getInt("version"), recordId))
            return remote
        } finally { connection.disconnect() }
    }
}
