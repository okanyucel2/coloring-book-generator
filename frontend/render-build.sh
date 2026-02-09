#!/usr/bin/env bash
# render-build.sh - Prepare standalone context and build for Render deployment
# Mirrors the CI "Prepare standalone context" step from .github/workflows/ci.yml
set -euo pipefail

echo "==> Stripping workspace:* dependencies..."
node -e "
  const fs = require('fs');
  const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
  for (const [name, ver] of Object.entries(pkg.devDependencies || {})) {
    if (String(ver).startsWith('workspace:')) delete pkg.devDependencies[name];
  }
  fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2) + '\n');
"

echo "==> Inlining tsconfig.json (replaces @genesis/tsconfig)..."
cat > tsconfig.json << 'TSEOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "resolveJsonModule": true,
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "useDefineForClassFields": true,
    "jsx": "preserve",
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
TSEOF

cat > tsconfig.node.json << 'TSEOF'
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
TSEOF

echo "==> Installing dependencies..."
pnpm install --no-frozen-lockfile

echo "==> Building..."
pnpm build

echo "==> Build complete!"
