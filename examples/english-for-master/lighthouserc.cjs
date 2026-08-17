module.exports = {
  ci: {
    collect: {
      staticDistDir: './site',
      numberOfRuns: 3,
      url: ['http://localhost/index.html']
    },
    assert: {
      assertions: {
        'categories:performance': ['warn', { minScore: 0.90 }],
        'categories:accessibility': ['error', { minScore: 0.95 }],
        'categories:best-practices': ['warn', { minScore: 0.95 }],
        'categories:seo': ['warn', { minScore: 0.90 }],
        'first-contentful-paint': ['warn', { maxNumericValue: 2000 }],
        'largest-contentful-paint': ['warn', { maxNumericValue: 2500 }],
        'cumulative-layout-shift': ['error', { maxNumericValue: 0.10 }]
      }
    },
    upload: { target: 'filesystem', outputDir: './.lighthouseci' }
  }
};
