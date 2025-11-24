# -*- coding: utf-8 -*-
"""
Master Wilayah Indonesia - V25.0 (Final Perfect UI)
---------------------------------------------------
Fitur Lengkap:
1. UI/UX:
   - Logo BPS proporsional dalam kotak rounded.
   - Responsif Adaptif (Card View < 1024px, Table View > 1024px).
   - Tema Hybrid (Navbar Biru + Tabel Putih).
   - Skeleton Loading & Empty State Guide.
2. Logic:
   - Pencarian Fleksibel (Loose Hierarchy).
   - Auto-Select (Jika 1 hasil, otomatis pilih).
   - Exact Match (Jika hasil klik, cari persis).
   - URL State (Menyimpan hasil pencarian di URL browser).
3. Performa:
   - Gzip Compression.
   - Browser Caching.
   - Pandas Vectorized Search.

Cara Pakai:
1. Simpan file ini sebagai 'data_master.py'.
2. Simpan file CSV sebagai 'master.csv'.
3. Simpan file logo sebagai 'logo_bps.png' (atau sesuaikan variabel LOGO_FILENAME).
4. Jalankan: python data_master.py
"""

import logging
import re
import os
from functools import lru_cache
from typing import List, Dict

import pandas as pd
import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

# ==========================================
# 1. KONFIGURASI & ASSETS
# ==========================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Master Wilayah Indonesia",
    version="25.0.0",
    docs_url=None, 
    redoc_url=None
)

app.add_middleware(GZipMiddleware, minimum_size=500)

# KONFIGURASI NAMA FILE LOGO (Ganti jika nama file Anda beda)
LOGO_FILENAME = "logo_bps.png" 

# Mount folder static untuk serve gambar
app.mount("/static", StaticFiles(directory="."), name="static")

DATA_PATH = "master.csv"
df_master: pd.DataFrame = pd.DataFrame()

# ==========================================
# 2. DATA LOADING
# ==========================================
def load_data() -> None:
    global df_master
    
    if os.path.exists(LOGO_FILENAME):
        logger.info(f"✅ File logo '{LOGO_FILENAME}' ditemukan.")
    else:
        logger.warning(f"⚠️ File logo '{LOGO_FILENAME}' TIDAK ditemukan. Pastikan file ada di folder yang sama.")

    try:
        logger.info(f"Memuat data dari {DATA_PATH}...")
        df = pd.read_csv(DATA_PATH, dtype=str).fillna("")
        
        df["kode_prov"] = df["kode_prov"].str.strip().str.zfill(2)
        df["kode_kab"] = df["kode_kab"].str.strip().str.zfill(2)
        df["kode_kec"] = df["kode_kec"].str.strip().str.zfill(3)
        df["kode_desa"] = df["kode_desa"].str.strip().str.zfill(3)
        
        df["_search_prov"] = df["nama_prov"].str.lower()
        df["_search_kab"] = df["kab_nama"].str.lower()
        df["_search_kec"] = df["kec_nama"].str.lower()
        df["_search_desa"] = df["desa_nama"].str.lower()
        
        df_master = df
        logger.info(f"✅ Data siap: {len(df_master)} baris.")
    except Exception as e:
        logger.error(f"❌ Gagal memuat data: {str(e)}")
        df_master = pd.DataFrame()

load_data()

# ==========================================
# 3. LOGIKA BISNIS
# ==========================================
def highlight_text(text: str, query: str) -> str:
    if not query or len(query) < 2: return text
    safe_query = re.escape(query)
    return re.sub(f"({safe_query})", r'<mark class="bg-yellow-200 dark:bg-yellow-900/60 dark:text-yellow-100 rounded-sm px-0.5">\1</mark>', text, flags=re.IGNORECASE)

