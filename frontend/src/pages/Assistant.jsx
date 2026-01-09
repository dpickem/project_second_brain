/**
 * Assistant Page
 * 
 * AI chat interface for knowledge questions.
 */

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useMutation } from '@tanstack/react-query'
import { clsx } from 'clsx'
import ReactMarkdown from 'react-markdown'
import toast from 'react-hot-toast'
import { Button, Badge } from '../components/common'
import { assistantApi } from '../api/assistant'
import { useSettingsStore } from '../stores'
import { fadeInUp, staggerContainer } from '../utils/animations'

export function Assistant() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  
  const preferredModel = useSettingsStore((s) => s.preferredModel)

  // Chat mutation
  const chatMutation = useMutation({
    mutationFn: (message) => assistantApi.chat(message, messages, preferredModel),
    onSuccess: (response) => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.content,
        sources: response.sources,
        timestamp: new Date().toISOString(),
      }])
    },
    onError: () => {
      toast.error('Failed to get response')
      // Remove pending message
      setMessages(prev => prev.filter(m => !m.pending))
    },
  })

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Handle send
  const handleSend = () => {
    if (!input.trim() || chatMutation.isPending) return
    
    const userMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    }
    
    setMessages(prev => [...prev, userMessage])
    setInput('')
    
    chatMutation.mutate(input.trim())
  }

  // Handle key press
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Quick prompts
  const quickPrompts = [
    'What did I learn about React hooks?',
    'Summarize my notes on system design',
    'Quiz me on Python concepts',
    'What topics should I review today?',
  ]

  const handleQuickPrompt = (prompt) => {
    setInput(prompt)
    inputRef.current?.focus()
  }

  return (
    <div className="min-h-screen bg-bg-primary flex flex-col">
      {/* Header */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="border-b border-border-primary bg-bg-secondary px-6 py-4"
      >
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-3xl">🤖</span>
            <div>
              <h1 className="text-xl font-bold text-text-primary font-heading">
                Learning Assistant
              </h1>
              <p className="text-sm text-text-secondary">
                Ask questions about your knowledge base
              </p>
            </div>
          </div>
          <Badge variant="info">{preferredModel || 'Gemini 3 Flash'}</Badge>
        </div>
      </motion.div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              animate="show"
              className="py-12"
            >
              {/* Welcome */}
              <motion.div variants={fadeInUp} className="text-center mb-8">
                <span className="text-6xl block mb-4">🧠</span>
                <h2 className="text-2xl font-bold text-text-primary font-heading mb-2">
                  How can I help you learn today?
                </h2>
                <p className="text-text-secondary max-w-md mx-auto">
                  I can answer questions about your notes, help you study, 
                  or explain concepts from your knowledge base.
                </p>
              </motion.div>

              {/* Quick prompts */}
              <motion.div variants={fadeInUp} className="max-w-2xl mx-auto">
                <p className="text-sm text-text-muted text-center mb-4">
                  Try asking:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {quickPrompts.map((prompt, index) => (
                    <button
                      key={index}
                      onClick={() => handleQuickPrompt(prompt)}
                      className="p-4 text-left rounded-xl bg-bg-secondary border border-border-primary hover:border-indigo-500/30 hover:bg-bg-hover transition-all"
                    >
                      <span className="text-sm text-text-primary">{prompt}</span>
                    </button>
                  ))}
                </div>
              </motion.div>
            </motion.div>
          ) : (
            <AnimatePresence>
              {messages.map((message, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className={clsx(
                    'flex gap-4',
                    message.role === 'user' && 'justify-end'
                  )}
                >
                  {message.role === 'assistant' && (
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                      <span className="text-white text-lg">🤖</span>
                    </div>
                  )}
                  
                  <div className={clsx(
                    'max-w-[80%] rounded-2xl px-5 py-4',
                    message.role === 'user'
                      ? 'bg-indigo-600 text-white'
                      : 'bg-bg-elevated border border-border-primary'
                  )}>
                    {message.role === 'assistant' ? (
                      <div className="prose prose-invert prose-sm max-w-none">
                        <ReactMarkdown>{message.content}</ReactMarkdown>
                        
                        {/* Sources */}
                        {message.sources?.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-border-primary">
                            <p className="text-xs text-text-muted mb-2">Sources:</p>
                            <div className="flex flex-wrap gap-2">
                              {message.sources.map((source, i) => (
                                <Badge key={i} size="xs" variant="default">
                                  📄 {source.title}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm">{message.content}</p>
                    )}
                  </div>

                  {message.role === 'user' && (
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-pink-500 to-orange-500 flex items-center justify-center flex-shrink-0">
                      <span className="text-white text-lg">👤</span>
                    </div>
                  )}
                </motion.div>
              ))}
              
              {/* Loading indicator */}
              {chatMutation.isPending && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex gap-4"
                >
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                    <span className="text-white text-lg">🤖</span>
                  </div>
                  <div className="bg-bg-elevated border border-border-primary rounded-2xl px-5 py-4">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" />
                      <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                      <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="border-t border-border-primary bg-bg-secondary p-4"
      >
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about your knowledge..."
                rows={1}
                className={clsx(
                  'w-full px-4 py-3 rounded-xl resize-none',
                  'bg-bg-primary border border-border-primary',
                  'text-text-primary placeholder:text-text-muted',
                  'focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500',
                  'transition-all'
                )}
                style={{ minHeight: '48px', maxHeight: '200px' }}
              />
            </div>
            <Button
              onClick={handleSend}
              disabled={!input.trim() || chatMutation.isPending}
              loading={chatMutation.isPending}
              className="h-12 px-6"
            >
              Send
            </Button>
          </div>
          <p className="text-xs text-text-muted mt-2 text-center">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </motion.div>
    </div>
  )
}

export default Assistant
