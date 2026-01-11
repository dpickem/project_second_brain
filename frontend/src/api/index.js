/**
 * API Barrel Export
 * 
 * Central export for all API clients in the Second Brain application.
 * Import API modules from here for cleaner imports throughout the app.
 * 
 * ## Available APIs
 * 
 * | API           | Purpose                                        |
 * |---------------|------------------------------------------------|
 * | `apiClient`   | Base Axios client for custom requests          |
 * | `typedApi`    | OpenAPI-typed client (compile-time safety)     |
 * | `knowledgeApi`| Neo4j graph queries, relationships, topics     |
 * | `vaultApi`    | Obsidian vault notes, folders, sync            |
 * | `captureApi`  | Quick capture of text, URLs, files             |
 * | `analyticsApi`| Learning stats, mastery, streaks               |
 * | `reviewApi`   | Spaced repetition flashcard reviews            |
 * | `practiceApi` | Interactive practice sessions                  |
 * | `assistantApi`| AI chat, explanations, recommendations         |
 * 
 * ## Usage
 * ```js
 * // Import specific APIs
 * import { vaultApi, knowledgeApi } from '../api'
 * 
 * // Use in components
 * const notes = await vaultApi.getNotes()
 * const graph = await knowledgeApi.getGraph()
 * ```
 * 
 * ## Typed API Client (OpenAPI-backed)
 * ```js
 * // After running: npm run generate:api-types
 * import { typedApi, api } from '../api'
 * 
 * // Type-safe requests (catches typos at dev time)
 * const { data } = await api.knowledge.search({ query: 'transformers' })
 * ```
 * 
 * ## Helper Functions
 * - `createApiEndpoint(path)` - Create CRUD wrapper for fixed paths
 * - `createDynamicEndpoint(fn)` - Create CRUD wrapper for dynamic paths
 * - `buildQueryParams(obj)` - Build URLSearchParams from object
 * 
 * @module api
 */

export { apiClient, createApiEndpoint, createDynamicEndpoint, buildQueryParams } from './client'
export { typedApi, api, isOk, unwrap } from './typed-client'
export { knowledgeApi } from './knowledge'
export { vaultApi } from './vault'
export { captureApi } from './capture'
export { analyticsApi } from './analytics'
export { reviewApi } from './review'
export { practiceApi } from './practice'
export { assistantApi } from './assistant'
