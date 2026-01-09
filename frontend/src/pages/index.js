/**
 * Pages Barrel Export
 * 
 * A barrel export re-exports modules from multiple files in a directory,
 * allowing consumers to import from a single entry point:
 * 
 *   import { Dashboard, Settings } from './pages'
 * 
 * Instead of:
 * 
 *   import { Dashboard } from './pages/Dashboard'
 *   import { Settings } from './pages/Settings'
 */

export { Dashboard } from './Dashboard'
export { Knowledge } from './Knowledge'
export { PracticeSession } from './PracticeSession'
export { ReviewQueue } from './ReviewQueue'
export { Analytics } from './Analytics'
export { Assistant } from './Assistant'
export { Settings } from './Settings'
