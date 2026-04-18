package com.tourism.gate.ui.customer

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.tourism.gate.R
import com.tourism.gate.ui.LoginActivity

/**
 * CustomerDashboardActivity — Màn hình chính cho Khách hàng.
 * Sử dụng Bottom Navigation để chuyển đổi giữa 4 phân vùng:
 * Home (Trang chủ), Tickets (Lịch sử vé), Buy (Mua vé), Profile (Cá nhân).
 */
class CustomerDashboardActivity : AppCompatActivity() {

    private lateinit var bottomNav: BottomNavigationView

    override fun onCreate(savedInstanceState: Bundle?) {
        // Áp dụng theme (Sáng/Tối) trước khi setContentView
        val prefs = getSharedPreferences("gate_prefs", MODE_PRIVATE)
        val savedTheme = prefs.getInt("app_theme", androidx.appcompat.app.AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM)
        androidx.appcompat.app.AppCompatDelegate.setDefaultNightMode(savedTheme)

        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_customer_dashboard)

        bottomNav = findViewById(R.id.bottom_navigation)

        // Mặc định mở Trang chủ (Home) hoặc tab được chỉ định từ Intent
        if (savedInstanceState == null) {
            val openTab = intent.getIntExtra("open_tab", R.id.nav_home)
            if (openTab != R.id.nav_home) {
                bottomNav.selectedItemId = openTab
            } else {
                replaceFragment(HomeFragment())
            }
        }

        // Xử lý sự kiện click trên thanh điều hướng
        bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home     -> { replaceFragment(HomeFragment()); true }
                R.id.nav_tickets  -> { replaceFragment(TicketsFragment()); true }
                R.id.nav_buy      -> { replaceFragment(BuyFragment()); true }
                R.id.nav_profile  -> { replaceFragment(ProfileFragment()); true }
                else -> false
            }
        }
    }

    private fun replaceFragment(fragment: Fragment) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragment_container, fragment)
            .setCustomAnimations(android.R.anim.fade_in, android.R.anim.fade_out)
            .commit()
    }

    /**
     * Xử lý nút Back của hệ thống:
     * Nếu không ở trang Home, quay về trang Home trước khi thoát app.
     */
    override fun onBackPressed() {
        if (bottomNav.selectedItemId != R.id.nav_home) {
            bottomNav.selectedItemId = R.id.nav_home
        } else {
            super.onBackPressed()
        }
    }
}