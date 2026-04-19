package com.tourism.gate.ui.customer

import android.content.Intent
import android.os.Bundle
import android.view.MotionEvent
import android.widget.FrameLayout
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.fragment.app.Fragment
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.tourism.gate.R
import com.tourism.gate.ui.AiChatActivity

/**
 * CustomerDashboardActivity — Màn hình chính cho Khách hàng.
 * Sử dụng Bottom Navigation để chuyển đổi giữa 4 phân vùng:
 * Home (Trang chủ), Tickets (Lịch sử vé), Buy (Mua vé), Profile (Cá nhân).
 */
class CustomerDashboardActivity : AppCompatActivity() {

    private lateinit var bottomNav: BottomNavigationView
    private lateinit var aiBallContainer: FrameLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        // Áp dụng theme (Sáng/Tối) trước khi setContentView
        val prefs = getSharedPreferences("gate_prefs", MODE_PRIVATE)
        val savedTheme = prefs.getInt("app_theme", AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM)
        AppCompatDelegate.setDefaultNightMode(savedTheme)

        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_customer_dashboard)

        bottomNav = findViewById(R.id.bottom_navigation)
        aiBallContainer = findViewById(R.id.ai_ball_container)

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

        // Mặc định mở Trang chủ (Home) hoặc tab được chỉ định từ Intent
        if (savedInstanceState == null) {
            val openTab = intent.getIntExtra("open_tab", R.id.nav_home)
            if (openTab != R.id.nav_home) {
                // Việc gán selectedItemId ở đây sẽ kích hoạt Listener bên trên
                bottomNav.selectedItemId = openTab
            } else {
                replaceFragment(HomeFragment())
            }
        }

        setupAiBall()
    }

    private fun setupAiBall() {
        var dX = 0f
        var dY = 0f
        var startX = 0f
        var startY = 0f

        aiBallContainer.setOnTouchListener { view, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    dX = view.x - event.rawX
                    dY = view.y - event.rawY
                    startX = event.rawX
                    startY = event.rawY
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    view.animate()
                        .x(event.rawX + dX)
                        .y(event.rawY + dY)
                        .setDuration(0)
                        .start()
                    true
                }
                MotionEvent.ACTION_UP -> {
                    // Nếu quãng đường di chuyển rất nhỏ, coi là Click
                    val diffX = Math.abs(event.rawX - startX)
                    val diffY = Math.abs(event.rawY - startY)
                    if (diffX < 10 && diffY < 10) {
                        AiChatBottomSheet().show(supportFragmentManager, "AiChat")
                    } else {
                        // Tự động hít vào cạnh trái hoặc phải
                        val screenWidth = resources.displayMetrics.widthPixels
                        val finalX = if (view.x + view.width / 2 < screenWidth / 2) 0f else (screenWidth - view.width).toFloat()
                        view.animate().x(finalX).setDuration(300).start()
                    }
                    true
                }
                else -> false
            }
        }
    }


    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        val openTab = intent.getIntExtra("open_tab", -1)
        if (openTab != -1) {
            bottomNav.selectedItemId = openTab
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
