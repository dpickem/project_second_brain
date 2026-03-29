/**
 * CapturePanel Component
 *
 * Tabbed container for all capture forms (Text, URL, File Upload).
 * Each tab shows the corresponding capture form.
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import PropTypes from 'prop-types'
import {
  DocumentTextIcon,
  LinkIcon,
  ArrowUpTrayIcon,
} from '@heroicons/react/24/outline'
import { Card } from '../common'
import { TextCaptureForm } from './TextCaptureForm'
import { UrlCaptureForm } from './UrlCaptureForm'
import { FileCaptureForm } from './FileCaptureForm'

const TABS = [
  { id: 'text', label: 'Text', icon: DocumentTextIcon },
  { id: 'url', label: 'URL', icon: LinkIcon },
  { id: 'file', label: 'File', icon: ArrowUpTrayIcon },
]

export function CapturePanel({ onCaptureSuccess, className }) {
  const [activeTab, setActiveTab] = useState('text')

  return (
    <Card className={clsx('', className)}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <span className="w-8 h-8 bg-indigo-600/20 rounded-lg flex items-center justify-center">
          <ArrowUpTrayIcon className="w-4 h-4 text-indigo-400" />
        </span>
        <h2 className="text-lg font-semibold text-text-primary font-heading">
          Capture Content
        </h2>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 p-1 bg-bg-tertiary rounded-lg" role="tablist">
        {TABS.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              aria-controls={`capture-panel-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-md text-sm font-medium',
                'transition-all duration-200',
                isActive
                  ? 'bg-bg-elevated text-text-primary shadow-sm'
                  : 'text-text-muted hover:text-text-secondary'
              )}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>

      {/* Tab panels */}
      <div>
        {activeTab === 'text' && (
          <div role="tabpanel" id="capture-panel-text">
            <TextCaptureForm onSuccess={onCaptureSuccess} />
          </div>
        )}
        {activeTab === 'url' && (
          <div role="tabpanel" id="capture-panel-url">
            <UrlCaptureForm onSuccess={onCaptureSuccess} />
          </div>
        )}
        {activeTab === 'file' && (
          <div role="tabpanel" id="capture-panel-file">
            <FileCaptureForm onSuccess={onCaptureSuccess} />
          </div>
        )}
      </div>
    </Card>
  )
}

CapturePanel.propTypes = {
  onCaptureSuccess: PropTypes.func,
  className: PropTypes.string,
}

export default CapturePanel
