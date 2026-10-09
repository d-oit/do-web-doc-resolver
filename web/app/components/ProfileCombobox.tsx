"use client";

import { useState, useRef, useEffect, KeyboardEvent, useId } from "react";

interface Option {
  id: string;
  label: string;
  description?: string;
}

interface ProfileComboboxProps {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  options: Option[];
}

export default function ProfileCombobox({ id: providedId, value, onChange, options }: ProfileComboboxProps) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const listboxRef = useRef<HTMLDivElement>(null);
  const generatedId = useId();
  const id = providedId || generatedId;
  const listboxId = `listbox-${id}`;

  const selectedOption = options.find((o) => o.id === value);
  const activeOption = open && activeIndex >= 0 ? options[activeIndex] : undefined;
  const activeDescendantId = activeOption ? `${listboxId}-option-${activeOption.id}` : undefined;

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (open) {
      const selectedIndex = options.findIndex((o) => o.id === value);
      setActiveIndex(selectedIndex >= 0 ? selectedIndex : 0);
    }
  }, [open, options, value]);

  const handleOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    triggerRef.current?.focus();
  };

  const handleSelect = (id: string) => {
    onChange(id);
    handleClose();
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (!open) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleOpen();
      }
      return;
    }

    switch (e.key) {
      case "Escape":
        e.preventDefault();
        handleClose();
        break;
      case "ArrowDown":
        e.preventDefault();
        setActiveIndex((prev) => (prev + 1) % options.length);
        break;
      case "ArrowUp":
        e.preventDefault();
        setActiveIndex((prev) => (prev - 1 + options.length) % options.length);
        break;
      case "Home":
        e.preventDefault();
        setActiveIndex(0);
        break;
      case "End":
        e.preventDefault();
        setActiveIndex(options.length - 1);
        break;
      case "Enter":
      case " ": {
        e.preventDefault();
        const option = options[activeIndex];
        if (activeIndex >= 0 && option) {
          handleSelect(option.id);
        }
        break;
      }
      case "Tab":
        setOpen(false);
        break;
    }
  };

  // Scroll active option into view when activeIndex changes
  useEffect(() => {
    if (open && activeIndex >= 0 && listboxRef.current && activeOption) {
      const activeEl = document.getElementById(`${listboxId}-option-${activeOption.id}`);
      if (activeEl) {
        activeEl.scrollIntoView({ block: "nearest" });
      }
    }
  }, [activeIndex, open, activeOption, listboxId]);

  return (
    <div className="relative" ref={containerRef}>
      <button
        id={id}
        ref={triggerRef}
        onClick={() => (open ? handleClose() : handleOpen())}
        onKeyDown={handleKeyDown}
        className="w-full bg-[#141414] border-2 border-border-muted px-3 py-2 text-left flex items-center justify-between text-[12px] min-h-[44px] hover:border-border-strong focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listboxId : undefined}
        aria-activedescendant={activeDescendantId}
        aria-label="Change search profile"
        title="Change search profile"
      >
        <span>{selectedOption?.label || "Select profile..."}</span>
        <span className="text-[10px] text-text-dim" aria-hidden="true">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div
          id={listboxId}
          ref={listboxRef}
          className="absolute z-10 w-full mt-1 bg-[#141414] border-2 border-border-muted shadow-xl"
          role="listbox"
          aria-label="Search profiles"
        >
          {options.map((option, index) => {
            const isSelected = option.id === value;
            const isActive = index === activeIndex;

            return (
              <div
                key={option.id}
                id={`${listboxId}-option-${option.id}`}
                onClick={() => handleSelect(option.id)}
                onMouseEnter={() => setActiveIndex(index)}
                className={`w-full px-3 py-2 text-left transition-colors flex flex-col cursor-pointer ${
                  isActive
                    ? "bg-accent text-background font-bold"
                    : isSelected
                    ? "bg-[#222] text-accent"
                    : "text-foreground hover:bg-[#222]"
                }`}
                role="option"
                aria-selected={isSelected}
              >
                <span className="text-[12px] font-bold">{option.label}</span>
                {option.description && (
                  <div className={`text-[10px] ${isActive ? "text-background/80" : "text-text-muted"}`}>
                    {option.description}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
