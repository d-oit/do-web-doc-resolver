"use client";

import { useState, useRef, useEffect, useId } from "react";

interface Option {
  id: string;
  label: string;
  description?: string;
}

interface ProfileComboboxProps {
  value: string;
  onChange: (value: string) => void;
  options: Option[];
}

export default function ProfileCombobox({ value, onChange, options }: ProfileComboboxProps) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const listboxId = useId();
  const triggerId = useId();

  const selectedOption = options.find((o) => o.id === value);

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
      const selectedIdx = options.findIndex(o => o.id === value);
      setActiveIndex(selectedIdx !== -1 ? selectedIdx : 0);
    } else {
      setActiveIndex(-1);
    }
  }, [open, options, value]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setOpen(true);
      }
      return;
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setActiveIndex((prev) => (prev + 1) % options.length);
        break;
      case "ArrowUp":
        e.preventDefault();
        setActiveIndex((prev) => (prev - 1 + options.length) % options.length);
        break;
      case "Enter":
      case " ":
        e.preventDefault();
        if (activeIndex >= 0 && activeIndex < options.length) {
          onChange(options[activeIndex].id);
          setOpen(false);
        }
        break;
      case "Escape":
        e.preventDefault();
        setOpen(false);
        break;
      case "Home":
        e.preventDefault();
        setActiveIndex(0);
        break;
      case "End":
        e.preventDefault();
        setActiveIndex(options.length - 1);
        break;
      case "Tab":
        setOpen(false);
        break;
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        id={triggerId}
        type="button"
        onClick={() => setOpen(!open)}
        onKeyDown={handleKeyDown}
        className="w-full bg-[#141414] border-2 border-border-muted px-3 py-2 text-left flex items-center justify-between text-[12px] min-h-[44px] hover:border-border-strong focus:border-accent outline-none"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-label="Change search profile"
        aria-activedescendant={open && activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined}
      >
        <span>{selectedOption?.label || "Select profile..."}</span>
        <span className="text-[10px] text-text-dim" aria-hidden="true">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div
          id={listboxId}
          className="absolute z-10 w-full mt-1 bg-[#141414] border-2 border-border-muted shadow-xl overflow-hidden"
          role="listbox"
          aria-labelledby={triggerId}
        >
          {options.map((option, index) => (
            <div
              key={option.id}
              id={`${listboxId}-option-${index}`}
              onClick={() => {
                onChange(option.id);
                setOpen(false);
              }}
              onMouseEnter={() => setActiveIndex(index)}
              className={`w-full px-3 py-2 text-left cursor-pointer transition-colors flex flex-col ${
                index === activeIndex ? "bg-accent text-background" :
                option.id === value ? "bg-[#222] text-accent" : "text-foreground"
              }`}
              role="option"
              aria-selected={option.id === value}
            >
              <span className="text-[12px] font-bold">{option.label}</span>
              {option.description && (
                <div className={`text-[10px] ${index === activeIndex ? "text-background/80" : "text-text-muted"}`}>
                  {option.description}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
