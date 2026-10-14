package com.example.minicpm_v_demo

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import kotlin.math.max
import kotlin.math.roundToInt

/** The same private-file preprocessor used by the inspection UI and device tests. */
class InspectionImageProcessor(private val context: Context) {
    private fun directory(item: JSONObject): File = File(context.filesDir, "inspection/${item.getString("id")}")

    fun preprocess(current: JSONObject): JSONObject {
        val source = File(directory(current), "original")
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(source.absolutePath, bounds)
        require(bounds.outWidth > 0 && bounds.outHeight > 0) { "不是可解码图片" }
        val options = BitmapFactory.Options()
        while (max(bounds.outWidth, bounds.outHeight) / options.inSampleSize.coerceAtLeast(1) > 2560) {
            options.inSampleSize = options.inSampleSize.coerceAtLeast(1) * 2
        }
        val bitmap = requireNotNull(BitmapFactory.decodeFile(source.absolutePath, options))
        val orientation = try {
            ExifInterface(source.absolutePath).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
        } catch (_: Exception) { ExifInterface.ORIENTATION_NORMAL }
        val matrix = Matrix().apply {
            when (orientation) {
                ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> setScale(-1f, 1f)
                ExifInterface.ORIENTATION_ROTATE_180 -> setRotate(180f)
                ExifInterface.ORIENTATION_FLIP_VERTICAL -> setScale(1f, -1f)
                ExifInterface.ORIENTATION_TRANSPOSE -> { setRotate(90f); postScale(-1f, 1f) }
                ExifInterface.ORIENTATION_ROTATE_90 -> setRotate(90f)
                ExifInterface.ORIENTATION_TRANSVERSE -> { setRotate(-90f); postScale(-1f, 1f) }
                ExifInterface.ORIENTATION_ROTATE_270 -> setRotate(270f)
            }
        }
        val oriented = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
        val scale = (1280f / max(oriented.width, oriented.height)).coerceAtMost(1f)
        val scaled = Bitmap.createScaledBitmap(oriented, (oriented.width * scale).roundToInt().coerceAtLeast(1),
            (oriented.height * scale).roundToInt().coerceAtLeast(1), true)
        try {
            File(directory(current), "inference.jpg").outputStream().use { check(scaled.compress(Bitmap.CompressFormat.JPEG, 90, it)) }
            return JSONObject().put("original_sha256", sha256(source)).put("inference_sha256", sha256(File(directory(current), "inference.jpg")))
                .put("original_width", bounds.outWidth).put("original_height", bounds.outHeight)
                .put("inference_width", scaled.width).put("inference_height", scaled.height)
                .put("jpeg_quality", 90).put("exif_orientation", orientation)
        } finally {
            if (scaled !== oriented && scaled !== bitmap) scaled.recycle()
            if (oriented !== bitmap) oriented.recycle()
            bitmap.recycle()
        }
    }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(1024 * 1024)
            while (true) { val count = input.read(buffer); if (count < 0) break; digest.update(buffer, 0, count) }
        }
        return digest.digest().joinToString("") { "%02x".format(it.toInt() and 255) }
    }

}
