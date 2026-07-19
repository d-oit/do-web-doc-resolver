"use client";

import { useEffect, useRef } from "react";

interface KeyboardShortcutsModalProps {
  onClose: () => void;
}

const SHORTCUTS = [
  { key: "Ctrl/Cmd + K", action: "Focus input" },
  { key: "Ctrl/Cmd + /", action: "Show/hide shortcuts" },
  { key: "Enter", action: "Submit query" },
  { key: "Escape", action: "Clear input or close modal" },
];

export function KeyboardShortcutsModal({ onClose }: KeyboardShortcutsModalProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previouslyFocusedElementRef = useRef<HTMLElement | null>(null);
  const modalContainerRef = useRef<HTMLDivElement>(null);

  // Focus preservation and restoration
  useEffect(() => {
    // Record the element that had focus before the modal opened
    if (typeof document !== "undefined") {
      previouslyFocusedElementRef.current = document.activeElement as HTMLElement;
    }

    // Move focus inside the modal (to the close button)
    closeButtonRef.current?.focus();

    return () => {
      // Restore focus to the previous element when closing
      previouslyFocusedElementRef.current?.focus();
    };
  }, []);

  // Trap focus inside the modal and handle Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key === "Tab") {
        if (!modalContainerRef.current) return;

        // Get all focusable elements inside the modal container
        const focusableElements = modalContainerRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );

        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey) {
          // If shift + tab and we are on the first element, wrap around to the last element
          if (document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          }
        } else {
          // If tab and we are on the last element, wrap around to the first element
          if (document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center"
      onClick={onClose}
    >
      <div
        ref={modalContainerRef}
        className="bg-background border-2 border-border-muted p-6 max-w-md w-full mx-4"
        onClick={(e) => {
          e.stopPropagation();
        }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="shortcuts-modal-title"
      >
        <div className="flex justify-between mb-4">
          <h2 id="shortcuts-modal-title" className="text-[13px] font-bold text-foreground">
            Keyboard Shortcuts
          </h2>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            className="text-text-muted hover:text-foreground text-[18px] leading-none focus:outline-none focus:text-accent focus:ring-2 focus:ring-accent"
            aria-label="Close shortcuts"
          >
            ×
          </button>
        </div>
        <div className="space-y-2">
          {SHORTCUTS.map(({ key, action }) => (
            <div key={key} className="flex justify-between text-[11px]">
              <span className="text-text-muted">{action}</span>
              <kbd className="bg-[#222] px-2 py-1 text-foreground border border-border-muted">{key}</kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
