import type { Meta, StoryObj } from '@storybook/html';
import '../tokens/design_tokens.css';
import './badge.css';

const meta = {
  title: 'Primitives/Badge',
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: { type: 'select' },
      options: ['default', 'success', 'warning', 'error', 'info'],
    },
    size: {
      control: { type: 'inline-radio' },
      options: ['sm', 'md', 'lg'],
    },
    label: { control: 'text' },
  },
  args: {
    variant: 'default',
    size: 'md',
    label: 'Badge',
  },
} satisfies Meta;

export default meta;
type Story = StoryObj;

export const Default: Story = {
  render: (args) => `
    <span class="wdr-badge wdr-badge--${args.variant} wdr-badge--${args.size}">${args.label}</span>
  `,
};

export const StatusBadges: Story = {
  render: () => `
    <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
      <span class="wdr-badge wdr-badge--default wdr-badge--md">Default</span>
      <span class="wdr-badge wdr-badge--success wdr-badge--md">Complete</span>
      <span class="wdr-badge wdr-badge--warning wdr-badge--md">Warning</span>
      <span class="wdr-badge wdr-badge--error wdr-badge--md">Error</span>
      <span class="wdr-badge wdr-badge--info wdr-badge--md">Info</span>
    </div>
  `,
};

export const Sizes: Story = {
  render: () => `
    <div style="display: flex; gap: 0.5rem; align-items: center;">
      <span class="wdr-badge wdr-badge--success wdr-badge--sm">Small</span>
      <span class="wdr-badge wdr-badge--success wdr-badge--md">Medium</span>
      <span class="wdr-badge wdr-badge--success wdr-badge--lg">Large</span>
    </div>
  `,
};

export const DotIndicators: Story = {
  render: () => `
    <div style="display: flex; gap: 0.75rem; align-items: center;">
      <span class="wdr-badge wdr-badge--dot wdr-badge--success wdr-badge--sm" aria-label="Connected"></span>
      <span class="wdr-badge wdr-badge--dot wdr-badge--warning wdr-badge--md" aria-label="Slow"></span>
      <span class="wdr-badge wdr-badge--dot wdr-badge--error wdr-badge--lg" aria-label="Disconnected"></span>
    </div>
  `,
};

export const ProviderBadges: Story = {
  render: () => `
    <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
      <span class="wdr-badge wdr-badge--provider-exa wdr-badge--md">Exa MCP</span>
      <span class="wdr-badge wdr-badge--provider-tavily wdr-badge--md">Tavily</span>
      <span class="wdr-badge wdr-badge--provider-firecrawl wdr-badge--md">Firecrawl</span>
      <span class="wdr-badge wdr-badge--provider-mistral wdr-badge--md">Mistral</span>
    </div>
  `,
};

export const Dismissible: Story = {
  render: () => `
    <div style="display: flex; gap: 0.5rem; align-items: center;">
      <span class="wdr-badge wdr-badge--info wdr-badge--md wdr-badge--dismissible">
        Filter
        <button class="wdr-badge__close" aria-label="Remove filter">
          <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3l6 6M9 3l-6 6"/></svg>
        </button>
      </span>
    </div>
  `,
};

export const PillWithCount: Story = {
  render: () => `
    <div style="display: flex; gap: 0.5rem; align-items: center;">
      <span class="wdr-badge wdr-badge--error wdr-badge--sm wdr-badge--pill">
        <span class="wdr-badge__count">3</span>
      </span>
      <span class="wdr-badge wdr-badge--info wdr-badge--md wdr-badge--pill">
        <span class="wdr-badge__count">12</span>
      </span>
      <span class="wdr-badge wdr-badge--success wdr-badge--lg wdr-badge--pill">
        <span class="wdr-badge__count">99+</span>
      </span>
    </div>
  `,
};
