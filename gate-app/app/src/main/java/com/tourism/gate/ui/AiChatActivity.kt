package com.tourism.gate.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.tourism.gate.R
import com.tourism.gate.data.api.ApiClient
import kotlinx.coroutines.launch

class AiChatActivity : AppCompatActivity() {

    private lateinit var rvChat: RecyclerView
    private lateinit var etMessage: EditText
    private lateinit var btnSend: TextView
    private lateinit var pbLoading: ProgressBar
    private lateinit var btnBack: TextView

    private val messages = mutableListOf<ChatMessage>()
    private lateinit var adapter: ChatAdapter
    private lateinit var markwon: io.noties.markwon.Markwon

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_ai_chat)

        markwon = io.noties.markwon.Markwon.create(this)

        rvChat = findViewById(R.id.rv_chat)
        etMessage = findViewById(R.id.et_message)
        btnSend = findViewById(R.id.btn_send)
        pbLoading = findViewById(R.id.pb_loading)
        btnBack = findViewById(R.id.btn_back)

        adapter = ChatAdapter(messages)
        rvChat.layoutManager = LinearLayoutManager(this).apply {
            stackFromEnd = true
        }
        rvChat.adapter = adapter

        btnBack.setOnClickListener { finish() }
        btnSend.setOnClickListener { sendMessage() }

        // Mặc định chào mừng
        addMessage(ChatMessage("assistant", "Xin chào! Tôi là trợ lý Tourism Gate. Tôi có thể hỗ trợ gì cho bạn về các chuyến đi hoặc vé của bạn?"))
    }

    private fun sendMessage() {
        val text = etMessage.text.toString().trim()
        if (text.isEmpty()) return

        etMessage.text.clear()
        addMessage(ChatMessage("user", text))

        pbLoading.visibility = View.VISIBLE
        btnSend.isEnabled = false

        lifecycleScope.launch {
            try {
                val api = ApiClient.create(this@AiChatActivity)
                
                // Convert history to Gemini format if needed, 
                // but for simplicity we'll just send current message for now.
                // In a real app, you'd pass the full list.
                val history = messages.dropLast(1).map { 
                    mapOf("role" to (if (it.role == "assistant") "model" else "user"), 
                          "parts" to listOf(mapOf("text" to it.content)))
                }

                val req = mapOf(
                    "message" to text,
                    "history" to history
                )

                val response = api.aiChat(req)
                val reply = response["reply"] ?: "Xin lỗi, tôi không nhận được phản hồi."
                
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
        messages.add(msg)
        adapter.notifyItemInserted(messages.size - 1)
        rvChat.scrollToPosition(messages.size - 1)
    }

    // ── Adapter & ViewHolders ─────────────────────────────────

    data class ChatMessage(val role: String, val content: String)

    inner class ChatAdapter(private val list: List<ChatMessage>) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {
        private val TYPE_ASSISTANT = 1
        private val TYPE_USER = 2

        override fun getItemViewType(position: Int) = if (list[position].role == "assistant") TYPE_ASSISTANT else TYPE_USER

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
            val layout = if (viewType == TYPE_ASSISTANT) R.layout.item_chat_assistant else R.layout.item_chat_user
            val view = LayoutInflater.from(parent.context).inflate(layout, parent, false)
            return ChatViewHolder(view)
        }

        override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
            val msg = list[position]
            val tv = (holder as ChatViewHolder).tvContent
            if (msg.role == "assistant") {
                markwon.setMarkdown(tv, msg.content)
            } else {
                tv.text = msg.content
            }
        }

        override fun getItemCount() = list.size

        inner class ChatViewHolder(v: View) : RecyclerView.ViewHolder(v) {
            val tvContent: TextView = v.findViewById(R.id.tv_content)
        }
    }
}
