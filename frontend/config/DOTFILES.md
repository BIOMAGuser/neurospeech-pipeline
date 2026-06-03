# Frontend Dotfiles & ESLint Konfiguration

## Dateien

- **`.eslintrc.json`** - ESLint Konfiguration (kopiert in frontend/config/)
- **`.dockerignore.frontend`** - Docker Build ignoriert diese Dateien (im docker/ Ordner)

## ESLint

ESLint Konfiguration für Code-Qualität:

```bash
npm run lint      # Check
npx eslint . --fix # Auto-Fix
```
