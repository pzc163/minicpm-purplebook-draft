package com.example.minicpm_v_demo

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
import android.os.SystemClock
import java.io.File

/** Opt-in real-model regression; never creates or confirms a business record. */
@RunWith(AndroidJUnit4::class)
class InspectionVisionInstrumentedTest {
    @Test fun systemPromptAndTwoImageGenerationsStayAlive() = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val relative = requireNotNull(InstrumentationRegistry.getArguments().getString("image_relpath")) {
            "Supply an authorized inspection/<draft-id>/inference.jpg via image_relpath"
        }
        val image = File(context.filesDir, relative).canonicalFile
        require(image.path.startsWith(File(context.filesDir, "inspection").canonicalPath + File.separator))
        require(image.isFile && image.name == "inference.jpg")
        LlamaEngine.setSelectedModel(context, "minicpm-v-4_6-instruct")
        LlamaEngine.setImageMaxSliceNumsPref(context, 1)
        val engine = LlamaEngine.getInstance(context)
        val results = JSONArray()
        val evidence = File(context.filesDir, "inspection/vision-regression.json")
        withTimeout(180000) {
            engine.state.first { it is LlamaState.Initialized || it is LlamaState.ModelReady || it is LlamaState.Error }
            if (engine.state.value is LlamaState.ModelReady) engine.unloadModel()
            engine.loadModel(LlamaEngine.modelPath(context), LlamaEngine.mmprojPath(context))
            engine.setImageMaxSliceNums(1)
            try {
                repeat(2) { attempt ->
                    val started = SystemClock.elapsedRealtime()
                    var firstToken: Long? = null
                    val raw = StringBuilder()
                    val result = JSONObject().put("attempt", attempt + 1).put("image_relpath", relative)
                    try {
                        val draft = InspectionRunner(engine).generate(image.readBytes()) { piece ->
                            if (firstToken == null) firstToken = SystemClock.elapsedRealtime() - started
                            raw.append(piece)
                        }
                        result.put("schema_valid", true).put("object", draft.objectName ?: JSONObject.NULL)
                            .put("visible_issue", draft.visibleIssue ?: JSONObject.NULL)
                    } catch (e: Exception) {
                        result.put("schema_valid", false).put("error", e.message ?: e.javaClass.simpleName)
                    }
                    result.put("raw", raw.toString()).put("first_token_ms", firstToken ?: -1L)
                        .put("elapsed_ms", SystemClock.elapsedRealtime() - started)
                    results.put(result)
                    evidence.writeText(results.toString(2))
                    Assert.assertTrue("No tokens: $result", raw.isNotBlank())
                    Assert.assertTrue("Engine did not recover: $result", engine.state.value is LlamaState.ModelReady)
                }
            } finally {
                if (engine.state.value is LlamaState.ModelReady) engine.unloadModel()
            }
        }
    }
}