@lru_cache(maxsize=1024) 
def get_cached_suggestions(level: str, query: str, prov: str, kab: str, kec: str) -> List[Dict[str, str]]:
    if df_master.empty: return []
    subset = df_master
    
    if prov: subset = subset[subset["kode_prov"] == prov]
    if kab: subset = subset[subset["kode_kab"] == kab]
    if kec: subset = subset[subset["kode_kec"] == kec]
    if subset.empty: return []

    config = {
        "prov":      {"code": "kode_prov", "name": "nama_prov", "search": "_search_prov"},
        "kabupaten": {"code": "kode_kab",  "name": "kab_nama",  "search": "_search_kab"},
        "kecamatan": {"code": "kode_kec",  "name": "kec_nama",  "search": "_search_kec"},
        "desa":      {"code": "kode_desa", "name": "desa_nama", "search": "_search_desa"},
    }
    
    cfg = config.get(level)
    if not cfg: return []

    q = query.strip().lower()
    col_code = cfg["code"]
    col_name = cfg["name"]
    
    if q:
        if q.isdigit():
            subset = subset[subset[col_code].str.contains(q, na=False)]
        else:
            col_search = cfg["search"]
            if len(q) == 1: subset = subset[subset[col_search].str.startswith(q, na=False)]
            else: subset = subset[subset[col_search].str.contains(q, na=False)]
    
    return subset[[col_code, col_name]].drop_duplicates().sort_values(col_code).head(20).to_dict(orient="records")

# ==========================================
# 4. API ENDPOINTS
# ==========================================

