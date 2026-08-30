import { defineConfig } from 'vitepress'

export default defineConfig({
  base: '/agent-replay/',
  title: 'Agent Replay',
  description: 'Time-travel debugging for AI agents. Record, replay, and analyze agent execution traces locally.',
  head: [
    ['meta', { name: 'keywords', content: 'AI agent debugging, agent trace, LLM debugging, agent observability, agent replay, time-travel debugging' }],
    ['meta', { property: 'og:title', content: 'Agent Replay — Time-travel debugging for AI agents' }],
    ['meta', { property: 'og:description', content: 'Record, replay, and analyze AI agent execution traces. Local-first, open-source, with built-in failure detection.' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
  ],
  cleanUrls: true,
  themeConfig: {
    nav: [
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'Failure Patterns', link: '/failure-patterns' },
      { text: 'API', link: '/api/python-sdk' },
      { text: 'GitHub', link: 'https://github.com/agent-experience/agent-replay' }
    ],
    sidebar: [
      {
        text: 'Introduction',
        items: [
          { text: 'What is Agent Replay?', link: '/' },
          { text: 'Getting Started', link: '/guide/getting-started' },
          { text: 'Why Agent Replay?', link: '/guide/why-agent-replay' },
        ]
      },
      {
        text: 'Core Concepts',
        items: [
          { text: 'Trace Schema', link: '/guide/trace-schema' },
          { text: 'Failure Analysis', link: '/guide/failure-analysis' },
          { text: 'Privacy & Redaction', link: '/guide/privacy' },
        ]
      },
      {
        text: 'References',
        items: [
          { text: '10 Agent Failure Patterns', link: '/failure-patterns' },
          { text: 'Python SDK', link: '/api/python-sdk' },
          { text: 'TypeScript SDK', link: '/api/typescript-sdk' },
          { text: 'CLI Reference', link: '/api/cli' },
        ]
      }
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/agent-experience/agent-replay' }
    ],
    footer: {
      message: 'Released under the Apache 2.0 License.',
      copyright: 'Copyright © 2026 Agent Experience'
    },
    search: {
      provider: 'local'
    }
  },
  sitemap: {
    hostname: 'https://agent-experience.github.io/agent-replay'
  }
})
