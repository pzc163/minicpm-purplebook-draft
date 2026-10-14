package com.example.minicpm_v_demo

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.security.MessageDigest

/** Read-only acceptance checks for the non-debuggable practice Release APK. */
@RunWith(AndroidJUnit4::class)
class InspectionReleaseAcceptanceTest {
    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(1024 * 1024)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    @Test fun freshInstallHasNoWeightsOrConfirmedRecords() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        assertEquals("com.example.minicpm_v_demo.practice", context.packageName)
        val modelFiles = File(context.filesDir, "models").walkTopDown().filter { it.isFile && it.extension == "gguf" }.toList()
        assertTrue("Fresh installation must not reuse existing model files", modelFiles.isEmpty())
        val store = InspectionRecordStore(context)
        try { assertTrue("Fresh installation must not restore old records", store.listRecords().isEmpty()) }
        finally { store.close() }
        println("PART5_RELEASE_FRESH_INSTALL=no_weights_no_records")
    }

    @Test fun prepareLargePublicTestFixture() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val file = File(context.filesDir, "inspection/benchmark/large-fixture.png")
        file.parentFile!!.mkdirs()
        val bitmap = android.graphics.Bitmap.createBitmap(8192, 6144, android.graphics.Bitmap.Config.ARGB_8888)
        try {
            bitmap.eraseColor(android.graphics.Color.LTGRAY)
            file.outputStream().use { bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, it) }
        } finally { bitmap.recycle() }
        println("PART5_RELEASE_LARGE_FIXTURE=8192x6144")
    }

    @Test fun downloadedModelFilesMatchFixedOfficialHashes() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        assertEquals("com.example.minicpm_v_demo.practice", context.packageName)
        val model = ModelInfo.AVAILABLE_MODELS.single { it.id == "minicpm-v-4_6-instruct" }
        val directory = File(LlamaEngine.modelDirFor(context, model))
        val expected = listOf(
            Triple("MiniCPM-V-4_6-Q4_K_M.gguf", 529101504L,
                "6b0c74962c44bc6bf4b655b9b02c13eda9d5a0491543ae976d1ac18e4b7892e2"),
            Triple("mmproj-model-f16.gguf", 1108746944L,
                "ca931d861d0801d9003e50697cd764721a334107c0e0415a51168ee1938462de")
        )
        val rows = JSONArray()
        for ((name, size, hash) in expected) {
            val file = File(directory, name)
            assertTrue("Missing downloaded model file: $name", file.isFile)
            assertEquals(name, size, file.length())
            val actual = sha256(file)
            assertEquals(name, hash, actual)
            rows.put(JSONObject().put("file", name).put("bytes", size).put("sha256", actual))
        }
        println("PART5_RELEASE_MODEL_HASHES=" + rows.toString())
    }

    @Test fun reportDraftAndConfirmedRecordHashes() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val store = InspectionRecordStore(context)
        try {
            val rows = JSONArray()
            for (row in store.listRecords()) {
                val record = row.record
                rows.put(JSONObject().put("id", record.getString("record_id"))
                    .put("payload_sha256", MessageDigest.getInstance("SHA-256").digest(record.toString().toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) })
                    .put("image_sha256", record.getString("image_sha256"))
                    .put("synced", row.synced).put("remote_status", row.remoteStatus))
            }
            println("PART5_RELEASE_RECORDS=" + rows.toString())
            val drafts = File(context.filesDir, "inspection").listFiles().orEmpty()
            println("PART5_RELEASE_DRAFT_DIRECTORY_COUNT=" + drafts.count { it.isDirectory })
        } finally { store.close() }
    }
}
