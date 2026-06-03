# Frontend Konfiguration

## Umgebungsvariablen

### Entwicklung
Kopiere `config/.env.example` zu `.env.local` und passe an:
```bash
NEXT_PUBLIC_API_URL=http://localhost/api
```

### Produktion
Verwende `config/.env.production.example` als Vorlage:
```bash
NEXT_PUBLIC_API_URL=/api
```

## Dateien

- **`.eslintrc.json`** - ESLint Konfiguration (kopiert in frontend/config/)
- **`.dockerignore.frontend`** - Docker Build ignoriert diese Dateien (im docker/ Ordner)

## ESLint

ESLint Konfiguration für Code-Qualität:

```bash
npm run lint      # Check
npx eslint . --fix # Auto-Fix
```
