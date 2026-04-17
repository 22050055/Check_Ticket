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
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.model.CheckinRequest
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * FaceVerifyActivity — Xác thực khuôn mặt tại cổng check-in/out.
 *
 * Theo góp ý GVHD & flow đúng:
 *  1. Nhận qr_token từ ScanActivity (chưa tiêu thụ nonce)
 *  2. Chụp ảnh probe tại camera
 *  3. Gọi /api/checkin channel=QR_FACE (qr_token + probe_image_b64)
 *     → Backend: verify JWT (tiêu thụ nonce) + trích xuất embedding probe
 *               + so sánh với stored_embeddings bằng cosine similarity
 *               + trả kết quả
 *  4. Hiển thị ResultActivity
 *
 * Nonce chỉ bị tiêu thụ đúng 1 lần tại bước 3.
 */
class FaceVerifyActivity : AppCompatActivity() {

    private lateinit var previewView:   PreviewView
    private lateinit var btnCapture:    TextView
    private lateinit var btnSkip:       TextView
    private lateinit var btnBack:       TextView
    private lateinit var btnFlipCamera: TextView
    private lateinit var tvStatus:      TextView
    private lateinit var progressBar:   ProgressBar

    private var imageCapture:    ImageCapture? = null
    private lateinit var cameraExecutor: ExecutorService

    private var qrToken:     String = ""
    private var ticketId:    String = ""
    private var ticketType:  String = ""

    // Camera state — camera trước cho verify mặt người
    private var useFrontCamera  = true
    private var cameraProvider: ProcessCameraProvider? = null
    private var isProcessing    = false

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

        qrToken    = intent.getStringExtra("qr_token")    ?: ""
        ticketId   = intent.getStringExtra("ticket_id")   ?: ""
        ticketType = intent.getStringExtra("ticket_type") ?: ""

        btnCapture.text = "📷  Chụp & Xác thực"
        btnSkip.text    = "Bỏ qua xác thực mặt"
        tvStatus.text   = "Nhìn thẳng vào camera để xác thực"

        cameraExecutor = Executors.newSingleThreadExecutor()

        btnBack.setOnClickListener       { if (!isProcessing) finish() }
        btnFlipCamera.setOnClickListener { if (!isProcessing) flipCamera() }
        btnCapture.setOnClickListener    { if (!isProcessing) captureAndVerify() }

        // Bỏ qua face → vẫn checkin bằng QR-only (tiêu thụ nonce ở đây)
        btnSkip.setOnClickListener {
            if (!isProcessing) doQrOnlyCheckin()
        }

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            requestPermission.launch(Manifest.permission.CAMERA)
        }
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

    // ── Chụp ảnh & xác thực ────────────────────────────────────

    private fun captureAndVerify() {
        val capture = imageCapture ?: return
        isProcessing            = true
        btnCapture.isEnabled    = false
        btnFlipCamera.isEnabled = false
        btnSkip.isEnabled       = false
        progressBar.visibility  = View.VISIBLE
        tvStatus.text           = "Đang chụp ảnh..."

        capture.takePicture(
            ContextCompat.getMainExecutor(this),
            object : ImageCapture.OnImageCapturedCallback() {
                override fun onCaptureSuccess(image: ImageProxy) {
                    val bmp = imageProxyToBitmap(image)
                    image.close()
                    doQrFaceCheckin(bmp)
                }
                override fun onError(e: ImageCaptureException) {
                    onError("Chụp ảnh thất bại: ${e.message}")
                }
            }
        )
    }

    /**
     * Gọi /api/checkin channel=QR_FACE:
     *  - qr_token: JWT để backend verify chữ ký + tiêu thụ nonce
     *  - probe_image_b64: ảnh vừa chụp để backend trích xuất embedding + so sánh
     *
     * Backend xử lý hoàn toàn — app không cần biết threshold hay embedding.
     */
    private fun doQrFaceCheckin(bitmap: Bitmap) {
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
                val api    = ApiClient.create(this@FaceVerifyActivity)
                val result = api.checkin(
                    CheckinRequest(
                        gate_id          = gateId,
                        direction        = direction,
                        channel          = "QR_FACE",    // Backend: verify JWT + compare embedding
                        qr_token         = qrToken,
                        probe_image_b64  = probeB64
                    )
                )

                val msg = buildString {
                    append(result.message)
                    result.face_score?.let { score ->
                        append("\nFace score: ${"%.3f".format(score)}")
                    }
                }
                goToResult(result.success, msg, result.ticket_type)

            } catch (e: Exception) {
                goToResult(false, "Lỗi xác thực: ${e.message}", ticketType)
            }
        }
    }

    /**
     * Người dùng bấm "Bỏ qua" → vẫn checkin bằng QR-only.
     * Nonce được tiêu thụ ở đây thay vì ở QR_FACE.
     */
    private fun doQrOnlyCheckin() {
        isProcessing = true
        btnCapture.isEnabled  = false
        btnSkip.isEnabled     = false
        progressBar.visibility = View.VISIBLE
        tvStatus.text          = "Đang xác thực QR..."

        val prefs     = getSharedPreferences("gate_prefs", MODE_PRIVATE)
        val direction = prefs.getString("direction", "IN") ?: "IN"
        val gateId    = prefs.getString("selected_gate_id", "") ?: ""

        lifecycleScope.launch {
            try {
                val api    = ApiClient.create(this@FaceVerifyActivity)
                val result = api.checkin(
                    CheckinRequest(
                        gate_id   = gateId,
                        direction = direction,
                        channel   = "QR",
                        qr_token  = qrToken
                    )
                )
                goToResult(result.success, result.message + "\n(Bỏ qua xác thực khuôn mặt)", result.ticket_type)
            } catch (e: Exception) {
                goToResult(false, "Lỗi: ${e.message}", ticketType)
            }
        }
    }

    private fun onError(msg: String) {
        isProcessing            = false
        tvStatus.text           = "❌ $msg"
        btnCapture.isEnabled    = true
        btnFlipCamera.isEnabled = true
        btnSkip.isEnabled       = true
        progressBar.visibility  = View.GONE
    }

    private fun goToResult(success: Boolean, message: String, type: String?) {
        startActivity(
            Intent(this, ResultActivity::class.java).apply {
                putExtra("success",     success)
                putExtra("message",     message)
                putExtra("ticket_type", type)
            }
        )
        finish()
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
 