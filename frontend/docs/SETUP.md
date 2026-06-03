# Frontend Setup & Entwicklung

## Docker-basierte Entwicklung (empfohlen)

Das Frontend laeuft komplett in Docker mit Hot Module Replacement (HMR).

### Starten

```bash
# Aus dem Projekt-Root
docker compose up -d
```

Das Frontend ist unter http://localhost erreichbar (via Nginx Reverse Proxy).

### Wie HMR funktioniert

- Der Frontend-Container nutzt das `dev`-Target im Dockerfile (`next dev --turbopack`)
- Der Quellcode wird als Volume gemountet (`./frontend:/app`)
- `node_modules` liegen in einem separaten Docker-Volume (kein Konflikt mit Host)
- Aenderungen an Dateien in `src/` werden sofort im Browser sichtbar

### node_modules aktualisieren

Nach Aenderungen an `package.json`:

```bash
docker compose down
docker volume rm speechscribe_frontend_node_modules
docker compose up --build -d
```

## Scripts

```bash
npm run dev      # Entwicklung mit Turbopack (im Container)
npm run build    # Production Build erstellen
npm start        # Production Server starten
npm run lint     # Code linting
npm run typecheck # TypeScript Check
```

## Umgebungsvariablen

Im Docker-Setup wird `NEXT_PUBLIC_API_URL=http://localhost/api` automatisch gesetzt. Die API laeuft ueber den Nginx Reverse Proxy.

## Troubleshooting

### Frontend zeigt alte Version?
```bash
# Container neu starten
docker compose restart frontend
```

### Module nicht gefunden?
```bash
# node_modules Volume neu aufbauen
docker compose down
docker volume rm speechscribe_frontend_node_modules
docker compose up --build -d
```

### HMR funktioniert nicht?
- Pruefen ob `WATCHPACK_POLLING=true` in docker-compose.yml gesetzt ist
- Pruefen ob Volume-Mount korrekt ist: `./frontend:/app`
- Nginx-Logs pruefen: `docker compose logs nginx`
