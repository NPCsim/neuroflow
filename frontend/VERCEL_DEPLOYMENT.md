# NeuroFlow Frontend Deployment Guide: Vercel

This guide outlines the exact setup and steps for deploying the NeuroFlow Next.js frontend to **Vercel**.

---

## 1. Overview & Project Structure

The frontend is a **Next.js 16 (App Router)** application located in the `/frontend` directory of the monorepo.

| File | Purpose |
| :--- | :--- |
| `src/lib/api.ts` | Centralized API client utility ensuring `NEXT_PUBLIC_API_URL` is sanitized without trailing slashes. |
| `src/app/layout.tsx` | Global metadata configuration including OpenGraph (`og:`), Twitter cards, and favicon links. |
| `src/app/icon.svg` | Vector favicon and high-DPI browser tab icon. |
| `src/app/opengraph-image.tsx` | Dynamic OpenGraph card generator (1200x630) powered by `@vercel/og` / `next/og`. |
| `vercel.json` | Vercel configuration declaring the Next.js framework preset and clean URLs. |
| `.env.example` | Environment variable documentation for local and production deployments. |

---

## 2. Environment Variables

Configure these in **Vercel Project Settings** → **Environment Variables**:

| Variable | Environment | Description | Example |
| :--- | :---: | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Production, Preview | The base URL of your deployed backend on Render. **Trailing slashes are automatically stripped by `src/lib/api.ts`.** | `https://neuroflow-backend.onrender.com` |
| `NEXT_PUBLIC_SITE_URL` | Production | Optional. Canonical URL for OpenGraph metadata and search engine indexing. Defaults to `https://neuroflow.vercel.app`. | `https://your-domain.vercel.app` |

> [!NOTE]
> Since this is a public client-side variable prefixed with `NEXT_PUBLIC_`, it is inlined into the client bundle at build time by Next.js. Whenever you update `NEXT_PUBLIC_API_URL` in Vercel, trigger a **Redeploy** to apply changes.

---

## 3. Favicon & OpenGraph (OG) Assets

1. **Favicon**:
   - `src/app/icon.svg`: Modern high-resolution vector icon with NeuroFlow indigo-to-cyan gradient and neural pulse symbol.
   - `src/app/favicon.ico`: Standard multi-size ICO fallback.
2. **OpenGraph & Twitter Card**:
   - `src/app/opengraph-image.tsx`: Dynamic 1200x630 social preview card rendered at `/opengraph-image`.
   - `src/app/layout.tsx`: Configured with:
     - `metadataBase: new URL(siteUrl)`
     - `openGraph`: Title, Description, Locale, Site Name, Type (`website`).
     - `twitter`: Card type (`summary_large_image`), Title, Description.

---

## 4. Exact Step-by-Step Vercel Deployment

### Step 1: Import Repository
1. Log in to [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New…** → **Project**.
3. Select your GitHub / GitLab repository.

### Step 2: Configure Monorepo Root Directory
1. In the **Configure Project** screen, find **Root Directory**.
2. Click **Edit** and select or type `frontend`.
3. Keep the **Framework Preset** as **Next.js**.

### Step 3: Configure Build & Development Settings
Leave the defaults as configured:
- **Build Command**: `next build` (or leave default)
- **Output Directory**: `.next` (or leave default)
- **Install Command**: `npm install` (or leave default)

### Step 4: Add Environment Variables
Under the **Environment Variables** section, add:
- **Key**: `NEXT_PUBLIC_API_URL`
- **Value**: `https://neuroflow-backend.onrender.com` *(Replace with your actual Render backend URL)*
- **Environments**: Check **Production**, **Preview**, and **Development**.

*(Optional)*:
- **Key**: `NEXT_PUBLIC_SITE_URL`
- **Value**: `https://neuroflow.vercel.app` (or your custom domain)

### Step 5: Deploy
1. Click **Deploy**.
2. Vercel will install dependencies, compile TypeScript, and statically render all 10 app routes.
3. Once finished, Vercel will give you a live production URL (e.g. `https://neuroflow.vercel.app`).

### Step 6: Update Backend CORS on Render
Now that your Vercel frontend has a URL (e.g., `https://neuroflow.vercel.app`):
1. Go to your [Render Dashboard](https://dashboard.render.com).
2. Open your `neuroflow-backend` Web Service.
3. Go to **Environment** → edit `ALLOWED_ORIGINS`.
4. Include your Vercel domain:
   ```text
   ALLOWED_ORIGINS=https://neuroflow.vercel.app,http://localhost:3000
   ```
5. Click **Save Changes**. Render will automatically restart your backend with the updated CORS allowlist.

---

## 5. Verification Checklist

- [x] **TypeScript**: `npx tsc --noEmit` exits with `0` errors.
- [x] **Production Build**: `npm run build` compiles with zero errors, pre-rendering static routes.
- [x] **ESLint**: `npm run lint -- --quiet` exits with `0` errors.
- [x] **OpenGraph Preview**: Inspect `https://your-domain.vercel.app/opengraph-image` or check via [OpenGraph.xyz](https://www.opengraph.xyz/).
- [x] **Backend Status Badge**: Look at the top navigation bar badge — it turns green with latency when connected to your Render backend.
