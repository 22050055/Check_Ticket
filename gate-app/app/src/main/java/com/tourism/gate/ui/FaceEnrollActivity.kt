package com.tourism.gate.ui

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.os.Bundle
import android.os.Handler
import android.os.Looper
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
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * FaceEnrollActivity — Chụp 3 ảnh khuôn mặt khi bán vé (opt-in).
 *
 * Theo góp ý GVHD:
 *  - Chụp 3–5 ảnh ở góc nhìn hơi khác nhau
 *  - Lưu nhiều embedding mẫu → verify lấy MAX similarity
 *  - Xóa ảnh gốc sau khi trích xuất embedding
 *
 * Flow: chụp ảnh 1 → 2 → 3 → gửi lên /api/face/enroll → finish
 */
class FaceEnrollActivity : AppCompatActivity() {

    companion object {
        private const val TOTAL_SHOTS  = 3           // Số ảnh cần chụp
        private const val SHOT_DELAY   = 800L        // Delay giữa các ảnh (ms)
    }

    private lateinit var previewView:   PreviewView
    private lateinit var btnCapture:    TextView
    private lateinit var btnSkip:       TextView
    private lateinit var btnBack:       TextView
    private lateinit var btnFlipCamera: TextView
    private lateinit var tvStatus:      TextView
    private lateinit var progressBar:   ProgressBar

    private var imageCapture:    ImageCapture? = null
    private lateinit var cameraExecutor: ExecutorService
    private var ticketId:        String = ""

    // Camera state
    private var useFrontCamera   = true
    private var cameraProvider:  ProcessCameraProvider? = null

    // Multi-shot state
    private val capturedImages   = mutableListOf<Bitmap>()
    private var isCapturing      = false

