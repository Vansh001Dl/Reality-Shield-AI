import React, { useEffect, useRef, useState } from 'react';
import { api } from '../../services/api';

function SafetyChat({ recordingAnalysis, dashboardData }) {
  const sessionId = 'dashboard-user';
  const initialMessage = { role: 'assistant', text: recordingAnalysis ? 'Ask about this video, its risk, alerts, or routes.' : 'Upload a road video to analyze it. You can also ask general road-safety questions.' };
  const suggestedPrompts = recordingAnalysis
    ? ['Why is the risk high here?', 'Which factors matter most?', 'Suggest a safer route', 'Summarize this video']
    : ['What can you analyze?', 'How do I start an analysis?'];
  const [messages, setMessages] = useState([initialMessage]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [assistantMode, setAssistantMode] = useState('Copilot');
  const messagesRef = useRef(null);

  useEffect(() => {
    const list = messagesRef.current;
    if (list) list.scrollTo({ top: list.scrollHeight, behavior: 'smooth' });
  }, [messages, busy]);

  const sendMessage = async (eventOrMessage) => {
    const fromSuggestion = typeof eventOrMessage === 'string';
    if (!fromSuggestion) eventOrMessage.preventDefault();
    const message = fromSuggestion ? eventOrMessage : input.trim();
    if (!message || busy) return;
    setInput('');
    setMessages((current) => [...current, { role: 'user', text: message }]);
    setBusy(true);
    try {
      const { data } = await api.post('/api/chat/message', {
        session_id: sessionId,
        message,
        context: {
          video: recordingAnalysis?.fileName,
          location: recordingAnalysis?.location?.label,
          latitude: recordingAnalysis?.location?.latitude,
          longitude: recordingAnalysis?.location?.longitude,
          detections: recordingAnalysis?.counts,
          total_detections: recordingAnalysis?.detectionsCount,
          vehicles: recordingAnalysis?.vehicleCount,
          pedestrians: recordingAnalysis?.pedestrianCount,
          potholes: recordingAnalysis?.potholeCount,
          risk: dashboardData?.risk,
          route: dashboardData?.route,
        },
      });
      setAssistantMode(data.mode === 'context' ? 'Dashboard data mode' : `${data.mode || 'AI'} connected`);
      setMessages((current) => [...current, { role: 'assistant', text: data.reply }]);
    } catch {
      setAssistantMode('Unavailable');
      setMessages((current) => [...current, { role: 'assistant', text: 'Chat service is unavailable. Please check that the backend is running.' }]);
    } finally {
      setBusy(false);
    }
  };

  const resetConversation = async () => {
    if (busy) return;
    try {
      await api.post(`/api/chat/reset/${sessionId}`);
    } finally {
      setMessages([initialMessage]);
      setInput('');
    }
  };

  return (
    <section className="panel safety-chat">
      <div className="chat-header"><div><h2 className="card-title">Safety Copilot</h2><p>Ask about road safety, risk analysis, routes, or video data.</p></div><div className="chat-header-actions"><span className={`chat-status ${assistantMode === 'Unavailable' || assistantMode.startsWith('Offline') ? 'chat-status-offline' : ''} ${assistantMode === 'Dashboard data mode' ? 'chat-status-local' : ''}`}><i /> {busy ? 'Thinking' : assistantMode}</span><button type="button" className="chat-reset" onClick={resetConversation} disabled={busy} title="Start a new conversation">Reset chat</button></div></div>
      <div className="chat-messages" ref={messagesRef} aria-live="polite" aria-label="Conversation">
        {messages.map((message, index) => <div className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>{message.text}</div>)}
        {busy && <div className="chat-message assistant">Thinking...</div>}
      </div>
      {messages.length === 1 && <div className="copilot-suggestions">{suggestedPrompts.map((prompt) => <button type="button" key={prompt} onClick={() => sendMessage(prompt)} disabled={busy}><span>⌕</span>{prompt}</button>)}</div>}
      <form className="chat-form" onSubmit={sendMessage}>
        <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Type your question..." aria-label="Ask safety copilot" disabled={busy} />
        <button type="submit" disabled={busy || !input.trim()} aria-label="Send message">➤</button>
      </form>
    </section>
  );
}

export default SafetyChat;
