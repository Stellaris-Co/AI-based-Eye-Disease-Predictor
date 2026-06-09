# OphthalmoAI Frontend

React/Vite frontend for the OphthalmoAI screening app.

## Local setup

```bash
npm install
npm run dev
```

The app expects the backend on `http://localhost:8000` unless `VITE_API_URL` is set.

## Useful commands

```bash
npm run build
npm run lint
```

Main files:
- `src/App.jsx` - page layout, diagnostic flow, PDF export
- `src/ChatBox.jsx` - floating chat widget
- `src/cropImage.js` - crop helper used before upload
