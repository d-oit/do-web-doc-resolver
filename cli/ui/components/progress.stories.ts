import type { Meta, StoryObj } from '@storybook/html';
import '../tokens/design_tokens.css';
import './progress.css';

const meta = {
  title: 'Pipeline/ProgressBar',
  tags: ['autodocs'],
  argTypes: {
    size: {
      control: { type: 'inline-radio' },
      options: ['sm', 'md', 'lg'],
    },
    value: {
      control: { type: 'range', min: 0, max: 100, step: 5 },
      description: 'Progress percentage',
    },
    variant: {
      control: { type: 'inline-radio' },
      options: ['default', 'success', 'warning', 'error'],
    },
    labeled: { control: 'boolean' },
  },
  args: {
    size: 'md',
    value: 65,
    variant: 'default',
    labeled: false,
  },
} satisfies Meta;

export default meta;
type Story = StoryObj;

export const Default: Story = {
  render: (args) => {
    const variantClass = args.variant !== 'default' ? ` wdr-progress--${args.variant}` : '';
    const labeledClass = args.labeled ? ' wdr-progress--labeled' : '';
    return `
      <div class="wdr-progress wdr-progress--${args.size}${variantClass}${labeledClass}"
           role="progressbar"
           aria-valuenow="${args.value}"
           aria-valuemin="0"
           aria-valuemax="100">
        <div class="wdr-progress__fill" style="width: ${args.value}%"></div>
        ${args.labeled ? `<span class="wdr-progress__label">${args.value}%</span>` : ''}
      </div>
    `;
  },
};

export const Indeterminate: Story = {
  render: () => `
    <div class="wdr-progress wdr-progress--md wdr-progress--indeterminate"
         role="progressbar" aria-label="Loading">
      <div class="wdr-progress__fill"></div>
    </div>
  `,
};

export const Variants: Story = {
  render: () => `
    <div style="display: flex; flex-direction: column; gap: 1rem; max-width: 400px;">
      <div>
        <span style="font-size: 0.75rem; color: var(--wdr-text-secondary); margin-bottom: 0.25rem; display: block;">Default</span>
        <div class="wdr-progress wdr-progress--md" role="progressbar" aria-valuenow="70">
          <div class="wdr-progress__fill" style="width: 70%"></div>
        </div>
      </div>
      <div>
        <span style="font-size: 0.75rem; color: var(--wdr-text-secondary); margin-bottom: 0.25rem; display: block;">Success</span>
        <div class="wdr-progress wdr-progress--md wdr-progress--success" role="progressbar" aria-valuenow="100">
          <div class="wdr-progress__fill" style="width: 100%"></div>
        </div>
      </div>
      <div>
        <span style="font-size: 0.75rem; color: var(--wdr-text-secondary); margin-bottom: 0.25rem; display: block;">Warning</span>
        <div class="wdr-progress wdr-progress--md wdr-progress--warning" role="progressbar" aria-valuenow="80">
          <div class="wdr-progress__fill" style="width: 80%"></div>
        </div>
      </div>
      <div>
        <span style="font-size: 0.75rem; color: var(--wdr-text-secondary); margin-bottom: 0.25rem; display: block;">Error</span>
        <div class="wdr-progress wdr-progress--md wdr-progress--error" role="progressbar" aria-valuenow="45">
          <div class="wdr-progress__fill" style="width: 45%"></div>
        </div>
      </div>
    </div>
  `,
};

export const Sizes: Story = {
  render: () => `
    <div style="display: flex; flex-direction: column; gap: 1rem; max-width: 400px;">
      <div>
        <span style="font-size: 0.75rem; color: var(--wdr-text-secondary); margin-bottom: 0.25rem; display: block;">Small (4px)</span>
        <div class="wdr-progress wdr-progress--sm" role="progressbar" aria-valuenow="60">
          <div class="wdr-progress__fill" style="width: 60%"></div>
        </div>
      </div>
      <div>
        <span style="font-size: 0.75rem; color: var(--wdr-text-secondary); margin-bottom: 0.25rem; display: block;">Medium (8px)</span>
        <div class="wdr-progress wdr-progress--md" role="progressbar" aria-valuenow="60">
          <div class="wdr-progress__fill" style="width: 60%"></div>
        </div>
      </div>
      <div>
        <span style="font-size: 0.75rem; color: var(--wdr-text-secondary); margin-bottom: 0.25rem; display: block;">Large (12px)</span>
        <div class="wdr-progress wdr-progress--lg" role="progressbar" aria-valuenow="60">
          <div class="wdr-progress__fill" style="width: 60%"></div>
        </div>
      </div>
    </div>
  `,
};

export const Labeled: Story = {
  render: () => `
    <div class="wdr-progress wdr-progress--md wdr-progress--labeled"
         role="progressbar" aria-valuenow="75" aria-valuemin="0" aria-valuemax="100">
      <div class="wdr-progress__fill" style="width: 75%"></div>
      <span class="wdr-progress__label">75%</span>
    </div>
  `,
};

export const MultiSegment: Story = {
  render: () => `
    <div class="wdr-progress wdr-progress--lg"
         role="progressbar" aria-label="Pipeline stages">
      <div class="wdr-progress__segments">
        <div class="wdr-progress__segment wdr-progress__segment--success"></div>
        <div class="wdr-progress__segment wdr-progress__segment--success"></div>
        <div class="wdr-progress__segment wdr-progress__segment--running"></div>
        <div class="wdr-progress__segment"></div>
      </div>
    </div>
  `,
};