@app.get("/search", response_class=HTMLResponse)
async def api_search_table(
    response: Response,
    prov: str = "", prov_exact: bool = False,
    kab: str = "", kab_exact: bool = False,
    kec: str = "", kec_exact: bool = False,
    desa: str = "", desa_exact: bool = False,
    expand: bool = False
):
    response.headers["Cache-Control"] = "public, max-age=3600"

    if df_master.empty:
        return "<div class='p-6 text-center text-red-600 font-bold bg-red-50 rounded-lg'>❌ Database belum dimuat.</div>"

    # EMPTY STATE GUIDE
    if not any([prov, kab, kec, desa]):
        return """
        <div class="flex flex-col items-center justify-center py-20 text-center animate-fade-in">
            <div class="bg-blue-50 dark:bg-slate-800/50 p-5 rounded-full mb-6 shadow-sm ring-1 ring-blue-100 dark:ring-slate-700 transition-all duration-500">
                <svg class="w-12 h-12 text-blue-500 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                </svg>
            </div>
            <h3 class="text-xl font-bold text-slate-800 dark:text-slate-200 mb-2 tracking-tight">Menunggu Pencarian</h3>
            <p class="text-slate-500 dark:text-slate-400 max-w-md mx-auto text-sm leading-relaxed">
                Silakan ketik nama atau kode <strong class="text-blue-600 dark:text-blue-400">Wilayah</strong>
                pada kolom di atas untuk menampilkan Kode Wilayah.
            </p>
        </div>
        """

    subset = df_master.copy()
    
    def apply_filter(df, val, is_exact, col_code, col_search, code_len):
        if not val: return df
        val = val[:50] 
        if val.isdigit() and len(val) == code_len: return df[df[col_code] == val]
        val_lower = val.lower()
        if is_exact: return df[df[col_search] == val_lower]
        else: return df[df[col_search].str.contains(val_lower, na=False)]

    subset = apply_filter(subset, prov, prov_exact, "kode_prov", "_search_prov", 2)
    subset = apply_filter(subset, kab, kab_exact, "kode_kab", "_search_kab", 2)
    subset = apply_filter(subset, kec, kec_exact, "kode_kec", "_search_kec", 3)
    subset = apply_filter(subset, desa, desa_exact, "kode_desa", "_search_desa", 3)

    if subset.empty:
        return """
        <div class="flex flex-col items-center justify-center py-16 text-slate-400 dark:text-slate-500 animate-fade-in">
            <svg class="w-16 h-16 mb-4 opacity-25" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <p class="text-lg font-medium">Data tidak ditemukan.</p>
        </div>
        """

    view_level = 4 
    if not desa:
        if kec: view_level = 3
        elif kab: view_level = 2
        elif prov: view_level = 1
        else: view_level = 4

    if expand and view_level < 4: view_level += 1

    if view_level == 1: subset = subset.drop_duplicates(subset=['kode_prov'])
    elif view_level == 2: subset = subset.drop_duplicates(subset=['kode_prov', 'kode_kab'])
    elif view_level == 3: subset = subset.drop_duplicates(subset=['kode_prov', 'kode_kab', 'kode_kec'])
    
    LIMIT = 100
    total_found = len(subset)
    subset = subset.head(LIMIT)
    rows_html = []

    for _, row in subset.iterrows():
        k_prov, k_kab = row['kode_prov'], row['kode_kab']
        k_kec, k_desa = row['kode_kec'], row['kode_desa']
        
        n_prov = highlight_text(row['nama_prov'], prov if not prov_exact else "")
        n_kab = highlight_text(row['kab_nama'], kab if not kab_exact else "")
        n_kec = highlight_text(row['kec_nama'], kec if not kec_exact else "")
        n_desa = highlight_text(row['desa_nama'], desa if not desa_exact else "")

        # --- UI FIXES: min-w, no-wrap for codes ---
        td_content = f'<td class="px-3 lg:px-4 py-3 text-sm font-semibold text-slate-700 dark:text-slate-200 align-middle min-w-[140px]" data-label="Provinsi">{n_prov}</td>'
        if view_level >= 2: td_content += f'<td class="px-3 lg:px-4 py-3 text-sm text-slate-600 dark:text-slate-300 align-middle min-w-[140px]" data-label="Kab/Kota">{n_kab}</td>'
        if view_level >= 3: td_content += f'<td class="px-3 lg:px-4 py-3 text-sm text-slate-600 dark:text-slate-300 align-middle min-w-[140px]" data-label="Kecamatan">{n_kec}</td>'
        if view_level >= 4: td_content += f'<td class="px-3 lg:px-4 py-3 text-sm text-slate-600 dark:text-slate-300 align-middle min-w-[140px]" data-label="Desa">{n_desa}</td>'

        td_content += f'<td class="px-3 lg:px-4 py-3 text-center align-middle whitespace-nowrap" data-label="Kode Prov"><span class="inline-block px-2 py-0.5 font-mono text-xs font-bold text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/40 rounded border border-blue-100 dark:border-blue-800/50">{k_prov}</span></td>'
        if view_level >= 2: td_content += f'<td class="px-3 lg:px-4 py-3 text-center align-middle whitespace-nowrap" data-label="Kode Kab"><span class="inline-block px-2 py-0.5 font-mono text-xs font-bold text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/40 rounded border border-blue-100 dark:border-blue-800/50">{k_kab}</span></td>'
        if view_level >= 3: td_content += f'<td class="px-3 lg:px-4 py-3 text-center align-middle whitespace-nowrap" data-label="Kode Kec"><span class="inline-block px-2 py-0.5 font-mono text-xs font-bold text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/40 rounded border border-blue-100 dark:border-blue-800/50">{k_kec}</span></td>'
        if view_level >= 4: td_content += f'<td class="px-3 lg:px-4 py-3 text-center align-middle whitespace-nowrap" data-label="Kode Desa"><span class="inline-block px-2 py-0.5 font-mono text-xs font-bold text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/40 rounded border border-blue-100 dark:border-blue-800/50">{k_desa}</span></td>'

        td_content += f"""
            <td class="px-3 lg:px-4 py-3 text-center align-middle whitespace-nowrap" data-label="Aksi">
                <button class="btn-copy group/btn relative inline-flex items-center justify-center p-2 text-slate-400 dark:text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-white dark:hover:bg-slate-700 border border-transparent hover:border-blue-100 dark:hover:border-slate-600 hover:shadow-sm rounded-lg transition-all active:scale-95"
                        data-prov="{k_prov}" data-kab="{k_kab if view_level >= 2 else ''}" data-kec="{k_kec if view_level >= 3 else ''}" data-desa="{k_desa if view_level >= 4 else ''}"
                        title="Salin Kode">
                    <svg class="w-5 h-5 transition-transform group-hover/btn:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path></svg>
                </button>
            </td>
        """
        rows_html.append(f'<tr class="bg-white dark:bg-slate-800 hover:bg-blue-50/40 dark:hover:bg-slate-700/50 border-b border-slate-100 dark:border-slate-700/60 last:border-0 transition-colors duration-150 group relative">{td_content}</tr>')

    header_html = '<th class="px-3 lg:px-4 py-4 tracking-wider whitespace-nowrap text-left">PROVINSI</th>'
    if view_level >= 2: header_html += '<th class="px-3 lg:px-4 py-4 tracking-wider whitespace-nowrap text-left">KAB/KOTA</th>'
    if view_level >= 3: header_html += '<th class="px-3 lg:px-4 py-4 tracking-wider whitespace-nowrap text-left">KECAMATAN</th>'
    if view_level >= 4: header_html += '<th class="px-3 lg:px-4 py-4 tracking-wider whitespace-nowrap text-left">DESA</th>'
    
    header_html += '<th class="px-3 lg:px-4 py-4 text-center whitespace-nowrap">KODE PROV</th>'
    if view_level >= 2: header_html += '<th class="px-3 lg:px-4 py-4 text-center whitespace-nowrap">KODE KAB</th>'
    if view_level >= 3: header_html += '<th class="px-3 lg:px-4 py-4 text-center whitespace-nowrap">KODE KEC</th>'
    if view_level >= 4: header_html += '<th class="px-3 lg:px-4 py-4 text-center whitespace-nowrap">KODE DESA</th>'
    header_html += '<th class="px-3 lg:px-4 py-4 text-center whitespace-nowrap">AKSI</th>'

    info_limit = f"<div class='px-4 py-3 text-xs font-medium text-center bg-blue-50/50 text-blue-800 dark:bg-slate-800 dark:text-slate-400 border-b border-blue-100 dark:border-slate-700'>Menampilkan <strong>{LIMIT}</strong> data teratas dari total <strong>{total_found}</strong> data ditemukan.</div>" if total_found > LIMIT else ""

    return f"""
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 overflow-hidden ring-1 ring-black/5 animate-fade-in">
        {info_limit}
        <div class="overflow-x-auto">
            <table class="w-full text-sm text-left responsive-table">
                <thead class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase bg-slate-50/80 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-10 backdrop-blur-sm">
                    <tr>{header_html}</tr>
                </thead>
                <tbody class="divide-y divide-slate-100 dark:divide-slate-700">{"".join(rows_html)}</tbody>
            </table>
        </div>
    </div>
    """

