package com.example.minicpm_v_demo

import android.content.Context
import android.content.ContextWrapper
import android.content.SharedPreferences

/** Shares downloaded model files while keeping inspection settings out of chat preferences. */
class InspectionModelContext(base: Context) : ContextWrapper(base.applicationContext) {
    override fun getApplicationContext(): Context = this

    override fun getSharedPreferences(name: String, mode: Int): SharedPreferences =
        super.getSharedPreferences(if (name == "model_prefs") "inspection_model_prefs" else name, mode)
}
