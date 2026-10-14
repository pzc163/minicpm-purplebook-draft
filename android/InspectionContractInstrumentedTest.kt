package com.example.minicpm_v_demo

import android.content.Context
import android.content.ContextWrapper
import android.database.DatabaseErrorHandler
import android.database.sqlite.SQLiteDatabase
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.*
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID

/** Real Android parser/SQLite tests, using an isolated DB directory. No image inference. */
@RunWith(AndroidJUnit4::class)
class InspectionContractInstrumentedTest {
    private lateinit var isolated: File
    private lateinit var context: Context
    private lateinit var store: InspectionRecordStore

    @Before fun setup() {
        val target = InstrumentationRegistry.getInstrumentation().targetContext
        isolated = File(target.cacheDir, "inspection-tests-${UUID.randomUUID()}").apply { mkdirs() }
        context = object : ContextWrapper(target) {
            override fun getDatabasePath(name: String) = File(isolated, name)
            override fun openOrCreateDatabase(name: String, mode: Int, factory: SQLiteDatabase.CursorFactory?): SQLiteDatabase =
                SQLiteDatabase.openOrCreateDatabase(getDatabasePath(name), factory)
            override fun openOrCreateDatabase(name: String, mode: Int, factory: SQLiteDatabase.CursorFactory?, errorHandler: DatabaseErrorHandler?): SQLiteDatabase =
                SQLiteDatabase.openOrCreateDatabase(getDatabasePath(name).path, factory, errorHandler)
        }
        store = InspectionRecordStore(context)
    }

    @After fun cleanup() { store.close(); isolated.deleteRecursively() }

    private fun fixture(): JSONObject = JSONObject()
        .put("record_id", UUID.randomUUID().toString()).put("captured_at", "2026-10-14T20:00:00+08:00")
        .put("location", "测试位置").put("object", "灯罩").put("visible_issue", "可见破损")
        .put("image_sha256", "a".repeat(64)).put("model_id", "instrumentation-fixture-no-inference")
        .put("model_revision", "fixture").put("confirmed_by", "test").put("confirmed_at", "2026-10-14T20:01:00+08:00")
        .put("human_confirmed", true)

    private fun rejects(block: () -> Unit) {
        try { block() } catch (_: Exception) { return }
        Assert.fail("Invalid value was accepted")
    }

    @Test fun strictDraftRejectsDuplicateTrailingAndWrongTypes() {
        val valid = """{"object":"灯罩","visible_issue":"破损","needs_retake":false,"missing_fields":[]}"""
        Assert.assertEquals("灯罩", InspectionContract.parse(valid).objectName)
        rejects { InspectionContract.parse(valid + " trailing") }
        rejects { InspectionContract.parse(valid.replace("false", "\"false\"")) }
        rejects { InspectionContract.parse(valid.replace("\"object\":\"灯罩\"", "\"object\":\"灯罩\",\"object\":\"墙面\"")) }
        rejects { InspectionContract.parse("```json\n$valid\n```") }
    }

    @Test fun unknownFieldsAndMissingListAreRejected() {
        val partial = """{"object":null,"visible_issue":null,"needs_retake":true,"missing_fields":["object","visible_issue"]}"""
        Assert.assertTrue(InspectionContract.parse(partial).needsRetake)
        rejects { InspectionContract.parse(partial.replace("[\"object\",\"visible_issue\"]", "[]")) }
        rejects { InspectionContract.parse(partial.replace("\"needs_retake\"", "\"unexpected\"")) }
    }

    @Test fun confirmationRequiresHumanCompleteFieldsAndTimezone() {
        rejects { store.saveConfirmed(fixture().put("human_confirmed", false)) }
        rejects { store.saveConfirmed(fixture().put("object", "")) }
        rejects { store.saveConfirmed(fixture().put("captured_at", "2026-10-14T20:00:00")) }
        rejects { store.saveConfirmed(fixture().put("location", "x".repeat(501))) }
        Assert.assertTrue(store.pending().isEmpty())
    }

    @Test fun timestampValidationRejectsImpossibleDates() {
        Assert.assertTrue(InspectionRecordStore.isZonedTimestamp("2026-10-14T20:00:00+08:00"))
        Assert.assertTrue(InspectionRecordStore.isZonedTimestamp("2026-10-14T12:00:00.123456Z"))
        Assert.assertFalse(InspectionRecordStore.isZonedTimestamp("2026-02-30T12:00:00Z"))
        Assert.assertFalse(InspectionRecordStore.isZonedTimestamp("2026-10-14T12:00:00"))
    }

    @Test fun immutableRecordsAndQueueSurviveReopen() {
        val record = fixture()
        store.saveConfirmed(record)
        store.saveConfirmed(JSONObject(record.toString()))
        rejects { store.saveConfirmed(JSONObject(record.toString()).put("location", "另一位置")) }
        store.close()
        store = InspectionRecordStore(context)
        Assert.assertEquals(1, store.pending().size)
        Assert.assertEquals(record.getString("record_id"), store.listRecords().single().record.getString("record_id"))
        Assert.assertFalse(store.listRecords().single().synced)
    }

    @Test fun failedSyncPreservesPendingRecordAndVisibleFailure() {
        store.saveConfirmed(fixture())
        Assert.assertFalse(store.syncPending("http://127.0.0.1:1").single().second)
        Assert.assertEquals(1, store.pending().size)
        Assert.assertNotNull(store.listRecords().single().lastError)
    }

    @Test fun versionOneOutboxMigratesWithoutLosingRecord() {
        store.close()
        val record = fixture()
        SQLiteDatabase.openOrCreateDatabase(context.getDatabasePath("inspection.db"), null).use { old ->
            old.execSQL("CREATE TABLE outbox(record_id TEXT PRIMARY KEY,payload TEXT NOT NULL,synced INTEGER NOT NULL DEFAULT 0,remote_status TEXT,remote_version INTEGER)")
            old.execSQL("INSERT INTO outbox(record_id,payload) VALUES(?,?)", arrayOf(record.getString("record_id"), record.toString()))
            old.version = 1
        }
        store = InspectionRecordStore(context)
        Assert.assertEquals(1, store.pending().size)
        Assert.assertNull(store.listRecords().single().lastError)
        Assert.assertEquals(2, store.readableDatabase.version)
    }
}
