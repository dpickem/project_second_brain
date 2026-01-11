/**
 * ResponseInput Component
 * 
 * Adaptive input based on exercise type (text or code).
 */

import { useState, useRef, useEffect } from 'react'
import { clsx } from 'clsx'
import Editor from '@monaco-editor/react'
import { Textarea, Button, Spinner } from '../common'
import { ExerciseType, isCodeExercise } from '../../constants/enums.generated'

const placeholders = {
  [ExerciseType.FREE_RECALL]: 'Write everything you can recall about this topic...',
  [ExerciseType.SELF_EXPLAIN]: 'Explain the concept in your own words...',
  [ExerciseType.TEACH_BACK]: 'Explain this as if teaching someone new to the topic...',
  [ExerciseType.WORKED_EXAMPLE]: 'Work through this problem step by step...',
  [ExerciseType.CODE_DEBUG]: 'Fix the code and explain your changes...',
  [ExerciseType.CODE_COMPLETE]: 'Complete the code implementation...',
  [ExerciseType.CODE_IMPLEMENT]: 'Write your implementation here...',
  [ExerciseType.CODE_REFACTOR]: 'Refactor this code to improve it...',
  [ExerciseType.CODE_EXPLAIN]: 'Explain what this code does...',
}

export function ResponseInput({
  exerciseType,
  language = 'javascript',
  initialCode = '',
  value = '',
  onChange,
  onSubmit,
  isSubmitting = false,
  disabled = false,
  className,
}) {
  // Ensure we always have a string, never null/undefined
  const [localValue, setLocalValue] = useState(value || initialCode || '')
  const textareaRef = useRef(null)
  const isCode = isCodeExercise(exerciseType)

  // Sync with external value
  useEffect(() => {
    setLocalValue(value || initialCode || '')
  }, [value, initialCode])

  const handleChange = (newValue) => {
    setLocalValue(newValue)
    onChange?.(newValue)
  }

  const handleKeyDown = (e) => {
    // Submit on Cmd/Ctrl + Enter
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && (localValue || '').trim()) {
      e.preventDefault()
      onSubmit?.(localValue)
    }
  }

  const placeholder = placeholders[exerciseType] || 'Enter your response...'

  return (
    <div className={clsx('space-y-4', className)}>
      {isCode ? (
        <CodeEditor
          language={language}
          value={localValue}
          onChange={handleChange}
          onSubmit={() => onSubmit?.(localValue)}
          disabled={disabled || isSubmitting}
        />
      ) : (
        <Textarea
          ref={textareaRef}
          value={localValue}
          onChange={(e) => handleChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={8}
          disabled={disabled || isSubmitting}
          className="resize-y min-h-[200px]"
        />
      )}

      {/* Footer */}
      <div className="flex items-center justify-between">
        {/* Character count / hints */}
        <div className="flex items-center gap-4 text-sm text-text-muted">
          {!isCode && (
            <span>{(localValue || '').length} characters</span>
          )}
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-xs">
              {navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'}
            </kbd>
            <span>+</span>
            <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-xs">↵</kbd>
            <span>to submit</span>
          </span>
        </div>

        {/* Submit button */}
        <Button
          onClick={() => onSubmit?.(localValue)}
          disabled={!(localValue || '').trim() || isSubmitting}
          loading={isSubmitting}
        >
          Submit Answer
        </Button>
      </div>
    </div>
  )
}

// Code Editor component
function CodeEditor({ language, value, onChange, onSubmit, disabled }) {
  const editorRef = useRef(null)

  const handleEditorMount = (editor) => {
    editorRef.current = editor
    
    // Add Cmd/Ctrl+Enter shortcut
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter,
      () => {
        if (value.trim()) {
          onSubmit?.()
        }
      }
    )
  }

  const languageMap = {
    javascript: 'javascript',
    typescript: 'typescript',
    python: 'python',
    java: 'java',
    cpp: 'cpp',
    c: 'c',
    go: 'go',
    rust: 'rust',
    sql: 'sql',
    html: 'html',
    css: 'css',
    json: 'json',
    markdown: 'markdown',
  }

  const monacoLanguage = languageMap[language] || 'plaintext'

  return (
    <div className="rounded-lg overflow-hidden border border-border-primary">
      {/* Language indicator */}
      <div className="flex items-center justify-between px-4 py-2 bg-bg-tertiary border-b border-border-primary">
        <span className="text-sm text-text-secondary font-mono">{language || 'Code'}</span>
        <button
          onClick={() => onChange?.('')}
          className="text-xs text-text-muted hover:text-text-secondary transition-colors"
        >
          Clear
        </button>
      </div>

      {/* Editor */}
      <Editor
        height="300px"
        language={monacoLanguage}
        value={value}
        onChange={onChange}
        onMount={handleEditorMount}
        theme="vs-dark"
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          fontFamily: 'JetBrains Mono, Fira Code, monospace',
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          wordWrap: 'on',
          padding: { top: 16, bottom: 16 },
          readOnly: disabled,
        }}
        loading={
          <div className="flex items-center justify-center h-[300px] bg-bg-tertiary">
            <Spinner size="lg" />
          </div>
        }
      />
    </div>
  )
}

// Import monaco for keyboard shortcuts
import * as monaco from 'monaco-editor'

export default ResponseInput
