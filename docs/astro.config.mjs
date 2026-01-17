import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://grburgess.github.io',
  base: '/great_silence',
  integrations: [
    starlight({
      title: 'Great Silence',
      description: 'Monte Carlo simulation of galactic civilizations and the Fermi Paradox',
      logo: {
        src: './public/favicon.svg',
        replacesTitle: false,
      },
      social: {
        github: 'https://github.com/grburgess/great_silence',
      },
      customCss: [
        './src/styles/space-theme.css',
        '@fontsource/space-mono/400.css',
        '@fontsource/space-mono/700.css',
        '@fontsource/outfit/400.css',
        '@fontsource/outfit/600.css',
        '@fontsource/outfit/700.css',
      ],
      head: [
        {
          tag: 'meta',
          attrs: {
            name: 'theme-color',
            content: '#0a0a0f',
          },
        },
      ],
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { label: 'Installation', slug: 'getting-started/installation' },
            { label: 'Quick Start', slug: 'getting-started/quickstart' },
            { label: 'Configuration', slug: 'getting-started/configuration' },
          ],
        },
        {
          label: 'Concepts',
          items: [
            { label: 'The Fermi Paradox', slug: 'concepts/fermi-paradox' },
            { label: 'Drake Equation', slug: 'concepts/drake-equation' },
            { label: 'Kardashev Scale', slug: 'concepts/kardashev-scale' },
            { label: 'The Great Filter', slug: 'concepts/great-filter' },
          ],
        },
        {
          label: 'Guides',
          items: [
            { label: 'Simulation Flow', slug: 'guides/simulation-flow' },
            { label: 'Probe Expansion', slug: 'guides/probe-expansion' },
            { label: 'Astrophysical Hazards', slug: 'guides/astrophysical-hazards' },
            { label: 'Visualization', slug: 'guides/visualization' },
          ],
        },
        {
          label: 'API Reference',
          autogenerate: { directory: 'api' },
        },
        {
          label: 'Tutorials',
          items: [
            { label: 'Basic Simulation', slug: 'tutorials/basic-simulation' },
            { label: 'Monte Carlo Analysis', slug: 'tutorials/monte-carlo' },
            { label: 'Three.js Visualization', slug: 'tutorials/threejs-visualization' },
            { label: 'Web Application', slug: 'tutorials/webapp' },
          ],
        },
        {
          label: 'Reference',
          items: [
            { label: 'Parameters', slug: 'reference/parameters' },
            { label: 'Presets', slug: 'reference/presets' },
            { label: 'CLI', slug: 'reference/cli' },
          ],
        },
      ],
      editLink: {
        baseUrl: 'https://github.com/grburgess/great_silence/edit/main/docs/',
      },
      lastUpdated: true,
      pagination: true,
      tableOfContents: {
        minHeadingLevel: 2,
        maxHeadingLevel: 4,
      },
      expressiveCode: {
        themes: ['dracula', 'github-light'],
        styleOverrides: {
          borderRadius: '0.5rem',
        },
      },
    }),
  ],
});
