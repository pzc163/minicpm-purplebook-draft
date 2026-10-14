package com.example.minicpm_v_demo

import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.Debug
import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

/** Explicit opt-in batch: loads once, never confirms or syncs business records. */
@RunWith(AndroidJUnit4::class)
class InspectionBenchmarkInstrumentedTest {
    @Test fun twentyDistinctImagesWithOneModelLoad(): Unit = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val relative = requireNotNull(InstrumentationRegistry.getArguments().getString("manifest_relpath"))
        val root = File(context.filesDir, "inspection/benchmark").canonicalFile
        val manifestFile = File(context.filesDir, relative).canonicalFile
        require(manifestFile.parentFile == root && manifestFile.name == "manifest.json")
        val manifest = JSONObject(manifestFile.readText())
        val inputs = manifest.getJSONArray("images")
        require(inputs.length() == 20) { "Exactly 20 distinct inputs required" }
        val imageFiles = (0 until inputs.length()).map { index ->
            val item = inputs.getJSONObject(index)
            val image = File(root, item.getString("image")).canonicalFile
            require(image.path.startsWith(root.path + File.separator) && image.isFile)
            val digest = MessageDigest.getInstance("SHA-256").digest(image.readBytes())
                .joinToString("") { "%02x".format(it.toInt() and 255) }
            require(digest == item.getString("sha256")) { "Input hash mismatch" }
            image
        }
        require((0 until inputs.length()).map { inputs.getJSONObject(it).getString("sha256") }.distinct().size == 20)
        fun battery(): JSONObject {
            val intent = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
            return JSONObject().put("level", intent?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1))
                .put("scale", intent?.getIntExtra(BatteryManager.EXTRA_SCALE, -1))
                .put("temperature_tenths_c", intent?.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, -1))
                .put("plugged", intent?.getIntExtra(BatteryManager.EXTRA_PLUGGED, -1))
        }
        val started = SystemClock.elapsedRealtime()
        val rows = JSONArray()
        val samples = ConcurrentLinkedQueue<JSONObject>()
        val sampling = AtomicBoolean(true)
        val stage = AtomicReference("initializing")
        val report = JSONObject().put("status", "running").put("rows", rows)
            .put("source_manifest_sha256", MessageDigest.getInstance("SHA-256").digest(manifestFile.readBytes())
                .joinToString("") { "%02x".format(it.toInt() and 255) })
            .put("target_version_code", context.packageManager.getPackageInfo(context.packageName, 0).longVersionCode)
            .put("timing_scope", "prepared JPEG read + clear context + image prefill + generation; excludes gallery/camera preprocessing and UI rendering")
            .put("config", JSONObject().put("slice_cap", 1).put("thinking", false).put("predict_length", 384)
                .put("cpu_threads", 4).put("context_size", 8192).put("temperature", 0.7)
                .put("sampling", "upstream temperature sampling; not deterministic GPU decoding"))
            .put("battery_before", battery())
        val evidence = File(root, "benchmark.json")
        fun persist() {
            report.put("elapsed_ms", SystemClock.elapsedRealtime() - started)
            report.put("memory_samples", JSONArray(samples.toList()))
            val temporary = File(root, "benchmark.json.tmp")
            temporary.writeText(report.toString(2))
            check(temporary.renameTo(evidence))
        }
        val sampler = Thread {
            while (sampling.get()) {
                try {
                    val memory = Debug.MemoryInfo()
                    Debug.getMemoryInfo(memory)
                    val proc = File("/proc/self/status").readLines()
                    fun kb(key: String) = proc.firstOrNull { it.startsWith("$key:") }
                        ?.substringAfter(':')?.trim()?.substringBefore(' ')?.toLongOrNull()
                    samples.add(JSONObject().put("elapsed_ms", SystemClock.elapsedRealtime() - started)
                        .put("stage", stage.get()).put("pss_kb", memory.totalPss)
                        .put("rss_kb", kb("VmRSS") ?: JSONObject.NULL)
                        .put("rss_high_water_kb", kb("VmHWM") ?: JSONObject.NULL))
                    Thread.sleep(1000)
                } catch (_: InterruptedException) { break }
            }
        }.apply { isDaemon = true; start() }
        LlamaEngine.setSelectedModel(context, "minicpm-v-4_6-instruct")
        LlamaEngine.setImageMaxSliceNumsPref(context, 1)
        val engine = LlamaEngine.getInstance(context)
        persist()
        try {
            withTimeout(900000) {
                engine.state.first { it is LlamaState.Initialized || it is LlamaState.ModelReady || it is LlamaState.Error }
                if (engine.state.value is LlamaState.ModelReady) engine.unloadModel()
                stage.set("load")
                val loadStart = SystemClock.elapsedRealtime()
                engine.loadModel(LlamaEngine.modelPath(context), LlamaEngine.mmprojPath(context))
                engine.setImageMaxSliceNums(1)
                require(engine.isVisionSupported)
                report.put("load_ms", SystemClock.elapsedRealtime() - loadStart)
                imageFiles.forEachIndexed { index, image ->
                    stage.set("image-${index + 1}")
                    report.put("active_image", inputs.getJSONObject(index).getString("id"))
                    persist()
                    val begin = SystemClock.elapsedRealtime()
                    var firstToken: Long? = null
                    val raw = StringBuilder()
                    val row = JSONObject().put("index", index + 1).put("id", inputs.getJSONObject(index).getString("id"))
                        .put("sha256", inputs.getJSONObject(index).getString("sha256"))
                    try {
                        val output = InspectionRunner(engine).generate(image.readBytes()) { piece ->
                            if (firstToken == null && piece.isNotEmpty()) firstToken = SystemClock.elapsedRealtime() - begin
                            raw.append(piece)
                        }
                        row.put("schema_valid", true).put("object", output.objectName ?: JSONObject.NULL)
                            .put("visible_issue", output.visibleIssue ?: JSONObject.NULL)
                            .put("needs_retake", output.needsRetake).put("missing_fields", JSONArray(output.missingFields))
                    } catch (error: Exception) {
                        row.put("schema_valid", false).put("error", error.message ?: error.javaClass.simpleName)
                    }
                    row.put("raw", raw.toString()).put("first_token_ms", firstToken ?: JSONObject.NULL)
                        .put("elapsed_ms", SystemClock.elapsedRealtime() - begin).put("battery", battery())
                        .put("engine_ready", engine.state.value is LlamaState.ModelReady)
                    rows.put(row)
                    persist()
                    Assert.assertTrue("No model tokens for ${row.getString("id")}", raw.isNotBlank())
                    Assert.assertTrue("Engine did not return to ready", engine.state.value is LlamaState.ModelReady)
                }
            }
            report.put("status", "completed").put("battery_after", battery()).remove("active_image")
        } finally {
            sampling.set(false)
            sampler.interrupt()
            sampler.join(2000)
            persist()
            if (engine.state.value is LlamaState.ModelReady) engine.unloadModel()
        }
        Unit
    }
}
