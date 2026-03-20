import type { Meta, StoryObj } from '@storybook/html';
import '../tokens/design_tokens.css';
import './card.css';
import './badge.css';
import './button.css';

const meta = {
  title: 'Containers/Card',
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: { type: 'select' },
      options: ['default', 'interactive', 'flat', 'outlined', 'compact'],
    },
    status: {
      control: { type: 'inline-radio' },
      options: ['none', 'success', 'warning', 'error', 'info'],
    },
  },
  args: {
    variant: 'default',
    status: 'none',
  },
} satisfies Meta;

export default meta;
type Story = StoryObj;

export const Default: Story = {
  render: (args) => {
    const statusClass = args.status !== 'none' ? ` wdr-card--status-${args.status}` : '';
    const variantClass = args.variant !== 'default' ? ` wdr-card--${args.variant}` : '';
    return `
      <div class="wdr-card${variantClass}${statusClass}" style="max-width: 400px;">
        <div class="wdr-card__header">
          <span class="wdr-card__title">Resolve Result</span>
          <span class="wdr-badge wdr-badge--sm wdr-badge--success">Complete</span>
        </div>
        <div class="wdr-card__body">
          <p class="wdr-card__description">Markdown content resolved from the target URL via Exa MCP provider.</p>
        </div>
        <div class="wdr-card__footer">
          <button class="wdr-button wdr-button--ghost wdr-button--sm">Copy</button>
          <button class="wdr-button wdr-button--primary wdr-button--sm">Open</button>
        </div>
      </div>
    `;
  },
};

export const Interactive: Story = {
  args: { variant: 'interactive' },
  render: (args) => `
    <div class="wdr-card wdr-card--interactive" style="max-width: 400px;">
      <div class="wdr-card__header">
        <span class="wdr-card__title">Exa SDK</span>
        <span class="wdr-badge wdr-badge--sm wdr-badge--provider-exa">Exa</span>
      </div>
      <div class="wdr-card__body">
        <p class="wdr-card__description">Neural search with content extraction. 10 req/min free tier.</p>
      </div>
    </div>
  `,
};

export const StatusAccent: Story = {
  render: () => `
    <div style="display: flex; flex-direction: column; gap: 1rem; max-width: 400px;">
      <div class="wdr-card wdr-card--status-success">
        <span class="wdr-card__title">Success</span>
        <p class="wdr-card__description">Provider connected and healthy.</p>
      </div>
      <div class="wdr-card wdr-card--status-warning">
        <span class="wdr-card__title">Warning</span>
        <p class="wdr-card__description">Rate limit approaching (80% used).</p>
      </div>
      <div class="wdr-card wdr-card--status-error">
        <span class="wdr-card__title">Error</span>
        <p class="wdr-card__description">API key invalid or expired.</p>
      </div>
      <div class="wdr-card wdr-card--status-info">
        <span class="wdr-card__title">Info</span>
        <p class="wdr-card__description">New provider version available.</p>
      </div>
    </div>
  `,
};

export const Compact: Story = {
  args: { variant: 'compact' },
  render: () => `
    <div class="wdr-card wdr-card--compact" style="max-width: 300px;">
      <span class="wdr-card__title">Cache Hit</span>
      <p class="wdr-card__description" style="margin: 0;">Resolved from semantic cache in 12ms.</p>
    </div>
  `,
};

export const FlatAndOutlined: Story = {
  render: () => `
    <div style="display: flex; flex-direction: column; gap: 1rem; max-width: 400px;">
      <div class="wdr-card wdr-card--flat">
        <span class="wdr-card__title">Flat Card</span>
        <p class="wdr-card__description">No shadow — for inline sections.</p>
      </div>
      <div class="wdr-card wdr-card--outlined">
        <span class="wdr-card__title">Outlined Card</span>
        <p class="wdr-card__description">Border only — for subtle grouping.</p>
      </div>
    </div>
  `,
};
