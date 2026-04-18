package com.tourism.gate.ui.customer

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import com.tourism.gate.R
import com.tourism.gate.ui.LoginActivity

class ProfileFragment : Fragment() {

    private lateinit var tvName:   TextView
    private lateinit var tvEmail:  TextView
    private lateinit var editName: EditText
    private lateinit var editPhone: EditText
    private lateinit var editCccd:  EditText
    private lateinit var btnEditSave: TextView
    private lateinit var btnLogout:   TextView
    private lateinit var rgTheme:     android.widget.RadioGroup

    private var isEditing = false

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View? {
        val view = inflater.inflate(R.layout.fragment_profile, container, false)
        
        tvName     = view.findViewById(R.id.tv_profile_name)
        tvEmail    = view.findViewById(R.id.tv_profile_email)
        editName   = view.findViewById(R.id.edit_name)
        editPhone  = view.findViewById(R.id.edit_phone)
        editCccd   = view.findViewById(R.id.edit_cccd)
        btnEditSave = view.findViewById(R.id.btn_edit_save)
        btnLogout  = view.findViewById(R.id.btn_logout)
        rgTheme    = view.findViewById(R.id.rg_theme)

        loadUserData()
        setupThemeSelection()

        btnEditSave.setOnClickListener {
// ... (rest of logic)
            if (isEditing) {
                confirmSave()
            } else {
                enterEditMode()
            }
        }

        btnLogout.setOnClickListener { confirmLogout() }

        return view
    }

    private fun setupThemeSelection() {
        val prefs = requireContext().getSharedPreferences("gate_prefs", Context.MODE_PRIVATE)
        val currentTheme = prefs.getInt("app_theme", androidx.appcompat.app.AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM)

        when (currentTheme) {
            androidx.appcompat.app.AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM -> rgTheme.check(R.id.rb_theme_system)
            androidx.appcompat.app.AppCompatDelegate.MODE_NIGHT_NO -> rgTheme.check(R.id.rb_theme_light)
            androidx.appcompat.app.AppCompatDelegate.MODE_NIGHT_YES -> rgTheme.check(R.id.rb_theme_dark)
        }

        rgTheme.setOnCheckedChangeListener { _, checkedId ->
            val mode = when (checkedId) {
                R.id.rb_theme_light  -> androidx.appcompat.app.AppCompatDelegate.MODE_NIGHT_NO
                R.id.rb_theme_dark   -> androidx.appcompat.app.AppCompatDelegate.MODE_NIGHT_YES
                else -> androidx.appcompat.app.AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM
            }
            
            prefs.edit().putInt("app_theme", mode).apply()
            androidx.appcompat.app.AppCompatDelegate.setDefaultNightMode(mode)
        }
    }

    private fun loadUserData() {
        val prefs = requireContext().getSharedPreferences("gate_prefs", Context.MODE_PRIVATE)
        val name  = prefs.getString("customer_name", "Khách hàng")
        val email = prefs.getString("customer_email", "")
        val phone = prefs.getString("customer_phone", "")
        val cccd  = prefs.getString("customer_cccd", "")

        tvName.text = name
        tvEmail.text = email
        editName.setText(name)
        editPhone.setText(phone)
        editCccd.setText(cccd)
    }

    private fun enterEditMode() {
        isEditing = true
        editName.isEnabled  = true
        editPhone.isEnabled = true
        editCccd.isEnabled  = true
        
        editName.requestFocus()
        btnEditSave.text = "💾 LƯU THAY ĐỔI"
        btnEditSave.setBackgroundResource(R.drawable.bg_btn_primary) // Match style
    }

    private fun confirmSave() {
        AlertDialog.Builder(requireContext())
            .setTitle("Xác nhận lưu")
            .setMessage("Bạn có chắc chắn muốn cập nhật thông tin cá nhân không?")
            .setPositiveButton("Lưu") { _, _ -> saveChanges() }
            .setNegativeButton("Hủy", null)
            .show()
    }

    private fun saveChanges() {
        val newName  = editName.text.toString().trim()
        val newPhone = editPhone.text.toString().trim()
        val newCccd  = editCccd.text.toString().trim()

        if (newName.isEmpty()) {
            Toast.makeText(context, "Tên không được để trống", Toast.LENGTH_SHORT).show()
            return
        }

        // Simulating save to Prefs (Real app would call API)
        val prefs = requireContext().getSharedPreferences("gate_prefs", Context.MODE_PRIVATE)
        prefs.edit().apply {
            putString("customer_name",  newName)
            putString("customer_phone", newPhone)
            putString("customer_cccd",  newCccd)
            apply()
        }

        exitEditMode()
        loadUserData()
        Toast.makeText(context, "Đã cập nhật thông tin thành công!", Toast.LENGTH_SHORT).show()
    }

    private fun exitEditMode() {
        isEditing = false
        editName.isEnabled  = false
        editPhone.isEnabled = false
        editCccd.isEnabled  = false
        btnEditSave.text = "✎ CHỈNH SỬA HỒ SƠ"
    }

    private fun confirmLogout() {
        AlertDialog.Builder(requireContext())
            .setTitle("Đăng xuất")
            .setMessage("Bạn có chắc muốn đăng xuất không?")
            .setPositiveButton("Đăng xuất") { _, _ ->
                requireContext().getSharedPreferences("gate_prefs", Context.MODE_PRIVATE).edit().clear().apply()
                startActivity(Intent(requireContext(), LoginActivity::class.java))
                requireActivity().finish()
            }
            .setNegativeButton("Hủy", null)
            .show()
    }
}
