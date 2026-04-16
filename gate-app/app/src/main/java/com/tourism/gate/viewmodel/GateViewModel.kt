package com.tourism.gate.viewmodel

import android.app.Application
import androidx.lifecycle.*
import com.tourism.gate.data.api.ApiClient
import com.tourism.gate.data.local.ShiftManager
import com.tourism.gate.data.model.Gate
import kotlinx.coroutines.launch

/**
 * GateViewModel — Logic chọn cổng và quản lý ca trực.
 *
 * Trách nhiệm:
 *  - Tải danh sách cổng từ API
 *  - Lưu cổng đã chọn vào SharedPreferences
 *  - Khởi động / kết thúc ca (ShiftManager)
 *  - Hiển thị trạng thái ca + số vé đã cache
 */
class GateViewModel(app: Application) : AndroidViewModel(app) {

    private val shiftManager = ShiftManager(app)

    // ── UI State ──────────────────────────────────────────

    sealed class GateState {
        object Loading : GateState()
        data class GatesLoaded(val gates: List<Gate>) : GateState()
        data class Error(val message: String)         : GateState()
    }

    sealed class ShiftState {
        object Idle     : ShiftState()
        object Starting : ShiftState()
        data class Active(
            val gateCode:      String,
            val cachedTickets: Int,
            val startTimeMs:   Long
        ) : ShiftState()
        data class Error(val message: String) : ShiftState()
    }

    private val _gateState  = MutableLiveData<GateState>()
    val gateState: LiveData<GateState> = _gateState

    private val _shiftState = MutableLiveData<ShiftState>(ShiftState.Idle)
    val shiftState: LiveData<ShiftState> = _shiftState

    private val _selectedGate = MutableLiveData<Gate?>()
    val selectedGate: LiveData<Gate?> = _selectedGate

    // ── Load gates ────────────────────────────────────────

    /**
     * Tải danh sách cổng từ API.
     * Gọi khi GateSelectActivity khởi động.
     */
    fun loadGates() {
        _gateState.value = GateState.Loading

        viewModelScope.launch {
            try {
                val api   = ApiClient.create(getApplication())
                val gates = api.listGates().filter { it.isActive }
                _gateState.value = GateState.GatesLoaded(gates)

                // Tự động chọn cổng đã được gán cho operator
                val prefs      = getApplication<Application>()
                    .getSharedPreferences("gate_prefs", android.content.Context.MODE_PRIVATE)
                val assignedId = prefs.getString("gate_id", "") ?: ""
                if (assignedId.isNotEmpty()) {
                    gates.find { it.gate_id == assignedId }?.let { selectGate(it) }
                }

            } catch (e: Exception) {
                _gateState.value = GateState.Error(
                    "Không tải được danh sách cổng: ${e.message}"
                )
            }
        }
    }

    // ── Select gate ───────────────────────────────────────

    /**
     * Operator chọn cổng làm việc → lưu vào SharedPreferences.
     */
    fun selectGate(gate: Gate) {
        _selectedGate.value = gate

        getApplication<Application>()
            .getSharedPreferences("gate_prefs", android.content.Context.MODE_PRIVATE)
            .edit()
            .putString("selected_gate_id",   gate.gate_id)
            .putString("selected_gate_code", gate.gate_code)
            .putString("selected_gate_name", gate.name)
            .apply()
    }

    // ── Shift management ──────────────────────────────────

    /**
     * Bắt đầu ca trực: cache vé active về local DB.
     * Gọi sau khi operator xác nhận cổng và hướng.
     */
    fun startShift() {
        val gate = _selectedGate.value ?: return
        _shiftState.value = ShiftState.Starting

        viewModelScope.launch {
            try {
                val cached = shiftManager.startShift()
                _shiftState.value = ShiftState.Active(
                    gateCode      = gate.gate_code,
                    cachedTickets = cached,
                    startTimeMs   = System.currentTimeMillis()
                )
            } catch (e: Exception) {
                _shiftState.value = ShiftState.Error("Lỗi khởi động ca: ${e.message}")
            }
        }
    }

    /**
     * Kết thúc ca: đồng bộ nonce offline + xóa cache.
     * Gọi khi operator bấm "Kết thúc ca" hoặc logout.
     */
    fun endShift() {
        viewModelScope.launch {
            try {
                shiftManager.endShift()
            } catch (_: Exception) { }
            _shiftState.value  = ShiftState.Idle
            _selectedGate.value = null
        }
    }

    /**
     * Đồng bộ nonce offline lên server (gọi khi mạng restore).
     */
    fun syncOfflineNonces() {
        viewModelScope.launch {
            try {
                val count = shiftManager.syncNonces()
                if (count > 0) {
                    android.util.Log.i("GateVM", "Đã đồng bộ $count nonces offline")
                }
            } catch (_: Exception) { }
        }
    }

    // ── Info helpers ──────────────────────────────────────

    fun isShiftActive(): Boolean = shiftManager.isShiftActive()

    fun getShiftDurationMinutes(): Long {
        val startMs = shiftManager.getShiftStartTime()
        if (startMs == 0L) return 0L
        return (System.currentTimeMillis() - startMs) / 60_000
    }

    override fun onCleared() {
        super.onCleared()
        // Không endShift ở đây vì ViewModel có thể bị recreate khi xoay màn hình
    }
}
