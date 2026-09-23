import { useRef, useEffect, useState } from "react";
import { chatWithAgent, getChatHistory } from "./api";
import type { SavedChat } from "./api";
import "./ChatPanel.css";

interface Message {
  id: string;
  type: "user" | "assistant";
  text: string;
  toolsUsed?: string[];
  timestamp: Date;
}

const WELCOME: Message = {
  id: "welcome",
  type: "assistant",
  text: "Hi! I'm the Yale SOM course assistant. Ask me anything about courses, faculty, schedules, or course content.",
  toolsUsed: [],
  timestamp: new Date(),
};

// Each saved chat row holds one question and its reply
function toMessages(chat: SavedChat): Message[] {
  const timestamp = new Date(chat.created_at);
  return [
    { id: `user-${chat.id}`, type: "user", text: chat.user_message, timestamp },
    {
      id: `assistant-${chat.id}`,
      type: "assistant",
      text: chat.reply,
      toolsUsed: chat.tools_used,
      timestamp,
    },
  ];
}

function formatTime(date: Date) {
  const time = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (date.toDateString() === new Date().toDateString()) return time;
  return `${date.toLocaleDateString([], { month: "short", day: "numeric" })}, ${time}`;
}

export function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    getChatHistory()
      .then((chats) => setMessages([WELCOME, ...chats.flatMap(toMessages)]))
      .catch(() => {})
      .finally(() => setLoadingHistory(false));
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");

    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        type: "user",
        text: userMessage,
        timestamp: new Date(),
      },
    ]);

    setLoading(true);

    try {
      const response = await chatWithAgent(userMessage);
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          type: "assistant",
          text: response.reply,
          toolsUsed: response.tools_used,
          timestamp: new Date(),
        },
      ]);
    } catch (error) {
      const errorMsg =
        error instanceof Error ? error.message : "An error occurred";
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          type: "assistant",
          text: `Sorry, I encountered an error: ${errorMsg}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h2>Course Assistant</h2>
      </div>

      <div className="messages">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`message message-${msg.type}`}
          >
            <div className="message-content">
              <p>{msg.text}</p>
              {msg.toolsUsed && msg.toolsUsed.length > 0 && (
                <div className="tools-used">
                  <strong>Tools:</strong> {msg.toolsUsed.join(", ")}
                </div>
              )}
            </div>
            <span className="message-time">{formatTime(msg.timestamp)}</span>
          </div>
        ))}
        {loadingHistory && (
          <div className="message message-assistant loading">
            <div className="spinner"></div>
            <p>Loading your saved chats...</p>
          </div>
        )}
        {loading && (
          <div className="message message-assistant loading">
            <div className="spinner"></div>
            <p>Thinking...</p>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about courses, faculty, schedules..."
          disabled={loading || loadingHistory}
          className="chat-input"
        />
        <button type="submit" disabled={loading || !input.trim()} className="send-btn">
          {loading ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}
