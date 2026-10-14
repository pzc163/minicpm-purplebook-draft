package com.example.minicpm_v_demo

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.media.ExifInterface
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID

/** Executes the exact preprocessor used by the installed UI, without crossing Activity processes. */
@RunWith(AndroidJUnit4::class)
class InspectionImageInstrumentedTest {
    private fun withProcessor(block: (android.content.Context, File, JSONObject, (JSONObject) -> JSONObject) -> Unit) {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val id = UUID.randomUUID().toString()
        val dir = File(context.filesDir, "inspection/$id").apply { mkdirs() }
        try {
            val processor = InspectionImageProcessor(context)
            block(context, dir, JSONObject().put("id", id), processor::preprocess)
        } finally { dir.deleteRecursively() }
    }

    @Test fun allEightExifDirectionsPreserveQuadrantPositions() {
        withProcessor { activity, dir, item, process ->
            val colors = intArrayOf(Color.RED, Color.GREEN, Color.BLUE, Color.YELLOW)
            val expected = arrayOf(
                intArrayOf(0, 1, 2, 3), intArrayOf(1, 0, 3, 2), intArrayOf(3, 2, 1, 0), intArrayOf(2, 3, 0, 1),
                intArrayOf(0, 2, 1, 3), intArrayOf(2, 0, 3, 1), intArrayOf(3, 1, 2, 0), intArrayOf(1, 3, 0, 2))
            val rows = JSONArray()
            for (orientation in 1..8) {
                val bitmap = Bitmap.createBitmap(240, 160, Bitmap.Config.ARGB_8888)
                for (y in 0 until 160) for (x in 0 until 240) bitmap.setPixel(x, y, colors[(y / 80) * 2 + x / 120])
                File(dir, "original").outputStream().use { bitmap.compress(Bitmap.CompressFormat.JPEG, 96, it) }
                bitmap.recycle()
                ExifInterface(File(dir, "original").path).apply {
                    setAttribute(ExifInterface.TAG_ORIENTATION, orientation.toString()); saveAttributes()
                }
                val metadata = process(item)
                val output = BitmapFactory.decodeFile(File(dir, "inference.jpg").path)
                val positions = listOf(1 to 1, 3 to 1, 1 to 3, 3 to 3)
                val actual = positions.map { (x, y) ->
                    val pixel = output.getPixel(output.width * x / 4, output.height * y / 4)
                    colors.indices.minBy { color ->
                        val candidate = colors[color]
                        kotlin.math.abs(Color.red(pixel) - Color.red(candidate)) +
                            kotlin.math.abs(Color.green(pixel) - Color.green(candidate)) +
                            kotlin.math.abs(Color.blue(pixel) - Color.blue(candidate))
                    }
                }
                Assert.assertArrayEquals("EXIF $orientation", expected[orientation - 1], actual.toIntArray())
                Assert.assertEquals(if (orientation >= 5) 160 else 240, output.width)
                Assert.assertEquals(if (orientation >= 5) 240 else 160, output.height)
                rows.put(metadata.put("actual_quadrants", JSONArray(actual)))
                output.recycle()
            }
            File(activity.filesDir, "inspection/exif-test.json").writeText(rows.toString(2))
        }
    }

    @Test fun largeImageIsSampledAndLimitedTo1280() {
        withProcessor { activity, dir, item, process ->
            val fixture = File(activity.filesDir, "inspection/benchmark/large-fixture.png")
            require(fixture.isFile) { "Supply generated 8192x6144 preprocessing fixture" }
            fixture.copyTo(File(dir, "original"), overwrite = true)
            val metadata = process(item)
            Assert.assertEquals(8192, metadata.getInt("original_width"))
            Assert.assertEquals(6144, metadata.getInt("original_height"))
            Assert.assertEquals(1280, metadata.getInt("inference_width"))
            Assert.assertEquals(960, metadata.getInt("inference_height"))
            Assert.assertNotEquals(metadata.getString("original_sha256"), metadata.getString("inference_sha256"))
            File(activity.filesDir, "inspection/large-image-test.json").writeText(metadata.toString(2))
        }
    }

    @Test fun undecodableImagePreservesOriginalWithoutInference() {
        withProcessor { _, dir, item, process ->
            val source = File(dir, "original").apply { writeText("not an image") }
            try { process(item); Assert.fail("Undecodable input accepted") }
            catch (error: IllegalArgumentException) { Assert.assertTrue(error.message.orEmpty().contains("可解码")) }
            Assert.assertEquals("not an image", source.readText())
            Assert.assertFalse(File(dir, "inference.jpg").exists())
        }
    }
}