    private val requestPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) startCamera()
        else { tvStatus.text = "Cần quyền camera"; btnCapture.isEnabled = false }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_face_verify)

        previewView   = findViewById(R.id.previewView)
        btnCapture    = findViewById(R.id.btnCapture)
        btnSkip       = findViewById(R.id.btnSkip)
        btnBack       = findViewById(R.id.btnBack)
        btnFlipCamera = findViewById(R.id.btnFlipCamera)
        tvStatus      = findViewById(R.id.tvStatus)
        progressBar   = findViewById(R.id.progressBar)

        ticketId = intent.getStringExtra("ticket_id") ?: ""

        btnCapture.text = "📷  Chụp 3 ảnh & Đăng ký"
        btnSkip.text    = "Bỏ qua"
        updateStatusHint()

        cameraExecutor = Executors.newSingleThreadExecutor()

        btnBack.setOnClickListener       { if (!isCapturing) finish() }
        btnSkip.setOnClickListener       { if (!isCapturing) finish() }
        btnCapture.setOnClickListener    { if (!isCapturing) startMultiShot() }
        btnFlipCamera.setOnClickListener { if (!isCapturing) flipCamera() }

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            requestPermission.launch(Manifest.permission.CAMERA)
        }
    }

    // ── Camera ────────────────────────────────────────────────

    private fun startCamera() {
        ProcessCameraProvider.getInstance(this).addListener({
            cameraProvider = ProcessCameraProvider.getInstance(this).get()
            bindCamera()
        }, ContextCompat.getMainExecutor(this))
    }

    private fun bindCamera() {
        val provider = cameraProvider ?: return
        val selector = if (useFrontCamera)
            CameraSelector.DEFAULT_FRONT_CAMERA
        else
            CameraSelector.DEFAULT_BACK_CAMERA

        val preview = Preview.Builder().build().also {
            it.setSurfaceProvider(previewView.surfaceProvider)
        }
        imageCapture = ImageCapture.Builder()
            .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
            .build()

        try {
            provider.unbindAll()
            provider.bindToLifecycle(this, selector, preview, imageCapture)
            btnFlipCamera.text = if (useFrontCamera) "🔄" else "🤳"
        } catch (e: Exception) {
            tvStatus.text = "Lỗi camera: ${e.message}"
        }
    }

    private fun flipCamera() {
        useFrontCamera = !useFrontCamera
        bindCamera()
    }

    // ── Multi-shot capture ───────────────────────────────────

    /**
     * Chụp 3 ảnh liên tiếp (cách nhau SHOT_DELAY ms) để lấy nhiều góc.
     * Hướng dẫn khách xoay đầu nhẹ giữa các lần chụp.
     */
    private fun startMultiShot() {
        capturedImages.clear()
        isCapturing            = true
        btnCapture.isEnabled   = false
        btnFlipCamera.isEnabled = false
        btnSkip.isEnabled      = false
        btnBack.isEnabled      = false
        progressBar.visibility = View.VISIBLE

        captureNextShot()
    }

    private fun captureNextShot() {
        val shotNum = capturedImages.size + 1
        val hints   = listOf("Nhìn thẳng", "Xoay nhẹ trái", "Xoay nhẹ phải")
        tvStatus.text = "📷 Ảnh $shotNum/$TOTAL_SHOTS — ${hints.getOrElse(capturedImages.size) { "Giữ nguyên" }}"

        val capture = imageCapture ?: run { onCaptureError("Camera chưa sẵn sàng"); return }
        capture.takePicture(
            ContextCompat.getMainExecutor(this),
            object : ImageCapture.OnImageCapturedCallback() {
                override fun onCaptureSuccess(image: ImageProxy) {
                    val bmp = imageProxyToBitmap(image)
                    image.close()
                    capturedImages.add(bmp)

                    if (capturedImages.size < TOTAL_SHOTS) {
                        // Chụp ảnh tiếp theo sau delay ngắn
                        Handler(Looper.getMainLooper()).postDelayed({
                            captureNextShot()
                        }, SHOT_DELAY)
                    } else {
                        // Đã đủ 3 ảnh → gửi lên server
                        tvStatus.text = "✅ Đã chụp $TOTAL_SHOTS ảnh. Đang đăng ký..."
                        enrollFaceMulti(capturedImages.toList())
                    }
                }
                override fun onError(e: ImageCaptureException) {
                    onCaptureError("Chụp ảnh ${capturedImages.size + 1} thất bại: ${e.message}")
                }
            }
        )
    }

    private fun onCaptureError(msg: String) {
        isCapturing             = false
        tvStatus.text           = "❌ $msg"
        btnCapture.isEnabled    = true
        btnFlipCamera.isEnabled = true
        btnSkip.isEnabled       = true
        btnBack.isEnabled       = true
        progressBar.visibility  = View.GONE
        capturedImages.clear()
    }

    // ── Enroll nhiều ảnh ─────────────────────────────────────

    private fun enrollFaceMulti(bitmaps: List<Bitmap>) {
        val imagesB64 = bitmaps.map { bmp ->
            val stream = ByteArrayOutputStream()
            bmp.compress(Bitmap.CompressFormat.JPEG, 85, stream)
            "data:image/jpeg;base64," +
                    Base64.encodeToString(stream.toByteArray(), Base64.NO_WRAP)
        }

        lifecycleScope.launch {
            try {
                val api  = ApiClient.create(this@FaceEnrollActivity)
                // Gửi nhiều ảnh — backend /api/face/enroll nhận images_b64
                val resp = api.enrollFace(
                    mapOf(
                        "ticket_id"   to ticketId,
                        "images_b64"  to imagesB64      // list<String>
                    )
                )

                tvStatus.text          = "✅ Đăng ký ${resp.embeddingDim > 0} mẫu thành công!"
                progressBar.visibility = View.GONE

                Handler(Looper.getMainLooper()).postDelayed({ finish() }, 1800)

            } catch (e: Exception) {
                onCaptureError("Lỗi đăng ký: ${e.message}")
            }
        }
    }

    // ── Util ─────────────────────────────────────────────────

    private fun updateStatusHint() {
        tvStatus.text = "Giữ điện thoại ngang tầm mặt\nNhìn thẳng vào camera"
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
