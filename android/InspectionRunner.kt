package com.example.minicpm_v_demo

import android.util.JsonReader
import android.util.JsonToken
import java.io.StringReader
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

data class InspectionDraft(
    val objectName: String?,
    val visibleIssue: String?,
    val needsRetake: Boolean,
    val missingFields: List<String>
)

object InspectionContract {
    const val PROMPT = "你是现场照片观察助手。请用中文描述这张照片中的一个主要可见对象及其状态，只输出一个JSON对象。禁止输出数组、对象列表、多个JSON对象、Markdown或解释。必须完整包含且只包含四个字段：object、visible_issue、needs_retake、missing_fields。object为对象名称字符串或null；visible_issue为仅由照片支持的状态描述字符串或null，正常场景也填写可见状态，不猜测动作意图、故障原因或维修方法。needs_retake必须是true或false，照片暗、模糊、遮挡或无法判断时为true。missing_fields必须是JSON数组，不能是null：object为null时包含\"object\"，visible_issue为null时包含\"visible_issue\"，两者都有描述时为[]。两个描述均无法确认时输出{\"object\":null,\"visible_issue\":null,\"needs_retake\":true,\"missing_fields\":[\"object\",\"visible_issue\"]}；可以确认时请依据照片填写，不能直接照抄空值示例。不要生成位置、时间或处理状态。"

    fun parse(raw: String): InspectionDraft {
        JsonReader(StringReader(raw)).use { reader ->
            reader.isLenient = false
            reader.beginObject()
            val seen = mutableSetOf<String>()
            var objectName: String? = null
            var issue: String? = null
            var retake = false
            val missing = mutableListOf<String>()
            fun nullableString(): String? {
                if (reader.peek() == JsonToken.NULL) { reader.nextNull(); return null }
                require(reader.peek() == JsonToken.STRING) { "Expected string or null" }
                return reader.nextString().also { require(it.isNotBlank() && it.length <= 300) }
            }
            while (reader.hasNext()) {
                val key = reader.nextName()
                require(seen.add(key)) { "Duplicate field" }
                when (key) {
                    "object" -> objectName = nullableString()
                    "visible_issue" -> issue = nullableString()
                    "needs_retake" -> { require(reader.peek() == JsonToken.BOOLEAN); retake = reader.nextBoolean() }
                    "missing_fields" -> {
                        reader.beginArray()
                        while (reader.hasNext()) {
                            require(reader.peek() == JsonToken.STRING)
                            missing.add(reader.nextString())
                        }
                        reader.endArray()
                    }
                    else -> error("Unexpected field")
                }
            }
            reader.endObject()
            require(reader.peek() == JsonToken.END_DOCUMENT) { "Trailing content" }
            require(seen == setOf("object", "visible_issue", "needs_retake", "missing_fields"))
            val expectedMissing = mutableSetOf<String>()
            if (objectName == null) expectedMissing.add("object")
            if (issue == null) expectedMissing.add("visible_issue")
            require(missing.toSet() == expectedMissing && missing.distinct().size == missing.size)
            return InspectionDraft(objectName, issue, retake, missing)
        }
    }
}

/** Use one shared runner; engine has already loaded the V4.6 LLM and matching mmproj. */
class InspectionRunner(private val engine: LlamaEngine) {
    companion object { private val mutex = Mutex() }
    suspend fun generate(jpegBytes: ByteArray, onToken: (String) -> Unit = {}): InspectionDraft = mutex.withLock {
        require(engine.isVisionSupported) { "Matching vision component must be loaded" }
        engine.setEnableThinking(false)
        // Never carry observations from the previous location into this inspection.
        engine.clearContext()
        engine.setSystemPrompt(InspectionContract.PROMPT)
        engine.prefillImage(jpegBytes)
        val result = StringBuilder()
        engine.sendUserPrompt(InspectionContract.PROMPT, predictLength = 384).collect {
            result.append(it)
            onToken(it)
        }
        InspectionContract.parse(result.toString())
    }
}
