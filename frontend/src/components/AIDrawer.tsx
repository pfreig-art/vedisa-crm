import { useState, useEffect, useRef } from 'react'
import { useAIStore } from '../store/aiStore'
import { X, Send, Bot, User, Trash2, ChevronDown } from 'lucide-react'

export default function AIDrawer() {
  const {
    isOpen,
    closeDrawer,
    messages,
    isLoading,
    providers,
    selectedProvider,
    setProvider,
    sendMessage,
    clearMessages,
    fetchProviders,
  } = useAIStore()

  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isOpen && providers.length === 0) {
      fetchProviders()
    }
  }, [isOpen])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    const prompt = input.trim()
    setInput('')
    await sendMessage(prompt)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!isOpen) return null

  return (
    <>
      {/* Overlay */}
      <div
        className="drawer-overlay"
        onClick={closeDrawer}
      />

      {/* Panel */}
      <div className="drawer-panel flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b bg-gray-900 text-white">
          <div className="flex items-center gap-2">
            <Bot size={20} className="text-brand-500" />
            <h2 className="font-semibold">Asistente IA</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={clearMessages}
              className="p-1 hover:text-red-400 transition-colors"
              title="Limpiar chat"
            >
              <Trash2 size={16} />
            </button>
            <button
              onClick={closeDrawer}
              className="p-1 hover:text-gray-300 transition-colors"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Provider selector */}
        {providers.length > 0 && (
          <div className="px-4 py-2 border-b bg-gray-50">
            <div className="relative">
              <select
                value={selectedProvider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full appearance-none bg-white border border-gray-300 rounded-md px-3 py-1.5 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {providers.map((p) => (
                  <option key={p.id} value={p.id} disabled={!p.is_available}>
                    {p.name} ({p.model}){!p.is_available ? ' - no disponible' : ''}
                  </option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-2 top-2.5 text-gray-400 pointer-events-none" />
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-400 mt-8">
              <Bot size={40} className="mx-auto mb-2 text-gray-300" />
              <p className="text-sm">Pregunta algo sobre tus datos CRM</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-2 ${
                msg.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {msg.role === 'assistant' && (
                <div className="w-7 h-7 rounded-full bg-brand-500 flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot size={14} className="text-white" />
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${
                  msg.role === 'user'
                    ? 'bg-brand-600 text-white rounded-tr-none'
                    : 'bg-gray-100 text-gray-800 rounded-tl-none'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                <span className="text-xs opacity-60 mt-1 block">
                  {new Date(msg.timestamp).toLocaleTimeString('es-ES', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
              {msg.role === 'user' && (
                <div className="w-7 h-7 rounded-full bg-gray-600 flex items-center justify-center flex-shrink-0 mt-1">
                  <User size={14} className="text-white" />
                </div>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="flex gap-2 justify-start">
              <div className="w-7 h-7 rounded-full bg-brand-500 flex items-center justify-center flex-shrink-0">
                <Bot size={14} className="text-white" />
              </div>
              <div className="bg-gray-100 rounded-2xl rounded-tl-none px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t bg-white">
          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribe tu pregunta..."
              rows={2}
              className="flex-1 resize-none border border-gray-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="self-end p-2 bg-brand-600 text-white rounded-xl hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