@app.get("/{level}")
async def api_get_suggestions(level: str, query: str = "", prov: str = "", kabupaten: str = "", kecamatan: str = ""):
    if level not in ["prov", "kabupaten", "kecamatan", "desa"]: return JSONResponse([])
    results = get_cached_suggestions(level, query, prov, kabupaten, kecamatan)
    return JSONResponse([{"kode": r[list(r.keys())[0]], "nama": r[list(r.keys())[1]]} for r in results])

# ==========================================
# 5. FRONTEND TEMPLATE
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Wilayah Indonesia</title>
    <meta name="description" content="Cari kode wilayah administrasi Indonesia.">
    <link rel="icon" type="image/png" href="/static/{logo_filename}">
    
    <meta property="og:image" content="/static/{logo_filename}">
    
    <link rel="preconnect" href="https://cdn.tailwindcss.com">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = { darkMode: 'class', theme: { extend: { fontFamily: { sans: ['Inter', 'sans-serif'] } } } }
    </script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
    
    <style>
        body { font-family: 'Inter', sans-serif; }
        *:focus-visible { outline: 2px solid #3b82f6; outline-offset: 2px; }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
        .dark ::-webkit-scrollbar-thumb { background: #475569; }
        ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
        
        @keyframes slideUpFade { from { transform: translateY(10px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .animate-fade-in { animation: slideUpFade 0.4s ease-out forwards; }

        .toggle-checkbox:checked { right: 0; border-color: #2563eb; }
        .toggle-checkbox:checked + .toggle-label { background-color: #2563eb; }
        
        @media (max-width: 1024px) {
            .responsive-table thead { display: none; }
            .responsive-table, .responsive-table tbody, .responsive-table tr, .responsive-table td { display: block; width: 100%; }
            .responsive-table tr { margin-bottom: 1rem; border-radius: 0.75rem; padding: 1.25rem; position: relative; }
            .responsive-table td { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0; border-bottom: 1px dashed #e2e8f0; text-align: right; }
            .dark .responsive-table td { border-bottom-color: #334155; }
            .responsive-table td:last-child { border-bottom: none; padding-top: 1.25rem; justify-content: flex-end; }
            .responsive-table td::before { content: attr(data-label); font-weight: 700; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; margin-right: 1rem; opacity: 0.7; }
        }
    </style>
</head>
<body class="min-h-screen flex flex-col bg-slate-50 text-slate-900 dark:bg-slate-900 dark:text-slate-100 transition-colors duration-300">

    <nav class="bg-blue-800 border-b border-blue-900 sticky top-0 z-40 shadow-lg shadow-blue-900/10 dark:border-slate-700">
        <div class="w-full max-w-[96%] mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16 items-center">
                <div class="flex items-center gap-3.5">
                    <div class="h-11 w-11 bg-white rounded-lg flex items-center justify-center shadow-sm border border-white/10">
                        <img src="/static/{logo_filename}" alt="Logo" class="h-full w-full object-contain p-1">
                    </div>
                    
                    <div>
                        <h1 class="text-lg font-bold text-white tracking-tight leading-none">Master Wilayah</h1>
                        <p class="text-[11px] text-blue-200 font-medium mt-0.5 opacity-90 tracking-wide">INDONESIA DATABASE</p>
                    </div>
                </div>
                
                <div class="flex items-center gap-3">
                    <button id="theme-toggle" class="p-2 rounded-lg bg-blue-700 text-white hover:bg-blue-600 transition-colors border border-blue-600 shadow-sm" aria-label="Toggle Dark Mode">
                        <svg id="theme-toggle-light-icon" class="hidden w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clip-rule="evenodd"></path></svg>
                        <svg id="theme-toggle-dark-icon" class="hidden w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path></svg>
                    </button>
                    <button onclick="resetFilter()" class="text-xs font-semibold text-white bg-blue-700 hover:bg-blue-600 px-4 py-2.5 rounded-lg transition-all border border-blue-600 shadow-sm hover:shadow-md active:scale-95">Reset</button>
                </div>
            </div>
        </div>
    </nav>

    <main class="flex-grow w-full max-w-[96%] mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 mb-8 transition-colors">
            <div class="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
                <div class="flex items-center gap-4">
                    <h2 class="text-sm font-bold text-slate-700 dark:text-slate-200 uppercase tracking-widest flex items-center gap-2">
                        <svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"></path></svg> Filter Pencarian
                    </h2>
                    <div id="expand-container" class="hidden items-center gap-2 transition-all">
                        <span class="text-xs text-slate-400">|</span>
                        <label for="expand-toggle" class="flex items-center cursor-pointer relative">
                            <input type="checkbox" id="expand-toggle" class="sr-only" onchange="loadResults(true)">
                            <div class="toggle-label w-9 h-5 bg-slate-200 dark:bg-slate-600 rounded-full border border-slate-300 dark:border-slate-500 shadow-inner transition-colors duration-200 ease-in-out"></div>
                            <div class="dot absolute left-0.5 top-0.5 bg-white w-4 h-4 rounded-full shadow transition-transform duration-200 ease-in-out peer-checked:translate-x-full peer-checked:border-white"></div>
                            <span id="expand-label" class="ml-2 text-xs font-semibold text-blue-600 dark:text-blue-400">Tampilkan Detail</span>
                        </label>
                    </div>
                </div>
                <div class="hidden md:flex items-center gap-2 text-[10px] text-slate-400 dark:text-slate-500 bg-slate-50 dark:bg-slate-700/50 px-3 py-1.5 rounded-full border border-slate-100 dark:border-slate-700">
                    <span>Navigasi:</span>
                    <kbd class="font-sans font-bold text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-600 px-1 rounded border border-slate-200 dark:border-slate-500">⬆</kbd>
                    <kbd class="font-sans font-bold text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-600 px-1 rounded border border-slate-200 dark:border-slate-500">⬇</kbd>
                    <span class="mx-0.5">+</span>
                    <kbd class="font-sans font-bold text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-600 px-1 rounded border border-slate-200 dark:border-slate-500">Enter</kbd>
                </div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
                <div class="relative group">
                    <label class="block text-[11px] font-bold text-slate-400 dark:text-slate-500 mb-1.5 uppercase tracking-wider">Provinsi</label>
                    <div class="relative"><input id="prov" type="text" placeholder="Ketik provinsi..." class="w-full pl-3 pr-9 py-2.5 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm shadow-sm transition-all" autocomplete="off"><button onclick="clearLevel('prov')" class="absolute right-2 top-2.5 text-slate-300 dark:text-slate-500 hover:text-red-500 transition hidden p-1" id="btn_clear_prov">✕</button></div>
                    <div id="prov_list" class="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl max-h-60 overflow-y-auto hidden"></div>
                </div>
                <div class="relative group"><label class="block text-[11px] font-bold text-slate-400 dark:text-slate-500 mb-1.5 uppercase tracking-wider">Kabupaten/Kota</label><div class="relative"><input id="kabupaten" type="text" placeholder="Ketik kab/kota..." class="w-full pl-3 pr-9 py-2.5 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm shadow-sm transition-all disabled:bg-slate-50 dark:disabled:bg-slate-800 disabled:text-slate-400" autocomplete="off"><button onclick="clearLevel('kabupaten')" class="absolute right-2 top-2.5 text-slate-300 dark:text-slate-500 hover:text-red-500 transition hidden p-1" id="btn_clear_kabupaten">✕</button></div><div id="kabupaten_list" class="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl max-h-60 overflow-y-auto hidden"></div></div>
                <div class="relative group"><label class="block text-[11px] font-bold text-slate-400 dark:text-slate-500 mb-1.5 uppercase tracking-wider">Kecamatan</label><div class="relative"><input id="kecamatan" type="text" placeholder="Ketik kecamatan..." class="w-full pl-3 pr-9 py-2.5 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm shadow-sm transition-all disabled:bg-slate-50 dark:disabled:bg-slate-800 disabled:text-slate-400" autocomplete="off"><button onclick="clearLevel('kecamatan')" class="absolute right-2 top-2.5 text-slate-300 dark:text-slate-500 hover:text-red-500 transition hidden p-1" id="btn_clear_kecamatan">✕</button></div><div id="kecamatan_list" class="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl max-h-60 overflow-y-auto hidden"></div></div>
                <div class="relative group"><label class="block text-[11px] font-bold text-slate-400 dark:text-slate-500 mb-1.5 uppercase tracking-wider">Desa/Kelurahan</label><div class="relative"><input id="desa" type="text" placeholder="Ketik desa..." class="w-full pl-3 pr-9 py-2.5 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm shadow-sm transition-all disabled:bg-slate-50 dark:disabled:bg-slate-800 disabled:text-slate-400" autocomplete="off"><button onclick="clearLevel('desa')" class="absolute right-2 top-2.5 text-slate-300 dark:text-slate-500 hover:text-red-500 transition hidden p-1" id="btn_clear_desa">✕</button></div><div id="desa_list" class="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl max-h-60 overflow-y-auto hidden"></div></div>
            </div>
        </div>

        <div id="loading" class="hidden">
            <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 animate-pulse">
                <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/4 mb-6"></div>
                <div class="space-y-3">
                    <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded"></div>
                    <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-5/6"></div>
                    <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-4/6"></div>
                </div>
            </div>
        </div>

        <div id="hasil" class="min-h-[200px] transition-opacity duration-300" aria-live="polite"></div>
    </main>

    <footer class="bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 py-8 mt-auto transition-colors">
        <div class="max-w-7xl mx-auto px-4 text-center">
            <p class="text-sm text-slate-500 dark:text-slate-400">&copy; 2025 Master Wilayah Indonesia <span class="mx-2 text-slate-300"></span></p>
        </div>
    </footer>

    <script>
        // --- THEME LOGIC ---
        const themeBtn = document.getElementById('theme-toggle');
        if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark'); document.getElementById('theme-toggle-light-icon').classList.remove('hidden');
        } else {
            document.documentElement.classList.remove('dark'); document.getElementById('theme-toggle-dark-icon').classList.remove('hidden');
        }
        themeBtn.addEventListener('click', () => {
            document.getElementById('theme-toggle-dark-icon').classList.toggle('hidden');
            document.getElementById('theme-toggle-light-icon').classList.toggle('hidden');
            if (document.documentElement.classList.contains('dark')) { document.documentElement.classList.remove('dark'); localStorage.setItem('color-theme', 'light'); }
            else { document.documentElement.classList.add('dark'); localStorage.setItem('color-theme', 'dark'); }
        });

        // --- URL STATE SYNC ---
        function syncURL(params) {
            const url = new URL(window.location);
            for (const [key, value] of Object.entries(params)) { if(value) url.searchParams.set(key, value); else url.searchParams.delete(key); }
            window.history.replaceState({}, '', url);
        }
        
        function restoreFromURL() {
            const params = new URLSearchParams(window.location.search);
            let hasData = false;
            ['prov', 'kabupaten', 'kecamatan', 'desa'].forEach(id => {
                const val = params.get(id); if (val) { document.getElementById(id).value = val; hasData = true; }
            });
            // FORCE LOAD: Even if empty, we want to show the "Guide" state
            loadResults();
        }

        // --- SEARCH LOGIC ---
        let focusIndex = -1;
        const debounce = (func, wait) => { let t; return (...args) => { clearTimeout(t); t = setTimeout(() => func.apply(this, args), wait); }; };
        function showLoading(show) { document.getElementById("loading").classList.toggle("hidden", !show); const hasil = document.getElementById("hasil"); if(show) hasil.classList.add("opacity-40"); else hasil.classList.remove("opacity-40"); }
        const getValue = (id) => { const el = document.getElementById(id); return el.dataset.kode || el.value; }

        function updateToggleState() {
            const prov = getValue('prov'); const kab = getValue('kabupaten');
            const kec = getValue('kecamatan'); const desa = getValue('desa');
            const container = document.getElementById('expand-container');
            const label = document.getElementById('expand-label');
            const toggle = document.getElementById('expand-toggle');

            if (prov && !kab) { container.classList.remove('hidden'); container.classList.add('flex'); label.textContent = "Tampilkan Kabupaten/Kota"; } 
            else if (kab && !kec) { container.classList.remove('hidden'); container.classList.add('flex'); label.textContent = "Tampilkan Kecamatan"; } 
            else if (kec && !desa) { container.classList.remove('hidden'); container.classList.add('flex'); label.textContent = "Tampilkan Desa"; } 
            else { container.classList.add('hidden'); container.classList.remove('flex'); toggle.checked = false; }
        }

        function setupListeners(level, nextLevel) {
            const input = document.getElementById(level);
            input.addEventListener('input', debounce(async (e) => {
                const query = e.target.value.trim();
                document.getElementById("btn_clear_" + level).classList.toggle("hidden", query.length === 0);
                input.dataset.exact = "false"; input.dataset.kode = ""; 
                loadResults(true);
                if (!query) { document.getElementById(level + "_list").classList.add("hidden"); return; }
                await fetchAndRender(level, nextLevel, query);
            }, 300));
            input.addEventListener('keydown', (e) => {
                const list = document.getElementById(level + "_list");
                const items = list.querySelectorAll(".suggestion-item");
                if (list.classList.contains("hidden") || items.length === 0) return;
                if (e.key === "ArrowDown") { e.preventDefault(); focusIndex++; if (focusIndex >= items.length) focusIndex = 0; setActive(items); }
                else if (e.key === "ArrowUp") { e.preventDefault(); focusIndex--; if (focusIndex < 0) focusIndex = items.length - 1; setActive(items); }
                else if (e.key === "Enter") { e.preventDefault(); if (focusIndex > -1 && items[focusIndex]) items[focusIndex].click(); }
                else if (e.key === "Escape") list.classList.add("hidden");
            });
        }

        function setActive(items) {
            items.forEach(item => { item.classList.remove("bg-blue-50", "text-blue-700", "dark:bg-slate-700", "dark:text-white"); });
            if (items[focusIndex]) { items[focusIndex].classList.add("bg-blue-50", "text-blue-700", "dark:bg-slate-700", "dark:text-white"); items[focusIndex].scrollIntoView({ block: "nearest" }); }
        }

        async function fetchAndRender(level, nextLevel, query) {
            const params = new URLSearchParams({ query, prov: document.getElementById("prov").dataset.kode || "", kabupaten: document.getElementById("kabupaten").dataset.kode || "", kecamatan: document.getElementById("kecamatan").dataset.kode || "" });
            try { const res = await fetch(`/${level}?${params.toString()}`); const data = await res.json(); renderSuggestions(data, level, nextLevel); } catch (err) {}
        }

        function renderSuggestions(data, level, nextLevel) {
            const list = document.getElementById(level + "_list"); list.innerHTML = ""; focusIndex = -1;
            if (data.length === 0) { list.classList.add("hidden"); return; }
            if (data.length === 1) { selectItem(level, nextLevel, data[0].kode, data[0].nama); return; }
            list.classList.remove("hidden");
            data.forEach((d) => {
                const div = document.createElement("div");
                div.className = "suggestion-item px-4 py-2.5 cursor-pointer text-sm text-slate-700 dark:text-slate-300 flex justify-between items-center border-b border-slate-50 dark:border-slate-700 last:border-0 hover:bg-blue-50 dark:hover:bg-slate-700 transition-colors";
                div.innerHTML = `<span class="font-medium">${d.nama}</span><span class="text-xs font-mono font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-slate-900 px-2 py-0.5 rounded border border-blue-100 dark:border-slate-600">${d.kode}</span>`;
                div.onclick = () => selectItem(level, nextLevel, d.kode, d.nama);
                list.appendChild(div);
            });
        }

        function selectItem(level, nextLevel, kode, nama) {
            const input = document.getElementById(level);
            input.value = nama; input.dataset.exact = "true";
            const provVal = document.getElementById("prov").dataset.kode;
            const kabVal = document.getElementById("kabupaten").dataset.kode;
            const kecVal = document.getElementById("kecamatan").dataset.kode;
            let useCode = true;
            if (level === "kabupaten" && !provVal) useCode = false;
            if (level === "kecamatan" && !kabVal) useCode = false;
            if (level === "desa" && !kecVal) useCode = false;
            if (useCode) input.dataset.kode = kode; else input.dataset.kode = ""; 
            document.getElementById(level + "_list").classList.add("hidden");
            document.getElementById("btn_clear_" + level).classList.remove("hidden");
            loadResults(true);
            if (nextLevel) { const nextInput = document.getElementById(nextLevel); if (nextInput && !nextInput.disabled) nextInput.focus(); }
        }

        const loadResults = debounce(async (updateUrl = false) => {
            showLoading(true);
            try { 
                updateToggleState(); 
                const expand = document.getElementById('expand-toggle').checked;
                const currentValues = { prov: document.getElementById('prov').value, kabupaten: document.getElementById('kabupaten').value, kecamatan: document.getElementById('kecamatan').value, desa: document.getElementById('desa').value };
                if(updateUrl) syncURL(currentValues);

                const params = new URLSearchParams({ 
                    prov: getValue('prov'), prov_exact: document.getElementById("prov").dataset.exact === "true",
                    kab: getValue('kabupaten'), kab_exact: document.getElementById("kabupaten").dataset.exact === "true",
                    kec: getValue('kecamatan'), kec_exact: document.getElementById("kecamatan").dataset.exact === "true",
                    desa: getValue('desa'), desa_exact: document.getElementById("desa").dataset.exact === "true",
                    expand: expand 
                });
                const res = await fetch(`/search?${params.toString()}`); 
                const html = await res.text(); 
                document.getElementById("hasil").innerHTML = html; 
            } catch (err) { } finally { showLoading(false); }
        }, 400);

        function clearLevel(level) {
            const el = document.getElementById(level); el.value = ""; el.dataset.kode = ""; el.dataset.exact = "false";
            document.getElementById("btn_clear_" + level).classList.add("hidden");
            document.getElementById('expand-toggle').checked = false; 
            loadResults(true);
        }
        
        function resetFilter() {
            ['prov', 'kabupaten', 'kecamatan', 'desa'].forEach(id => {
                const el = document.getElementById(id); el.value = ""; el.dataset.kode = ""; el.dataset.exact = "false";
                document.getElementById("btn_clear_" + id).classList.add("hidden");
            });
            document.getElementById('expand-toggle').checked = false;
            loadResults(true);
        }

        document.addEventListener('click', function(e) {
            if (!e.target.closest('.relative.group')) document.querySelectorAll('[id$="_list"]').forEach(el => el.classList.add('hidden'));
            if (e.target.id === 'expand-toggle') {
                const dot = e.target.nextElementSibling.nextElementSibling;
                if(e.target.checked) { dot.classList.add('translate-x-full', 'border-white'); } 
                else { dot.classList.remove('translate-x-full', 'border-white'); }
            }
            const btn = e.target.closest('.btn-copy');
            if (btn) {
                const { prov, kab, kec, desa } = btn.dataset;
                let text = `'${prov}`; if(kab) text += `\t'${kab}`; if(kec) text += `\t'${kec}`; if(desa) text += `\t'${desa}`;
                navigator.clipboard.writeText(text).then(() => {
                    const originalHTML = btn.innerHTML;
                    btn.innerHTML = `<svg class="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path></svg>`;
                    btn.classList.add("bg-emerald-50", "border-emerald-100");
                    setTimeout(() => { btn.innerHTML = originalHTML; btn.classList.remove("bg-emerald-50", "border-emerald-100"); }, 1500);
                });
            }
        });

        setupListeners('prov', 'kabupaten'); setupListeners('kabupaten', 'kecamatan'); setupListeners('kecamatan', 'desa'); setupListeners('desa', null);
        restoreFromURL(); 
    </script>
</body>
</html>
""".replace("{logo_filename}", LOGO_FILENAME)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return HTML_TEMPLATE

# ==========================================
# 6. SERVER RUN
# ==========================================
if __name__ == "__main__":
    logger.info("🚀 Memulai server di http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)