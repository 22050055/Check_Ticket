package com.tourism.gate.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.os.Bundle
import android.util.Base64
import android.view.View
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.model.CheckinRequest
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * ScanActivity — Quét QR + Xác thực khuôn mặt trong 1 màn hình.
 *
 * 2 mode trên cùng 1 Activity:
 *  MODE_SCAN — camera sau, khung vuông QR, nút Tìm thủ công
 *  MODE_FACE — khung oval mặt, nút Chụp mặt, giữ camera hiện tại
 *
 * Flow:
 *  1. Quét QR → decode JWT lấy ticket_id
 *  2. GET /api/tickets/{id} → has_face?
 *  3a. has_face=false → checkin QR trực tiếp → ResultActivity
 *  3b. has_face=true  → chuyển MODE_FACE (cùng màn hình)
 *  4. Chụp ảnh → POST /api/checkin QR_FACE → ResultActivity
 */
class ScanActivity : AppCompatActivity() {

    // ── Views ─────────────────────────────────────────────────
    private lateinit var previewView:    PreviewView
    private lateinit var btnManual:      TextView
    private lateinit var btnCaptureFace: TextView
    private lateinit var btnFlipCamera:  TextView
    private lateinit var btnBack:        TextView
    private lateinit var tvTitle:        TextView
    private lateinit var tvStatus:       TextView
    private lateinit var tvHint:         TextView
    private lateinit var progressBar:    ProgressBar
    private lateinit var tvDirection:    TextView
    private lateinit var qrFrame:        View
    private lateinit var faceOval:       View

    // ── State ─────────────────────────────────────────────────
    private enum class Mode { SCAN, FACE }
    private var mode         = Mode.SCAN
    private var isProcessing = false
    private var pendingQrToken: String? = null   // lưu token khi chuyển sang MODE_FACE

    // ── Camera ────────────────────────────────────────────────
    private var useBackCamera   = true
    private var cameraProvider: ProcessCameraProvider? = null
    private var imageCapture:   ImageCapture? = null
    private lateinit var cameraExecutor: ExecutorService

