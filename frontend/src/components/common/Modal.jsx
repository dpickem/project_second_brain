/**
 * Modal Component
 * 
 * Accessible modal dialog using Headless UI with Framer Motion animations.
 */

import { Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { clsx } from 'clsx'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { IconButton } from './Button'

const sizes = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
  '3xl': 'max-w-3xl',
  '4xl': 'max-w-4xl',
  full: 'max-w-[calc(100vw-2rem)]',
}

export function Modal({
  isOpen,
  onClose,
  title,
  description,
  size = 'md',
  showCloseButton = true,
  closeOnOverlayClick = true,
  children,
  footer,
  className,
}) {
  return (
    <Transition show={isOpen} as={Fragment}>
      <Dialog
        as="div"
        className="relative z-modal"
        onClose={closeOnOverlayClick ? onClose : () => {}}
      >
        {/* Backdrop */}
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" />
        </Transition.Child>

        {/* Modal container */}
        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel
                className={clsx(
                  'w-full transform overflow-hidden rounded-2xl',
                  'bg-bg-elevated border border-border-primary shadow-xl',
                  'text-left align-middle transition-all',
                  sizes[size],
                  className
                )}
              >
                {/* Header */}
                {(title || showCloseButton) && (
                  <div className="flex items-start justify-between p-6 pb-0">
                    <div className="flex-1 pr-4">
                      {title && (
                        <Dialog.Title
                          as="h3"
                          className="text-xl font-semibold text-text-primary font-heading"
                        >
                          {title}
                        </Dialog.Title>
                      )}
                      {description && (
                        <Dialog.Description className="mt-1 text-sm text-text-secondary">
                          {description}
                        </Dialog.Description>
                      )}
                    </div>
                    {showCloseButton && (
                      <IconButton
                        variant="ghost"
                        size="sm"
                        icon={<XMarkIcon />}
                        label="Close"
                        onClick={onClose}
                        className="flex-shrink-0 -mt-1 -mr-2"
                      />
                    )}
                  </div>
                )}

                {/* Content */}
                <div className="p-6">
                  {children}
                </div>

                {/* Footer */}
                {footer && (
                  <div className="flex items-center justify-end gap-3 px-6 py-4 bg-bg-secondary/50 border-t border-border-primary">
                    {footer}
                  </div>
                )}
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}

// Confirmation Modal - specialized for confirm/cancel dialogs
export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  description,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'danger', // 'danger' | 'primary' | 'warning'
  loading = false,
  children,
}) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      description={description}
      size="sm"
      footer={
        <>
          <button
            type="button"
            className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            onClick={onClose}
            disabled={loading}
          >
            {cancelText}
          </button>
          <button
            type="button"
            className={clsx(
              'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900',
              variant === 'danger' && 'bg-red-600 text-white hover:bg-red-500 focus-visible:ring-red-500',
              variant === 'primary' && 'bg-indigo-600 text-white hover:bg-indigo-500 focus-visible:ring-indigo-500',
              variant === 'warning' && 'bg-amber-600 text-white hover:bg-amber-500 focus-visible:ring-amber-500'
            )}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? 'Loading...' : confirmText}
          </button>
        </>
      }
    >
      {children}
    </Modal>
  )
}

// Drawer - slide-in panel variant
export function Drawer({
  isOpen,
  onClose,
  title,
  description,
  position = 'right', // 'left' | 'right'
  size = 'md',
  showCloseButton = true,
  children,
  footer,
}) {
  const drawerSizes = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
  }

  const positionClasses = {
    left: 'left-0',
    right: 'right-0',
  }

  const translateClasses = {
    left: { enter: '-translate-x-full', leave: '-translate-x-full' },
    right: { enter: 'translate-x-full', leave: 'translate-x-full' },
  }

  return (
    <Transition show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-modal" onClose={onClose}>
        {/* Backdrop */}
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" />
        </Transition.Child>

        {/* Drawer container */}
        <div className="fixed inset-0 overflow-hidden">
          <div className="absolute inset-0 overflow-hidden">
            <div className={clsx(
              'pointer-events-none fixed inset-y-0 flex max-w-full',
              positionClasses[position]
            )}>
              <Transition.Child
                as={Fragment}
                enter="transform transition ease-in-out duration-300"
                enterFrom={translateClasses[position].enter}
                enterTo="translate-x-0"
                leave="transform transition ease-in-out duration-200"
                leaveFrom="translate-x-0"
                leaveTo={translateClasses[position].leave}
              >
                <Dialog.Panel
                  className={clsx(
                    'pointer-events-auto w-screen',
                    drawerSizes[size]
                  )}
                >
                  <div className="flex h-full flex-col bg-bg-elevated border-l border-border-primary shadow-xl">
                    {/* Header */}
                    {(title || showCloseButton) && (
                      <div className="flex items-start justify-between px-6 py-5 border-b border-border-primary">
                        <div className="flex-1 pr-4">
                          {title && (
                            <Dialog.Title className="text-xl font-semibold text-text-primary font-heading">
                              {title}
                            </Dialog.Title>
                          )}
                          {description && (
                            <Dialog.Description className="mt-1 text-sm text-text-secondary">
                              {description}
                            </Dialog.Description>
                          )}
                        </div>
                        {showCloseButton && (
                          <IconButton
                            variant="ghost"
                            size="sm"
                            icon={<XMarkIcon />}
                            label="Close"
                            onClick={onClose}
                          />
                        )}
                      </div>
                    )}

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto p-6">
                      {children}
                    </div>

                    {/* Footer */}
                    {footer && (
                      <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border-primary">
                        {footer}
                      </div>
                    )}
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}

export default Modal
