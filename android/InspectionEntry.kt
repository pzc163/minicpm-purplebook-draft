package com.example.minicpm_v_demo

import android.app.Activity
import android.content.Intent
import android.view.View
import android.widget.Toast

/** Adds inspection navigation without changing the upstream chat or TTS controllers. */
object InspectionEntry {
    fun bind(activity: Activity, canOpen: () -> Boolean) {
        activity.findViewById<View>(R.id.btn_inspection).setOnClickListener {
            if (!canOpen()) {
                Toast.makeText(activity, R.string.inspection_wait_for_model, Toast.LENGTH_SHORT).show()
            } else {
                activity.startActivity(Intent(activity, InspectionActivity::class.java))
            }
        }
    }
}
