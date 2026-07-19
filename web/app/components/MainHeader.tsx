"use client";

import Link from "next/link";

interface MainHeaderProps {
  setMobileMenuOpen(open: boolean): void;
  mobileMenuOpen: boolean;
  onShowShortcuts: () => void;
}

export function MainHeader(props: MainHeaderProps) {
  const { setMobileMenuOpen, mobileMenuOpen, onShowShortcuts } = props;
  function handleMenuOpen() {
    setMobileMenuOpen(true);
  }

  return (
    <header className="border-b-2 border-border-muted p-2 flex items-center justify-between min-h-[44px]">
      <div className="flex items-center gap-2">
        {/* Hamburger menu - mobile only */}
        <button
          onClick={handleMenuOpen}
          className="lg:hidden p-2 text-text-muted hover:text-foreground min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Open menu"
          aria-expanded={mobileMenuOpen}
          aria-controls="sidebar-navigation"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <span className="text-[11px] text-text-muted">do-web-doc-resolver</span>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={onShowShortcuts}
          className="text-[11px] text-text-muted hover:text-accent min-h-[44px] flex items-center px-2 focus:outline-none focus:text-accent"
          aria-label="Show keyboard shortcuts"
        >
          Shortcuts
        </button>
        <Link href="/help" className="text-[11px] text-text-muted hover:text-accent min-h-[44px] flex items-center px-2 focus:outline-none focus:text-accent">
          Help
        </Link>
      </div>
    </header>
  );
}
