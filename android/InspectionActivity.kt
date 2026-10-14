package com.example.minicpm_v_demo

import android.app.AlertDialog
import android.content.Intent
import androidx.activity.OnBackPressedCallback
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.os.SystemClock
import android.view.View
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.widget.addTextChangedListener
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID
import kotlin.math.roundToInt

/** Reproducible chapter UI: private photos, explicit confirmation and explicit sync. */
class InspectionActivity : AppCompatActivity() {
    private lateinit var modelContext: InspectionModelContext
    private lateinit var engine: LlamaEngine
    private lateinit var runner: InspectionRunner
    private lateinit var store: InspectionRecordStore
    private lateinit var body: LinearLayout
    private lateinit var status: TextView
    private val prefs by lazy { getSharedPreferences("inspection_ui", MODE_PRIVATE) }
    private val controls = mutableListOf<View>()
    private var draft: JSONObject? = null
    private var page = 0
    private var busy = false
    private var binding = false
    private var modelReady = false
    private var reviewCheck: CheckBox? = null
    private var activeRaw = ""
    private var message = "先加载模型，再拍摄或选择图片。"

    private val takePhoto = registerForActivityResult(ActivityResultContracts.TakePicture()) { ok ->
        val current = draft
        if (current != null && original(current).length() > 0) {
            // Preserve an actual camera file even if the camera result was interrupted.
            current.put("captured_at", nowIso()).put("camera_pending", false)
            persist()
            prepareImage()
        } else {
            message = if (ok) "未取得相机图片，请重新拍摄。" else "拍摄已取消，原有记录仍在记录列表。"
            render()
        }
    }
    private val choosePhoto = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) importPhoto(uri)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        store = InspectionRecordStore(applicationContext)
        modelContext = InspectionModelContext(applicationContext)
        engine = LlamaEngine.getInstance(modelContext)
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() { returnToHome() }
        })
        runner = InspectionRunner(engine)
        recover()
        page = savedInstanceState?.getInt("page") ?: 0
        render()
    }

    private fun nowIso(): String = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US).format(Date())
    private fun dp(n: Int): Int = (n * resources.displayMetrics.density).roundToInt()
    private fun directory(item: JSONObject): File = File(filesDir, "inspection/${item.getString("id")}")
    private fun original(item: JSONObject): File = File(directory(item), "original")
    private fun prepared(item: JSONObject): File = File(directory(item), "inference.jpg")

    private fun newDraft(source: String): JSONObject {
        val item = JSONObject().put("id", UUID.randomUUID().toString()).put("source", source)
            .put("created_at", nowIso()).put("captured_at", "")
            .put("location", "").put("object", "").put("visible_issue", "")
            .put("confirmed", false).put("raw", "")
        directory(item).mkdirs()
        draft = item
        prefs.edit().putString("active_id", item.getString("id")).apply()
        persist()
        return item
    }

    private fun persist() {
        val item = draft ?: return
        val dir = directory(item).apply { mkdirs() }
        val temp = File(dir, "draft.json.tmp")
        temp.writeText(item.toString(2))
        check(temp.renameTo(File(dir, "draft.json"))) { "草稿保存失败" }
    }

    private fun recover() {
        val id = prefs.getString("active_id", null) ?: return
        try {
            UUID.fromString(id)
            draft = JSONObject(File(filesDir, "inspection/$id/draft.json").readText())
            val current = draft!!
            if (store.listRecords().any { it.record.getString("record_id") == id }) {
                current.put("confirmed", true)
            }
            if (current.optBoolean("generation_running")) {
                current.put("generation_running", false)
                message = "上次生成中断，照片和位置已恢复，可重新生成或手工填写。"
            } else message = "已恢复上次照片与草稿。"
            persist()
        } catch (e: Exception) {
            message = "未能恢复草稿：${e.message}。已保存的正式记录仍可在记录列表查看。"
        }
    }

    private fun button(parent: LinearLayout, label: String, action: () -> Unit): Button {
        return Button(this).apply {
            text = label
            isEnabled = !busy
            setOnClickListener { action() }
            parent.addView(this)
            controls.add(this)
        }
    }

    private fun text(parent: LinearLayout, value: String, size: Float = 15f): TextView =
        TextView(this).apply {
            text = value
            textSize = size
            setPadding(0, dp(6), 0, dp(6))
            parent.addView(this)
        }

    private fun field(parent: LinearLayout, label: String, key: String, multiline: Boolean = false): EditText {
        text(parent, label)
        val current = draft ?: error("No draft")
        return EditText(this).apply {
            setText(current.optString(key))
            setSingleLine(!multiline)
            isEnabled = !busy && !current.optBoolean("confirmed")
            parent.addView(this)
            controls.add(this)
            addTextChangedListener {
                if (!binding && !current.optBoolean("confirmed")) {
                    current.put(key, it.toString())
                    // Any edit requires a fresh explicit confirmation.
                    current.put("reviewed", false)
                    reviewCheck?.isChecked = false
                    persist()
                }
            }
        }
    }

    private fun render() {
        if (isDestroyed || isFinishing) return
        binding = true
        controls.clear()
        reviewCheck = null
        val scroll = ScrollView(this)
        body = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(12), dp(16), dp(24))
        }
        scroll.addView(body)
        setContentView(scroll)
        ViewCompat.setOnApplyWindowInsetsListener(scroll) { view, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout())
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        ViewCompat.requestApplyInsets(scroll)
        button(body, "返回 MiniCPM-V") { returnToHome() }
        text(body, "现场巡检助手", 24f)
        button(body, "模型管理与下载") {
            startActivity(Intent(this, ModelManagerActivity::class.java))
        }
        text(body, "照片留在手机。观察由你确认，点击同步才发送记录。")
        val nav = LinearLayout(this)
        body.addView(nav)
        listOf("1 采集", "2 确认", "3 记录").forEachIndexed { index, label ->
            button(nav, label) { page = index; render() }
        }
        status = text(body, message)
        if (page == 2) renderRecords() else renderDraft()
        binding = false
    }

    private fun renderDraft() {
        button(body, if (modelReady) "模型已加载（4.6）" else "加载本地 4.6 模型") { loadModel() }
        button(body, "拍摄新照片") {
            try {
                val current = newDraft("camera").put("camera_pending", true)
                original(current).createNewFile()
                persist()
                val uri = FileProvider.getUriForFile(this, "$packageName.inspection.files", original(current))
                takePhoto.launch(uri)
            } catch (e: Exception) { fail("无法打开相机", e) }
        }
        button(body, "从相册选择新照片") { choosePhoto.launch("image/*") }
        button(body, "恢复已保存的照片草稿") {
            val candidates = File(filesDir, "inspection").listFiles().orEmpty().filter { it.isDirectory }
                .mapNotNull { dir -> runCatching { JSONObject(File(dir, "draft.json").readText()) }.getOrNull() }
                .filter { !it.optBoolean("confirmed") && original(it).length() > 0 }
                .sortedByDescending { it.optString("created_at") }
            if (candidates.isEmpty()) { message = "没有待确认的照片草稿。"; status.text = message }
            else AlertDialog.Builder(this).setTitle("选择照片草稿")
                .setItems(candidates.map { it.optString("created_at") + " · " + it.optString("location").ifBlank { "位置待填" } }.toTypedArray()) { _, index ->
                    draft = candidates[index]
                    prefs.edit().putString("active_id", draft!!.getString("id")).apply()
                    message = "已恢复照片草稿。"
                    page = 0
                    render()
                }.setNegativeButton("取消", null).show()
        }
        val current = draft ?: return
        text(body, "来源：${if (current.optString("source") == "camera") "现场拍摄" else "相册导入，需核对原拍摄时间"}")
        val jpeg = prepared(current)
        if (jpeg.isFile) {
            val preview = ImageView(this).apply {
                adjustViewBounds = true
                contentDescription = "待核对的巡检照片"
                setImageBitmap(BitmapFactory.decodeFile(jpeg.absolutePath))
            }
            body.addView(preview, LinearLayout.LayoutParams(-1, dp(260)))
        } else if (original(current).length() > 0) {
            button(body, "恢复照片预览") { prepareImage() }
        }
        field(body, "位置（自行输入，模型不猜测）", "location")
        field(body, "实际拍摄时间，含时区（例如 2026-10-14T21:00:00+08:00）", "captured_at")
        if (current.optBoolean("confirmed")) {
            text(body, "此记录已确认并冻结。更正请建立新记录；原照片和观察保留。")
        } else {
            button(body, "根据照片生成观察草稿") { generate() }
        }
        if (page == 1 || current.has("generation_attempted")) {
            if (current.optBoolean("needs_retake")) text(body, "模型建议重拍。请核对图片，可重拍或手工补录。")
            field(body, "对象", "object")
            field(body, "照片中可见的现象（不推断故障原因）", "visible_issue", true)
            field(body, "确认人", "confirmed_by")
            if (!current.optBoolean("confirmed")) {
                val reviewed = CheckBox(this).apply {
                    text = "我已核对照片、位置、拍摄时间与观察"
                    isEnabled = !busy
                    isChecked = current.optBoolean("reviewed")
                }
                reviewCheck = reviewed
                body.addView(reviewed)
                controls.add(reviewed)
                reviewed.setOnCheckedChangeListener { _, checked -> current.put("reviewed", checked); persist() }
                button(body, "确认并仅保存在手机") { confirm() }
            }
        }
        if (current.optString("raw").isNotBlank()) {
            button(body, "查看模型原始回答与耗时") {
                AlertDialog.Builder(this).setTitle("生成详情")
                    .setMessage("首字：${current.optLong("first_token_ms", -1)} ms\n完整草稿：${current.optLong("elapsed_ms", -1)} ms\n\n${current.optString("raw")}")
                    .setPositiveButton("关闭", null).show()
            }
        }
    }

    private fun setBusy(value: Boolean, note: String) {
        busy = value
        message = note
        controls.forEach { it.isEnabled = !value }
        if (::status.isInitialized) status.text = note
    }

    private fun fail(prefix: String, e: Exception) {
        message = "$prefix：${e.message ?: e.javaClass.simpleName}"
        render()
    }

    private fun importPhoto(uri: Uri) {
        setBusy(true, "正在保存原图并准备预览…")
        lifecycleScope.launch {
            try {
                val current = newDraft("album")
                val metadata = withContext(Dispatchers.IO) {
                    contentResolver.openInputStream(uri).use { input ->
                        requireNotNull(input) { "无法读取所选图片" }
                        original(current).outputStream().use { output -> input.copyTo(output) }
                    }
                    preprocess(current)
                }
                mergeImageMetadata(current, metadata)
                message = "原图已保存在手机，请填写位置并核对原拍摄时间。"
            } catch (e: CancellationException) { throw e }
            catch (e: Exception) { message = "图片预处理失败，原图已保留：${e.message}" }
            finally { busy = false; render() }
        }
    }

    private fun prepareImage() {
        val current = draft ?: return
        setBusy(true, "正在校正照片方向并准备预览…")
        lifecycleScope.launch {
            try {
                val metadata = withContext(Dispatchers.IO) { preprocess(current) }
                mergeImageMetadata(current, metadata)
                message = "照片已保存，请填写位置并核对拍摄时间。"
            } catch (e: CancellationException) { throw e }
            catch (e: Exception) { message = "图片预处理失败，原图已保留：${e.message}" }
            finally { busy = false; render() }
        }
    }

    private fun preprocess(current: JSONObject): JSONObject =
        InspectionImageProcessor(applicationContext).preprocess(current)

    private fun mergeImageMetadata(current: JSONObject, metadata: JSONObject) {
        metadata.keys().asSequence().forEach { current.put(it, metadata.get(it)) }
        persist()
    }

    private fun loadModel() {
        if (busy) return
        setBusy(true, "正在加载语言模型与视觉组件…")
        lifecycleScope.launch {
            val started = SystemClock.elapsedRealtime()
            try {
                LlamaEngine.setSelectedModel(modelContext, "minicpm-v-4_6-instruct")
                require(File(LlamaEngine.modelPath(modelContext)).isFile &&
                    LlamaEngine.mmprojPath(modelContext)?.let { File(it).isFile } == true) {
                    "缺少 4.6 模型文件，请点击“模型管理与下载”，选择 MiniCPM-V 4.6 并下载语言模型与视觉组件，完成后返回此页加载。"
                }
                withTimeout(120000) { engine.state.first { it is LlamaState.Initialized || it is LlamaState.ModelReady || it is LlamaState.Error } }
                val state = engine.state.value
                if (state is LlamaState.Error) withContext(Dispatchers.IO) { engine.cleanUp() }
                // Always load the known package, even if another Demo screen previously loaded a different model.
                if (state is LlamaState.ModelReady && !modelReady) engine.unloadModel()
                LlamaEngine.setImageMaxSliceNumsPref(modelContext, 1)
                if (engine.state.value is LlamaState.Initialized) engine.loadModel(LlamaEngine.modelPath(modelContext), LlamaEngine.mmprojPath(modelContext))
                require(engine.isVisionSupported) { "视觉组件加载失败，无法生成图片观察" }
                engine.setEnableThinking(false)
                engine.setImageMaxSliceNums(1)
                modelReady = true
                val elapsed = SystemClock.elapsedRealtime() - started
                File(filesDir, "inspection").mkdirs()
                File(filesDir, "inspection/model-load.json").writeText(JSONObject().put("elapsed_ms", elapsed)
                    .put("recorded_at", nowIso()).put("vision_supported", true).put("slice_cap", 1).toString(2))
                message = "4.6 语言模型与视觉组件已加载，可离线生成。加载用时 ${elapsed} ms。"
            } catch (e: CancellationException) { throw e }
            catch (e: Exception) { modelReady = false; message = "模型加载失败：${e.message}。照片仍可保存和手工填写。" }
            finally { busy = false; render() }
        }
    }

    private fun generate() {
        val current = draft ?: return
        if (busy || current.optBoolean("confirmed")) return
        if (!modelReady || !engine.isVisionSupported || LlamaEngine.getSelectedModel(modelContext).id != "minicpm-v-4_6-instruct") { message = "请先加载本地语言模型与视觉组件。"; render(); return }
        if (!prepared(current).isFile) { message = "请先拍照或恢复照片预览。"; render(); return }
        setBusy(true, "正在生成观察，请核对完成后的图片与字段…")
        lifecycleScope.launch {
            val started = SystemClock.elapsedRealtime()
            var firstToken: Long? = null
            activeRaw = ""
            current.put("generation_running", true).put("generation_attempted", true).put("schema_valid", false).put("reviewed", false)
            current.remove("generation_error")
            persist()
            try {
                val input = withContext(Dispatchers.IO) { preprocess(current) to prepared(current).readBytes() }
                mergeImageMetadata(current, input.first)
                val output = runner.generate(input.second) { piece ->
                    if (firstToken == null) firstToken = SystemClock.elapsedRealtime() - started
                    activeRaw += piece
                }
                current.put("object", output.objectName ?: "").put("visible_issue", output.visibleIssue ?: "")
                    .put("needs_retake", output.needsRetake).put("schema_valid", true)
                    .put("model_object", output.objectName ?: JSONObject.NULL)
                    .put("model_visible_issue", output.visibleIssue ?: JSONObject.NULL)
                message = "草稿已生成，请逐项核对并确认。"
                page = 1
            } catch (e: CancellationException) {
                current.put("generation_error", "生成中断，可重试或手工填写")
                engine.cancelGeneration()
                throw e
            } catch (e: Exception) {
                current.put("schema_valid", false).put("generation_error", e.message)
                message = "生成未通过：${e.message}。原始回答与照片保留，可重拍、重试或手工填写。"
                page = 1
            } finally {
                current.put("raw", activeRaw).put("generation_running", false)
                    .put("first_token_ms", firstToken ?: -1L).put("elapsed_ms", SystemClock.elapsedRealtime() - started)
                persist()
                busy = false
                render()
            }
        }
    }

    private fun confirm() {
        val current = draft ?: return
        if (!current.optBoolean("reviewed")) { message = "请勾选核对确认后再保存。"; status.text = message; return }
        try {
            require(original(current).isFile && current.optString("original_sha256").length == 64) { "缺少原图或图片校验值" }
            require(InspectionRecordStore.isZonedTimestamp(current.optString("captured_at"))) { "请填写真实拍摄时间并包含时区" }
            val record = JSONObject().put("record_id", current.getString("id"))
                .put("captured_at", current.getString("captured_at"))
                .put("location", current.optString("location").trim())
                .put("object", current.optString("object").trim())
                .put("visible_issue", current.optString("visible_issue").trim())
                .put("image_sha256", current.getString("original_sha256"))
                .put("model_id", if (current.optBoolean("generation_attempted")) "OpenBMB/MiniCPM-V-4.6-gguf" else "manual-entry-no-inference")
                .put("model_revision", if (current.optBoolean("generation_attempted")) "llm-sha256:6b0c74962c44bc6bf4b655b9b02c13eda9d5a0491543ae976d1ac18e4b7892e2;mmproj-sha256:ca931d861d0801d9003e50697cd764721a334107c0e0415a51168ee1938462de;app:d1aac05" else "manual")
                .put("confirmed_by", current.optString("confirmed_by").trim()).put("confirmed_at", nowIso())
                .put("human_confirmed", true)
            store.saveConfirmed(record)
            current.put("confirmed", true).put("confirmed_record", record)
            persist()
            page = 2
            message = "已确认并仅保存在手机；点击同步才发送结构化记录。"
            render()
        } catch (e: Exception) { message = "不能确认：${e.message}。请补齐对象、现象、位置、时间与确认人。"; status.text = message }
    }

    private fun renderRecords() {
        text(body, "台账地址（本地教学默认回环地址）")
        val endpoint = EditText(this).apply {
            setSingleLine(true)
            setText(prefs.getString("ledger_url", "http://127.0.0.1:8787"))
            isEnabled = !busy
        }
        body.addView(endpoint)
        controls.add(endpoint)
        button(body, "同步已确认的待发送记录") {
            val url = endpoint.text.toString().trim()
            prefs.edit().putString("ledger_url", url).apply()
            setBusy(true, "正在同步已确认记录…")
            lifecycleScope.launch {
                try {
                    val results = withContext(Dispatchers.IO) { store.syncPending(url) }
                    message = "本次同步成功 ${results.count { it.second }} 条，失败 ${results.count { !it.second }} 条。"
                } catch (e: Exception) { message = "同步失败：${e.message}" }
                finally { busy = false; render() }
            }
        }
        val rows = store.listRecords()
        if (rows.isEmpty()) text(body, "还没有已确认记录。照片草稿保存在采集页面。")
        for (row in rows) {
            val record = row.record
            text(body, "${record.getString("location")} · ${record.getString("object")}", 18f)
            text(body, record.getString("visible_issue"))
            val label = when { row.synced -> "同步成功"; row.lastError != null -> "同步失败，保留待发送"; else -> "仅保存在手机" }
            text(body, "$label · 处理状态：${row.remoteStatus ?: "尚未同步"}\n${record.getString("record_id")}")
            if (row.lastError != null) text(body, row.lastError)
            if (row.synced) button(body, "刷新此记录处理状态") {
                val url = endpoint.text.toString().trim()
                setBusy(true, "正在刷新处理状态…")
                lifecycleScope.launch {
                    try {
                        withContext(Dispatchers.IO) { store.refreshStatus(url, record.getString("record_id")) }
                        message = "处理状态已刷新。"
                    } catch (e: Exception) { message = "刷新失败：${e.message}" }
                    finally { busy = false; render() }
                }
            }
        }
    }

    private fun returnToHome() {
        if (busy) {
            message = "请等待当前操作完成后返回，照片草稿会保留。"
            status.text = message
            return
        }
        persist()
        setBusy(true, "正在保存草稿并返回 MiniCPM-V…")
        lifecycleScope.launch {
            try {
                engine.unloadModel()
                modelReady = false
                finish()
            } catch (e: Exception) {
                busy = false
                fail("返回失败，可重试", e)
            }
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putInt("page", page)
        persist()
        super.onSaveInstanceState(outState)
    }
}
