package com.tourism.gate.ui

import android.app.Dialog
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.bottomsheet.BottomSheetBehavior
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import kotlinx.coroutines.launch

class AiChatBottomSheet : BottomSheetDialogFragment() {

    private lateinit var rvChat: RecyclerView
    private lateinit var etMessage: EditText
    private lateinit var btnSend: View
    private lateinit var pbLoading: ProgressBar
    private lateinit var btnClose: View

    private lateinit var adapter: ChatAdapter
    private lateinit var markwon: io.noties.markwon.Markwon

    companion object {
        // Lưu lịch sử tin nhắn trong Session để khi đóng/mở lại vẫn còn
        private val sessionMessages = mutableListOf<ChatMessage>(
            ChatMessage("assistant", "Xin chào! Sên đã sẵn sàng hỗ trợ bạn. Bạn cần tra cứu thông tin gì hôm nay?")
        )
    }

    override fun onCreateDialog(savedInstanceState: Bundle?): Dialog {
        val dialog = super.onCreateDialog(savedInstanceState) as BottomSheetDialog
        dialog.setOnShowListener {
            val bottomSheet = dialog.findViewById<View>(com.google.android.material.R.id.design_bottom_sheet)
            bottomSheet?.let {
                val behavior = BottomSheetBehavior.from(it)
                // Thiết lập chiều cao khoảng 80% màn hình
                val displayMetrics = requireContext().resources.displayMetrics
                it.layoutParams.height = (displayMetrics.heightPixels * 0.8).toInt()
                behavior.state = BottomSheetBehavior.STATE_EXPANDED
                behavior.peekHeight = (displayMetrics.heightPixels * 0.8).toInt()
                behavior.isHideable = true
            }
        }
        return dialog
    }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View? {
        return inflater.inflate(R.layout.layout_ai_chat_bottom_sheet, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        markwon = io.noties.markwon.Markwon.create(requireContext())

        rvChat = view.findViewById(R.id.rv_chat)
        etMessage = view.findViewById(R.id.et_message)
        btnSend = view.findViewById(R.id.btn_send)
        pbLoading = view.findViewById(R.id.pb_loading)
        btnClose = view.findViewById(R.id.btn_close)

        adapter = ChatAdapter(sessionMessages)
        rvChat.layoutManager = LinearLayoutManager(context).apply {
            stackFromEnd = true
        }
        rvChat.adapter = adapter

        btnClose.setOnClickListener { dismiss() }
        btnSend.setOnClickListener { sendMessage() }
    }

    private fun sendMessage() {
        val text = etMessage.text.toString().trim()
        if (text.isEmpty() || pbLoading.visibility == View.VISIBLE) return

        etMessage.text.clear()
        addMessage(ChatMessage("user", text))

        pbLoading.visibility = View.VISIBLE
        btnSend.isEnabled = false

        lifecycleScope.launch {
            try {
                val api = ApiClient.create(requireContext())
                
                // GIỚI HẠN TOKEN: Chỉ lấy 10 tin nhắn gần nhất làm history
                val historyLimit = 10
                val history = sessionMessages.takeLast(historyLimit + 1).dropLast(1).map { 
                    mapOf("role" to (if (it.role == "assistant") "model" else "user"), 
                          "parts" to listOf(mapOf("text" to it.content)))
                }

                val req = mapOf(
                    "message" to text,
                    "history" to history
                )

                val response = api.aiChat(req)
                val reply = response["reply"] ?: "Xin lỗi, tớ đang gặp chút trục trặc."
                
                addMessage(ChatMessage("assistant", reply))
            } catch (e: Exception) {
                addMessage(ChatMessage("assistant", "❌ Lỗi kết nối: ${e.message}"))
            } finally {
                pbLoading.visibility = View.GONE
                btnSend.isEnabled = true
            }
        }
    }

    private fun addMessage(msg: ChatMessage) {
        sessionMessages.add(msg)
        adapter.notifyItemInserted(sessionMessages.size - 1)
        rvChat.scrollToPosition(sessionMessages.size - 1)
    }

    data class ChatMessage(val role: String, val content: String)

    inner class ChatAdapter(private val list: List<ChatMessage>) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {
        override fun getItemViewType(position: Int) = if (list[position].role == "assistant") 1 else 2

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
            val layout = if (viewType == 1) R.layout.item_chat_assistant else R.layout.item_chat_user
            val v = LayoutInflater.from(parent.context).inflate(layout, parent, false)
            return object : RecyclerView.ViewHolder(v) {}
        }

        override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
            val msg = list[position]
            val tv = holder.itemView.findViewById<TextView>(R.id.tv_content)
            if (msg.role == "assistant") {
                markwon.setMarkdown(tv, msg.content)
            } else {
                tv.text = msg.content
            }
        }

        override fun getItemCount() = list.size
    }
}