    private val requestPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) startCamera()
        else { tvStatus.text = "Cần quyền truy cập camera" }
    }

    // ── onCreate ──────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_scan)

        previewView    = findViewById(R.id.previewView)
        btnManual      = findViewById(R.id.btnManual)
        btnCaptureFace = findViewById(R.id.btnCaptureFace)
        btnFlipCamera  = findViewById(R.id.btnFlipCamera)
        btnBack        = findViewById(R.id.btnBack)
        tvTitle        = findViewById(R.id.tvTitle)
        tvStatus       = findViewById(R.id.tvStatus)
        tvHint         = findViewById(R.id.tvHint)
        progressBar    = findViewById(R.id.progressBar)
        tvDirection    = findViewById(R.id.tvDirection)
        qrFrame        = findViewById(R.id.qrFrame)
        faceOval       = findViewById(R.id.faceOval)

        cameraExecutor = Executors.newSingleThreadExecutor()

        val prefs     = getSharedPreferences("gate_prefs", MODE_PRIVATE)
        val direction = prefs.getString("direction", "IN") ?: "IN"
        tvDirection.text = if (direction == "IN") "▶ VÀO" else "◀ RA"
        tvDirection.setBackgroundColor(
            if (direction == "IN") 0xFF52C41A.toInt() else 0xFFF5222D.toInt()
        )

        btnBack.setOnClickListener {
            if (mode == Mode.FACE) {
                // Quay về mode quét QR, không checkin
                switchMode(Mode.SCAN)
            } else {
                finish()
            }
        }
        btnManual.setOnClickListener {
            startActivity(Intent(this, ManualSearchActivity::class.java))
        }
        btnFlipCamera.setOnClickListener { flipCamera() }
        btnCaptureFace.setOnClickListener { captureAndVerify() }

        applyMode(Mode.SCAN)

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            requestPermission.launch(Manifest.permission.CAMERA)
        }
    }

    // ── Mode switching ─────────────────────────────────────────

    private fun switchMode(newMode: Mode) {
        mode         = newMode
        isProcessing = false
        applyMode(newMode)
        bindCamera()   // đổi camera trước/sau theo mode
    }

    private fun applyMode(m: Mode) {
        when (m) {
            Mode.SCAN -> {
                tvTitle.text           = "QUÉT MÃ QR"
                tvHint.text            = "Đưa mã QR vào khung"
                tvStatus.text          = ""
                qrFrame.visibility     = View.VISIBLE
                faceOval.visibility    = View.GONE
                btnManual.visibility   = View.VISIBLE
                btnCaptureFace.visibility = View.GONE
                useBackCamera          = true
            }
            Mode.FACE -> {
                tvTitle.text           = "XÁC THỰC KHUÔN MẶT"
                tvHint.text            = "Nhìn thẳng vào camera"
                tvStatus.text          = "Đưa khuôn mặt vào khung oval"
                qrFrame.visibility     = View.GONE
                faceOval.visibility    = View.VISIBLE
                btnManual.visibility   = View.GONE
                btnCaptureFace.visibility = View.VISIBLE
                // Giữ camera hiện tại — nhân viên tự flip nếu cần
            }
        }
        btnFlipCamera.text = if (useBackCamera) "🔄" else "🤳"
    }

    // ── Camera ─────────────────────────────────────────────────

    private fun startCamera() {
        ProcessCameraProvider.getInstance(this).addListener({
            cameraProvider = ProcessCameraProvider.getInstance(this).get()
            bindCamera()
        }, ContextCompat.getMainExecutor(this))
    }

    private fun bindCamera() {
        val provider = cameraProvider ?: return
        val selector = if (useBackCamera)
            CameraSelector.DEFAULT_BACK_CAMERA
        else
            CameraSelector.DEFAULT_FRONT_CAMERA

        val preview = Preview.Builder().build().also {
            it.setSurfaceProvider(previewView.surfaceProvider)
        }

        imageCapture = ImageCapture.Builder()
            .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
            .build()

        // Mode SCAN thêm QR analyzer, Mode FACE không cần
        try {
            provider.unbindAll()
            if (mode == Mode.SCAN) {
                val qrAnalysis = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .build()
                    .also { it.setAnalyzer(cameraExecutor, QrAnalyzer()) }
                provider.bindToLifecycle(this, selector, preview, qrAnalysis, imageCapture)
            } else {
                provider.bindToLifecycle(this, selector, preview, imageCapture)
            }
            btnFlipCamera.text = if (useBackCamera) "🔄" else "🤳"
        } catch (e: Exception) {
            tvStatus.text = "Lỗi camera: ${e.message}"
        }
    }

    private fun flipCamera() {
        if (isProcessing) return
        useBackCamera = !useBackCamera
        isProcessing  = false
        bindCamera()
    }

    // ── QR Analyzer (chỉ dùng ở Mode.SCAN) ────────────────────

    @androidx.camera.core.ExperimentalGetImage
    inner class QrAnalyzer : ImageAnalysis.Analyzer {
        private val scanner = BarcodeScanning.getClient()
        override fun analyze(imageProxy: ImageProxy) {
            if (isProcessing || mode != Mode.SCAN) { imageProxy.close(); return }
            val mediaImage = imageProxy.image ?: run { imageProxy.close(); return }
            val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
            scanner.process(image)
                .addOnSuccessListener { barcodes ->
                    val qr = barcodes.firstOrNull()?.rawValue
                    if (qr != null && qr.contains(".")) {
                        isProcessing = true
                        runOnUiThread { handleQrScanned(qr) }
                    }
                }
                .addOnCompleteListener { imageProxy.close() }
        }
    }

    // ── Xử lý QR ───────────────────────────────────────────────

    private fun handleQrScanned(token: String) {
        val ticketId = extractTicketIdFromJwt(token)
        if (ticketId == null) {
            goToResult(false, "QR không hợp lệ", null)
            return
        }

        setLoading(true)
        tvStatus.text = "Đang kiểm tra vé..."

        lifecycleScope.launch {
            try {
                val api    = ApiClient.create(this@ScanActivity)
                val ticket = api.getTicket(ticketId)

                setLoading(false)

                if (ticket.hasFace) {
                    // Lưu token, chuyển sang mode chụp mặt
                    pendingQrToken = token
                    switchMode(Mode.FACE)
                } else {
                    doQrCheckin(token)
                }
            } catch (e: Exception) {
                setLoading(false)
                // Offline / lỗi → vẫn thử QR-only
                doQrCheckin(token)
            }
        }
    }

    // ── Checkin QR-only ────────────────────────────────────────

    private fun doQrCheckin(token: String) {
        val prefs     = getSharedPreferences("gate_prefs", MODE_PRIVATE)
        val direction = prefs.getString("direction", "IN") ?: "IN"
        val gateId    = prefs.getString("selected_gate_id", "") ?: ""

        setLoading(true)
        tvStatus.text = "Đang xác thực QR..."

        lifecycleScope.launch {
            try {
                val api    = ApiClient.create(this@ScanActivity)
                val result = api.checkin(
                    CheckinRequest(
                        gate_id   = gateId,
                        direction = direction,
                        channel   = "QR",
                        qr_token  = token
                    )
                )
                goToResult(result.success, result.message, result.ticket_type)
            } catch (e: Exception) {
                goToResult(false, "Lỗi kết nối: ${e.message}", null)
            } finally {
                setLoading(false)
            }
        }
    }

    // ── Chụp mặt & checkin QR_FACE ────────────────────────────

    private fun captureAndVerify() {
        val capture = imageCapture ?: return
        val token   = pendingQrToken ?: run {
            tvStatus.text = "Lỗi: mất QR token, vui lòng quét lại"
            switchMode(Mode.SCAN)
            return
        }

        isProcessing            = true
        btnCaptureFace.isEnabled = false
        btnFlipCamera.isEnabled  = false
        setLoading(true)
        tvStatus.text = "Đang chụp ảnh..."

        capture.takePicture(
            ContextCompat.getMainExecutor(this),
            object : ImageCapture.OnImageCapturedCallback() {
                override fun onCaptureSuccess(image: ImageProxy) {
                    val bmp = imageProxyToBitmap(image)
                    image.close()
                    doQrFaceCheckin(token, bmp)
                }
                override fun onError(e: ImageCaptureException) {
                    isProcessing             = false
                    btnCaptureFace.isEnabled = true
                    btnFlipCamera.isEnabled  = true
                    setLoading(false)
                    tvStatus.text = "Chụp thất bại: ${e.message}"
                }
            }
        )
    }

    private fun doQrFaceCheckin(token: String, bitmap: Bitmap) {
        tvStatus.text = "Đang xác thực khuôn mặt..."

        val stream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, 85, stream)
        val probeB64 = "data:image/jpeg;base64," +
                Base64.encodeToString(stream.toByteArray(), Base64.NO_WRAP)

        val prefs     = getSharedPreferences("gate_prefs", MODE_PRIVATE)
        val direction = prefs.getString("direction", "IN") ?: "IN"
        val gateId    = prefs.getString("selected_gate_id", "") ?: ""

        lifecycleScope.launch {
            try {
                val api    = ApiClient.create(this@ScanActivity)
                val result = api.checkin(
                    CheckinRequest(
                        gate_id         = gateId,
                        direction       = direction,
                        channel         = "QR_FACE",
                        qr_token        = token,
                        probe_image_b64 = probeB64
                    )
                )
                val msg = result.message +
                        (result.face_score?.let { "\nFace score: ${"%.3f".format(it)}" } ?: "")
                goToResult(result.success, msg, result.ticket_type)
            } catch (e: Exception) {
                goToResult(false, "Lỗi xác thực: ${e.message}", null)
            } finally {
                setLoading(false)
                btnCaptureFace.isEnabled = true
                btnFlipCamera.isEnabled  = true
            }
        }
    }

    // ── Utils ───────────────────────────────────────────────────

    private fun extractTicketIdFromJwt(token: String): String? {
        return try {
            val parts  = token.split(".")
            if (parts.size < 2) return null
            val padded = parts[1] + "=".repeat((4 - parts[1].length % 4) % 4)
            val json   = String(Base64.decode(padded, Base64.URL_SAFE))
            Regex(""""sub"\s*:\s*"([^"]+)"""").find(json)?.groupValues?.get(1)
        } catch (e: Exception) { null }
    }

    private fun goToResult(success: Boolean, message: String, ticketType: String?) {
        startActivity(
            Intent(this, ResultActivity::class.java).apply {
                putExtra("success",     success)
                putExtra("message",     message)
                putExtra("ticket_type", ticketType)
            }
        )
        finish()
    }

    private fun setLoading(loading: Boolean) {
        progressBar.visibility = if (loading) View.VISIBLE else View.GONE
    }

    private fun imageProxyToBitmap(image: ImageProxy): Bitmap {
        val buffer = image.planes[0].buffer
        val bytes  = ByteArray(buffer.remaining())
        buffer.get(bytes)
        return android.graphics.BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }
}
