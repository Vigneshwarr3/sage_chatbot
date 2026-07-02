import { useState, useEffect, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import "./App.css";

// Relative path: proxied to the backend by Vite (dev) or nginx (Docker/prod).
const API_BASE = "";

const SUGGESTIONS = [
  "My internet is not connecting",
  "What is DNS?",
  "WiFi keeps disconnecting",
  "How to find my IP address?",
  "Router not working",
  "How to flush DNS cache?",
];

function App() {
  const [sessionId]         = useState(() => uuidv4());
  const [messages, setMessages]         = useState([]);
  const [input, setInput]               = useState("");
  const [loading, setLoading]           = useState(false);

  // Self-learning state
  const [learnMode, setLearnMode]       = useState(false);      // show learn panel?
  const [learnQuestion, setLearnQuestion] = useState("");       // the question user solved
  const [learnSolution, setLearnSolution] = useState("");       // what user actually did
  const [learnLoading, setLearnLoading] = useState(false);
  const [learnSuccess, setLearnSuccess] = useState(false);

  // Track last bot question so we can pre-fill learnQuestion
  const [lastBotQuestion, setLastBotQuestion] = useState("");

  const bottomRef = useRef(null);

  useEffect(() => {
    // Welcome message
    setMessages([
      {
        role: "bot",
        text: "Hi! I'm Sage 👋 Your networking assistant. Ask me anything about WiFi, DNS, routers, or connectivity issues. I also learn from solutions that work for you!",
      },
    ]);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, learnMode]);

  // ── Send message to /chat ────────────────────────────────────────────────
  const sendMessage = async (text) => {
    const question = text || input.trim();
    if (!question || loading) return;

    setInput("");
    setLearnMode(false);
    setLearnSuccess(false);

    const userMsg = { role: "user", text: question };
    setMessages((prev) => [...prev, userMsg]);
    setLastBotQuestion(question);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question, session_id: sessionId }),
      });
      const data = await res.json();
      const botMsg = {
        role: "bot",
        text: data.answer || "Sorry, I couldn't get a response.",
        intent: data.intent,
        question: question,   // remember which question this answers
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "Connection error. Is the Flask server running?" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // ── Open learn panel for a specific bot message ───────────────────────────
  const openLearnPanel = (question) => {
    setLearnQuestion(question || lastBotQuestion);
    setLearnSolution("");
    setLearnSuccess(false);
    setLearnMode(true);
  };

  // ── Submit solution to /learn ─────────────────────────────────────────────
  const submitLearn = async () => {
    if (!learnSolution.trim() || learnLoading) return;
    setLearnLoading(true);

    try {
      const res = await fetch(`${API_BASE}/learn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id:        sessionId,
          original_question: learnQuestion,
          user_solution:     learnSolution.trim(),
        }),
      });
      const data = await res.json();
      if (data.saved) {
        setLearnSuccess(true);
        // Add a system message in the chat
        setMessages((prev) => [
          ...prev,
          {
            role: "system",
            text: `✅ Got it! I've learned: "${learnSolution.trim()}" — I'll include this in future answers about similar issues.`,
          },
        ]);
        setTimeout(() => {
          setLearnMode(false);
          setLearnSuccess(false);
        }, 2500);
      }
    } catch {
      alert("Failed to save. Is the server running?");
    } finally {
      setLearnLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-container">
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="chat-header">
        <div className="header-left">
          <div className="avatar">N</div>
          <div>
            <div className="bot-name">Sage</div>
            <div className="bot-status">● Online</div>
          </div>
        </div>
      </div>

      {/* ── Messages ───────────────────────────────────────────── */}
      <div className="messages-area">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message-wrapper ${msg.role}`}>
            {msg.role === "bot" && <div className="avatar small">N</div>}

            <div className={`bubble ${msg.role}`}>
              <p>{msg.text}</p>

              {/* "I solved it differently!" button — only on bot RAG answers */}
              {msg.role === "bot" && msg.intent === "rag" && (
                <button
                  className="solved-btn"
                  onClick={() => openLearnPanel(msg.question)}
                  title="Tell Sage what actually solved your problem"
                >
                  ✅ I solved it differently — teach Sage!
                </button>
              )}
            </div>

            {msg.role === "system" && (
              <div className="system-msg">{msg.text}</div>
            )}
          </div>
        ))}

        {loading && (
          <div className="message-wrapper bot">
            <div className="avatar small">N</div>
            <div className="bubble bot typing">
              <span /><span /><span />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Suggestion chips ───────────────────────────────────── */}
      {messages.length <= 1 && (
        <div className="suggestions">
          {SUGGESTIONS.map((s, i) => (
            <button key={i} className="chip" onClick={() => sendMessage(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      {/* ── Self-Learning Panel ────────────────────────────────── */}
      {learnMode && (
        <div className="learn-panel">
          <div className="learn-header">
            <span>🧠 Teach Sage what worked</span>
            <button className="close-btn" onClick={() => setLearnMode(false)}>✕</button>
          </div>
          <div className="learn-body">
            <label>Your original question:</label>
            <input
              type="text"
              value={learnQuestion}
              onChange={(e) => setLearnQuestion(e.target.value)}
              className="learn-input"
              placeholder="What was your problem?"
            />
            <label>What did you do that solved it?</label>
            <textarea
              value={learnSolution}
              onChange={(e) => setLearnSolution(e.target.value)}
              className="learn-textarea"
              placeholder="e.g. I restarted the modem by unplugging it for 30 seconds and it worked..."
              rows={3}
            />
            <button
              className="learn-submit-btn"
              onClick={submitLearn}
              disabled={learnLoading || !learnSolution.trim()}
            >
              {learnLoading ? "Saving..." : learnSuccess ? "✅ Saved!" : "Save & Teach Sage"}
            </button>
          </div>
        </div>
      )}

      {/* ── Input bar ──────────────────────────────────────────── */}
      <div className="input-area">
        <textarea
          className="input-box"
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about networking…"
        />
        <button
          className="send-btn"
          onClick={() => sendMessage()}
          disabled={loading || !input.trim()}
        >
          ➤
        </button>
      </div>
    </div>
  );
}

export default App;
