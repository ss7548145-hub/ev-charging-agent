import React, { useState } from 'react';
import { sendChatMessage } from '../api';

export default function ChatWidget({ stationId }) {
  const [messages, setMessages] = useState([
    { role: 'agent', text: "Hello! I'm VoltIQ, your EV charging intelligence assistant. Ask me about charging congestion, optimal times, or savings!" }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async (queryText) => {
    const textToSend = queryText || input;
    if (!textToSend.trim()) return;

    const newMsgs = [...messages, { role: 'user', text: textToSend }];
    setMessages(newMsgs);
    setInput('');
    setLoading(true);

    try {
      const res = await sendChatMessage(textToSend, stationId);
      setMessages([...newMsgs, { role: 'agent', text: res.reply }]);
    } catch (err) {
      setMessages([...newMsgs, { role: 'agent', text: 'Error connecting to reasoning engine.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col h-[480px]">
      <div className="flex justify-between items-center pb-3 border-b border-slate-800 mb-4">
        <h3 className="text-md font-bold text-white flex items-center gap-2">
          <span>💬</span> VoltIQ AI Advisor
        </h3>
        <span className="text-xs text-cyan-400">Groq Reasoning</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-2">
        {messages.map((m, idx) => (
          <div key={idx} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
            <div
              className={`p-3 rounded-xl text-xs max-w-[85%] leading-relaxed ${
                m.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none'
                  : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-bl-none'
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading && <div className="text-xs text-slate-500 italic">Thinking with Groq reasoning engine...</div>}
      </div>

      <div className="flex flex-wrap gap-1.5 my-3">
        {['Why is station full at 6pm?', 'Cheapest charging hours?'].map((q, i) => (
          <button
            key={i}
            onClick={() => handleSend(q)}
            className="text-[10px] bg-slate-800 border border-slate-700 text-slate-300 px-2 py-1 rounded-full hover:border-cyan-400 transition"
          >
            {q}
          </button>
        ))}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask about charging trends..."
          className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
        />
        <button
          onClick={() => handleSend()}
          className="bg-cyan-500 text-black px-4 py-2 rounded-xl text-xs font-bold hover:bg-cyan-400 transition"
        >
          ➤
        </button>
      </div>
    </div>
  );
}
