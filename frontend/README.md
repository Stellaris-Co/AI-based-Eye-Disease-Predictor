# OphthalmoAI Frontend

React/Vite frontend for the OphthalmoAI screening app.

## Local setup

```bash
npm install
npm run dev
```

The app calls `/api` by default. In development, Vite proxies `/api` to
`http://localhost:8000`; in production, Nginx proxies `/api` to the backend
container. Set `VITE_API_URL` only when deploying the frontend separately.

## Useful commands

```bash
npm run build
npm run lint
```

Main files:
- `src/App.jsx` - page layout, diagnostic flow, PDF export
- `src/ChatBox.jsx` - floating chat widget
- `src/cropImage.js` - crop helper used before upload
