/**
 * Assistant API Client
 * 
 * Functions for interacting with the AI-powered learning assistant.
 * Provides conversational AI features backed by your personal knowledge base.
 * 
 * ## Use Cases
 * - **Knowledge Q&A**: Ask questions and get answers from your knowledge base
 * - **Concept Explanations**: Get AI-generated explanations of saved concepts
 * - **Study Recommendations**: Personalized suggestions for what to study next
 * - **Quiz Generation**: Auto-generate quizzes on specific topics
 * - **Conversation History**: Persistent chat threads for ongoing discussions
 * 
 * ## AI Features
 * - **RAG (Retrieval-Augmented Generation)**: Responses grounded in your notes
 * - **Source Citations**: See which notes informed each response
 * - **Multi-turn Conversations**: Context-aware follow-up questions
 * - **Adaptive Explanations**: Choose simple, detailed, or ELI5 styles
 * 
 * ## Conversation Model
 * ```
 * User Message → Knowledge Search → LLM + Context → Response + Sources
 *      ↓                                              ↓
 * Conversation History                         Source References
 * ```
 * 
 * ## Related APIs
 * - `knowledgeApi` - The graph database powering knowledge retrieval
 * - `vaultApi` - Source notes referenced in responses
 * - `practiceApi` - Generated quizzes feed into practice sessions
 * 
 * @see knowledgeApi - For direct graph queries
 * @see reviewApi - For spaced repetition of AI-suggested content
 */

import { typedApi } from './typed-client'

export const assistantApi = {
  /**
   * Chat with the AI assistant (simplified interface for Assistant page)
   * @param {string} message - User message content
   * @param {Array} messages - Previous messages (for context, not currently used by backend)
   * @param {string} [model] - Preferred model (not currently used by backend)
   * @returns {Promise<{content: string, sources?: Array}>} Response with content and sources
   */
  chat: async (message, _messages = [], _model = null) => {
    const response = await typedApi.POST('/api/assistant/chat', {
      body: { message }
    })
    // Transform backend response format to match frontend expectations
    return {
      content: response.data.response,
      sources: response.data.sources || [],
      conversationId: response.data.conversation_id,
    }
  },
  /**
   * Send a message to the AI assistant and get a response
   * @param {Object} data - Message data
   * @param {string|null} data.conversationId - Conversation ID (null to start new conversation)
   * @param {string} data.message - User message content
   * @returns {Promise<{conversation_id: string, response: string, sources?: Array<{id: string, title: string, relevance: number}>}>} Assistant response with optional source references
   */
  sendMessage: ({ conversationId, message }) => 
    typedApi.POST('/api/assistant/chat', {
      body: {
        conversation_id: conversationId,
        message,
      }
    }).then(r => r.data),

  /**
   * Get paginated list of all conversations
   * @param {Object} [options] - Query options
   * @param {number} [options.limit=20] - Maximum number of conversations to return
   * @param {number} [options.offset=0] - Number of conversations to skip for pagination
   * @returns {Promise<{conversations: Array<{id: string, title: string, created_at: string, updated_at: string, message_count: number}>, total: number}>} List of conversations
   */
  getConversations: ({ limit = 20, offset = 0 } = {}) => 
    typedApi.GET('/api/assistant/conversations', { 
      params: { query: { limit, offset } } 
    }).then(r => r.data),

  /**
   * Get a specific conversation with all its messages
   * @param {string} conversationId - Unique conversation identifier
   * @returns {Promise<{id: string, title: string, created_at: string, messages: Array<{id: string, role: 'user'|'assistant', content: string, timestamp: string}>}>} Full conversation with messages
   */
  getConversation: (conversationId) => 
    typedApi.GET('/api/assistant/conversations/{conversation_id}', {
      params: { path: { conversation_id: conversationId } }
    }).then(r => r.data),

  /**
   * Delete a conversation and all its messages
   * @param {string} conversationId - Unique conversation identifier
   * @returns {Promise<{success: boolean, deleted_id: string}>} Deletion confirmation
   */
  deleteConversation: (conversationId) => 
    typedApi.DELETE('/api/assistant/conversations/{conversation_id}', {
      params: { path: { conversation_id: conversationId } }
    }).then(r => r.data),

  /**
   * Get AI-generated prompt suggestions based on current knowledge base
   * @returns {Promise<{suggestions: Array<{text: string, category: string, topic_id?: string}>}>} List of suggested prompts
   */
  getSuggestions: () => 
    typedApi.GET('/api/assistant/suggestions').then(r => r.data),

  /**
   * Search knowledge base for content relevant to a query
   * @param {string} query - Search query string
   * @returns {Promise<{results: Array<{id: string, title: string, snippet: string, score: number, type: string}>}>} Search results with relevance scores
   */
  searchKnowledge: (query) => 
    typedApi.GET('/api/assistant/search', { 
      params: { query: { q: query } } 
    }).then(r => r.data),

  /**
   * Get personalized study recommendations based on learning history
   * @returns {Promise<{recommendations: Array<{topic_id: string, topic_name: string, reason: string, priority: 'high'|'medium'|'low'}>}>} Prioritized study recommendations
   */
  getRecommendations: () => 
    typedApi.GET('/api/assistant/recommendations').then(r => r.data),

  /**
   * Generate a quiz on a specific topic
   * @param {Object} params - Quiz parameters
   * @param {string} params.topicId - Topic ID to generate quiz for
   * @param {number} [params.count=5] - Number of questions to generate
   * @returns {Promise<{quiz_id: string, topic: string, questions: Array<{id: string, question: string, options?: Array<string>, type: 'multiple_choice'|'free_response'}>}>} Generated quiz
   */
  generateQuiz: ({ topicId, count = 5 }) => 
    typedApi.POST('/api/assistant/quiz', {
      body: {
        topic_id: topicId,
        question_count: count,
      }
    }).then(r => r.data),

  /**
   * Get an AI-generated explanation of a concept
   * @param {string} conceptId - Concept identifier to explain
   * @param {string} [style='detailed'] - Explanation style: 'simple', 'detailed', or 'eli5' (explain like I'm 5)
   * @returns {Promise<{concept: string, explanation: string, examples?: Array<string>, related_concepts?: Array<{id: string, name: string}>}>} Concept explanation
   */
  explainConcept: (conceptId, style = 'detailed') => 
    typedApi.GET('/api/assistant/explain/{concept_id}', {
      params: { path: { concept_id: conceptId }, query: { style } },
    }).then(r => r.data),

  /**
   * Clear conversation history
   * @param {string} [conversationId] - Conversation ID to clear (omit to clear all conversations)
   * @returns {Promise<{success: boolean, cleared_count: number}>} Deletion confirmation
   */
  clearHistory: (conversationId) => {
    if (conversationId) {
      return typedApi.DELETE('/api/assistant/conversations/{conversation_id}/messages', {
        params: { path: { conversation_id: conversationId } }
      }).then(r => r.data)
    }
    return typedApi.DELETE('/api/assistant/conversations').then(r => r.data)
  },

  /**
   * Rename a conversation
   * @param {string} conversationId - Unique conversation identifier
   * @param {string} title - New title for the conversation
   * @returns {Promise<{id: string, title: string, updated_at: string}>} Updated conversation metadata
   */
  renameConversation: (conversationId, title) => 
    typedApi.PATCH('/api/assistant/conversations/{conversation_id}', {
      params: { path: { conversation_id: conversationId } },
      body: { title },
    }).then(r => r.data),
}

export default assistantApi
