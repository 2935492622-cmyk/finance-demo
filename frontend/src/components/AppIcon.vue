<script setup>
defineProps({ name: { type: String, required: true } })
const paths = {
  book: 'M4 4h12a3 3 0 0 1 3 3v13H7a3 3 0 0 1-3-3V4Zm0 13a3 3 0 0 1 3-3h12M8 4v7m4-3h3',
  grid: 'M3 3h7v7H3V3Zm11 0h7v7h-7V3ZM3 14h7v7H3v-7Zm11 0h7v7h-7v-7Z',
  plus: 'M12 5v14M5 12h14',
  arrowIn: 'M17 7 7 17M7 7v10h10',
  arrowOut: 'M7 17 17 7M7 7h10v10',
  wallet: 'M20 8V5H5a2 2 0 0 0 0 4h15v11H5a2 2 0 0 1-2-2V7m17 6h-5v4h5',
  refresh: 'M20 7v5h-5M4 17v-5h5M6.1 7a7 7 0 0 1 11.6-2L20 8M4 16l2.3 3A7 7 0 0 0 18 17',
  check: 'm5 12 4 4L19 6',
  list: 'M8 6h12M8 12h12M8 18h12M3 6h.01M3 12h.01M3 18h.01',
  leaf: 'M20 4C9 3 3 8 5 15c5 6 13 2 15-11ZM6 19l9-9',
  warning: 'm12 3 10 18H2L12 3Zm0 6v5m0 3h.01',
  calendar: 'M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2ZM7 3v4m10-4v4M3 11h18',
  edit: 'm15 4 5 5M4 20l4-1 12-12a2 2 0 0 0-4-4L4 15v5Z',
  trash: 'M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7',
  filter: 'M3 4h18l-7 8v7l-4 2v-9L3 4Z',
  chart: 'M11 3a9 9 0 1 0 10 10H11V3Zm4 0v6h6a7 7 0 0 0-6-6Z',
}
</script>

<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path :d="paths[name] || paths.book" />
  </svg>
</template>
