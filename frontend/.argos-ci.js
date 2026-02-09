/**
 * Argos CI Configuration
 * https://argos-ci.com/docs/getting-started
 *
 * Visual regression testing for Coloring Book Generator (project001)
 */

/** @type {import('@argos-ci/cli').Config} */
export default {
  token: process.env.ARGOS_TOKEN,

  // Screenshot directory — where storycap outputs PNGs
  screenshotDirectory: './__screenshots__',

  // Base branch for comparison
  baseBranch: 'main',

  // 0.1% pixel difference tolerance (standard preset)
  threshold: 0.001,

  // Parallel upload for faster CI
  parallel: {
    nonce: process.env.ARGOS_PARALLEL_NONCE,
    total: parseInt(process.env.ARGOS_PARALLEL_TOTAL || '1', 10),
  },

  // Build information for PR context
  build: {
    name: process.env.ARGOS_BUILD_NAME || 'project001-coloring-book',
  },

  // Ignore non-image files
  ignore: [
    '**/*.mp4',
    '**/*.webm',
    '**/favicon.ico',
  ],
}
