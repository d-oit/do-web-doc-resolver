import type { StorybookConfig } from '@storybook/html-vite';

const config: StorybookConfig = {
  stories: [
    '../stories/**/*.mdx',
    '../stories/**/*.stories.@(js|ts)',
    '../components/**/*.stories.@(js|ts)',
  ],

  addons: [
    '@storybook/addon-essentials',
    '@storybook/addon-a11y',
    '@storybook/addon-interactions',
  ],

  framework: {
    name: '@storybook/html-vite',
    options: {},
  },

  typescript: {
    check: false,
    reactDocgen: false,
  },

  viteFinal: async (config) => {
    // Ensure CSS custom properties are available
    config.css ??= {};
    config.css.devSourcemap = true;
    return config;
  },

  docs: {
    autodocs: 'tag',
    defaultName: 'Overview',
  },

  core: {
    disableTelemetry: true,
  },

  features: {
    interactionsDebugger: true,
  },
};

export default config;
