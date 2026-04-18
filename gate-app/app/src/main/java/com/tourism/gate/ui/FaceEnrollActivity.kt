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
import android.view.WindowManager
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.face.FaceDetection
import com.google.mlkit.vision.face.FaceDetector
import com.google.mlkit.vision.face.FaceDetectorOptions
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

    // ML Kit Face Detector
    private lateinit var faceDetector:   FaceDetector
    private var currentYaw:             Float = 0f
    private var requiredPose:           String = "FRONT" // FRONT, LEFT, RIGHT
    private var isPoseMet:              Boolean = false

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

        val options = FaceDetectorOptions.Builder()
            .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_FAST)
            .setClassificationMode(FaceDetectorOptions.CLASSIFICATION_MODE_NONE)
            .setLandmarkMode(FaceDetectorOptions.LANDMARK_MODE_NONE)
            .build()
        faceDetector = FaceDetection.getClient(options)

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            requestPermission.launch(Manifest.permission.CAMERA)
        }

        // Đảm bảo màn hình không tắt khi đang đăng ký khuôn mặt
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
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
        val imageAnalysis = ImageAnalysis.Builder()
            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
            .build()
            .also {
                it.setAnalyzer(cameraExecutor) { imageProxy ->
                    processImageProxy(imageProxy)
                }
            }

        try {
            provider.unbindAll()
            provider.bindToLifecycle(this, selector, preview, imageCapture, imageAnalysis)
            btnFlipCamera.text = if (useFrontCamera) "🔄" else "🤳"
        } catch (e: Exception) {
            tvStatus.text = "Lỗi camera: ${e.message}"
        }
    }

    @ExperimentalGetImage
    private fun processImageProxy(imageProxy: ImageProxy) {
        val mediaImage = imageProxy.image ?: run { imageProxy.close(); return }
        val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
        
        faceDetector.process(image)
            .addOnSuccessListener { faces ->
                if (faces.isNotEmpty()) {
                    val face = faces[0]
                    currentYaw = face.headEulerAngleY
                    checkPose(currentYaw)
                } else {
                    isPoseMet = false
                    if (!isCapturing) tvStatus.text = "Không tìm thấy khuôn mặt"
                }
            }
            .addOnCompleteListener {
                imageProxy.close()
            }
    }

    private fun checkPose(yaw: Float) {
        if (isCapturing) return

        val (met, hint) = when (requiredPose) {
            "FRONT" -> (yaw in -12f..12f) to "Nhìn thẳng vào camera"
            "LEFT"  -> (yaw > 25f)       to "Quay mặt sang trái ←"
            "RIGHT" -> (yaw < -25f)      to "Quay mặt sang phải →"
            else -> false to ""
        }
        
        isPoseMet = met
        if (met) {
            tvStatus.text = "✅ Sẵn sàng! Bấm nút để chụp"
            btnCapture.alpha = 1.0f
        } else {
            tvStatus.text = "⚠️ $hint"
            btnCapture.alpha = 0.5f
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
        requiredPose = when(shotNum) {
            1 -> "FRONT"
            2 -> "LEFT"
            3 -> "RIGHT"
            else -> "FRONT"
        }

        val hint = when(requiredPose) {
            "FRONT" -> "Nhìn thẳng"
            "LEFT"  -> "Quay trái"
            "RIGHT" -> "Quay phải"
            else    -> ""
        }
        
        tvStatus.text = "📷 Đang chụp ảnh $shotNum/3 ($hint)..."

        val capture = imageCapture ?: run { onCaptureError("Camera chưa sẵn sàng"); return }
        capture.takePicture(
            ContextCompat.getMainExecutor(this),
            object : ImageCapture.OnImageCapturedCallback() {
                override fun onCaptureSuccess(image: ImageProxy) {
                    val bmp = imageProxyToBitmap(image)
                    image.close()
                    capturedImages.add(bmp)

                    if (capturedImages.size < TOTAL_SHOTS) {
                        // Cập nhật pose tiếp theo và chờ khách chuẩn bị
                        val nextPose = when(capturedImages.size + 1) {
                            2 -> "LEFT"
                            3 -> "RIGHT"
                            else -> "FRONT"
                        }
                        requiredPose = nextPose
                        isPoseMet    = false
                        
                        val msg = when(nextPose) {
                            "LEFT" -> "Tốt! Bây giờ hãy QUAY SANG TRÁI ←"
                            "RIGHT" -> "Tốt! Bây giờ hãy QUAY SANG PHẢI →"
                            else -> "Chuẩn bị..."
                        }
                        tvStatus.text = msg
                        
                        // Delay ngắn để khách di chuyển
                        Handler(Looper.getMainLooper()).postDelayed({
                            captureNextShot()
                        }, 1500)
                    } else {
                        tvStatus.text = "✅ Đã chụp đủ $TOTAL_SHOTS ảnh. Đang đăng ký..."
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
            // Tối ưu hóa: Resize ảnh xuống max 640px
            val resizedBmp = getResizedBitmap(bmp, 640)
            
            val stream = ByteArrayOutputStream()
            resizedBmp.compress(Bitmap.CompressFormat.JPEG, 70, stream)
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

    private fun getResizedBitmap(image: Bitmap, maxSize: Int): Bitmap {
        var width  = image.width
        var height = image.height
        val bitmapRatio = width.toFloat() / height.toFloat()
        if (bitmapRatio > 1) {
            width = maxSize
            height = (width / bitmapRatio).toInt()
        } else {
            height = maxSize
            width = (height * bitmapRatio).toInt()
        }
        return Bitmap.createScaledBitmap(image, width, height, true)
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }
}
