"""Design system — tokens + component styles layered on Streamlit's theme.

Colour tokens
  primary  #2563EB   secondary #1E293B   background #F8FAFC
  surface  #FFFFFF   border    #E2E8F0   text       #0F172A
"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --dm-primary: #2563EB;
  --dm-primary-50: #EFF6FF;
  --dm-primary-100: #DBEAFE;
  --dm-secondary: #1E293B;
  --dm-bg: #F8FAFC;
  --dm-surface: #FFFFFF;
  --dm-border: #E2E8F0;
  --dm-border-strong: #CBD5E1;
  --dm-text: #0F172A;
  --dm-text-2: #475569;
  --dm-text-3: #64748B;
  --dm-muted: #94A3B8;
  --dm-success: #059669; --dm-success-bg: #ECFDF5;
  --dm-warning: #B45309; --dm-warning-bg: #FFFBEB;
  --dm-danger:  #DC2626; --dm-danger-bg:  #FEF2F2;
  --dm-radius: 12px;
  --dm-radius-sm: 8px;
  --dm-shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
  --dm-shadow: 0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04);
  --dm-shadow-lg: 0 10px 30px -12px rgba(15, 23, 42, 0.18);
}

/* Base font comes from .streamlit/config.toml; don't override globally or icon fonts break. */
body { -webkit-font-smoothing: antialiased; }
[class^="dm-"], [class*=" dm-"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
.dm-ico { display: block; }

/* ---------- App frame --------------------------------------------------- */
[data-testid="stHeader"] { background: transparent; height: 0; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stMainBlockContainer"], .block-container {
  max-width: 1320px; padding: 3.25rem 2.25rem 4rem 2.25rem; /* room for the host toolbar */
}
h1, h2, h3, h4 { color: var(--dm-text); letter-spacing: -0.015em; }
hr { border-color: var(--dm-border) !important; margin: 0.75rem 0 !important; }

/* ---------- Sidebar ----------------------------------------------------- */
[data-testid="stSidebar"] { box-shadow: none; }
[data-testid="stSidebarNav"] { padding-top: 0.25rem; }
[data-testid="stNavSectionHeader"], [data-testid="stSidebarNavSeparator"] + div span {
  font-size: 0.6875rem !important; font-weight: 600 !important; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--dm-muted) !important;
}
[data-testid="stSidebarNavLink"] {
  border-radius: var(--dm-radius-sm); padding: 0.4rem 0.65rem; margin: 1px 0;
  font-weight: 500; color: var(--dm-text-2);
}
[data-testid="stSidebarNavLink"]:hover { background: var(--dm-bg); }
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: var(--dm-primary-50); color: var(--dm-primary);
}
[data-testid="stSidebarNavLink"][aria-current="page"] span { color: var(--dm-primary) !important; font-weight: 600; }

.dm-side-card {
  border: 1px solid var(--dm-border); border-radius: var(--dm-radius); padding: 0.85rem 0.9rem;
  background: var(--dm-bg); font-size: 0.8125rem; color: var(--dm-text-2);
}
.dm-side-card b { color: var(--dm-text); font-weight: 600; }
.dm-side-meter { height: 6px; border-radius: 999px; background: var(--dm-border); margin: 0.55rem 0 0.35rem; overflow: hidden; }
.dm-side-meter > span { display: block; height: 100%; background: var(--dm-primary); border-radius: 999px; }
.dm-side-foot { font-size: 0.75rem; color: var(--dm-muted); padding: 0.25rem 0.1rem; }
.dm-side-foot a { color: var(--dm-text-3); text-decoration: none; }

/* ---------- Top bar ----------------------------------------------------- */
.st-key-topbar {
  background: var(--dm-surface); border: 1px solid var(--dm-border); border-radius: var(--dm-radius);
  padding: 0.45rem 0.6rem; box-shadow: var(--dm-shadow-sm); margin-bottom: 0.5rem;
}
.st-key-topbar [data-testid="stSelectbox"] div[data-baseweb="select"] > div { font-weight: 600; }
.st-key-topbar [data-testid="stPopover"] button { border: 1px solid var(--dm-border); }
.st-key-topbar .dm-avatar-label { font-weight: 600; }

/* ---------- Page header / breadcrumbs ---------------------------------- */
.dm-breadcrumb { display: flex; align-items: center; gap: 0.4rem; font-size: 0.8125rem; color: var(--dm-text-3); margin: 0.5rem 0 0.35rem; flex-wrap: wrap; }
.dm-breadcrumb .sep { color: var(--dm-border-strong); }
.dm-breadcrumb .current { color: var(--dm-text); font-weight: 500; }
.dm-page-title { font-size: 1.625rem; font-weight: 650; letter-spacing: -0.02em; color: var(--dm-text); margin: 0; line-height: 1.25; }
.dm-page-sub { color: var(--dm-text-3); font-size: 0.9375rem; margin: 0.3rem 0 0.25rem; }

/* ---------- Cards ------------------------------------------------------- */
[class*="st-key-card"] {
  background: var(--dm-surface); border: 1px solid var(--dm-border); border-radius: var(--dm-radius);
  padding: 1.15rem 1.25rem; box-shadow: var(--dm-shadow);
}
.dm-card-title { font-size: 0.9375rem; font-weight: 600; color: var(--dm-text); margin: 0; }
.dm-card-sub { font-size: 0.8125rem; color: var(--dm-text-3); margin: 0.15rem 0 0; }
.dm-card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 0.35rem; }

/* Welcome banner */
.st-key-card-welcome { background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFF 100%); }
.dm-eyebrow { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--dm-primary); }

/* ---------- Stat cards -------------------------------------------------- */
.dm-stat-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1rem; }
@media (max-width: 1024px) { .dm-stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem; } }
.dm-stat { background: var(--dm-surface); border: 1px solid var(--dm-border); border-radius: var(--dm-radius);
  padding: 1rem 1.1rem; box-shadow: var(--dm-shadow); height: 100%; }
.dm-stat-top { display: flex; justify-content: space-between; align-items: center; }
.dm-stat-label { font-size: 0.8125rem; color: var(--dm-text-3); font-weight: 500; }
.dm-stat-icon { width: 30px; height: 30px; border-radius: 8px; background: var(--dm-primary-50); color: var(--dm-primary);
  display: grid; place-items: center; }
.dm-stat-value { font-size: 1.75rem; font-weight: 650; letter-spacing: -0.02em; color: var(--dm-text); margin-top: 0.35rem; line-height: 1.2; }
.dm-stat-foot { font-size: 0.75rem; color: var(--dm-text-3); margin-top: 0.2rem; }
.dm-stat-foot .up { color: var(--dm-success); font-weight: 600; }

/* ---------- Badges ------------------------------------------------------ */
.dm-badge { display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.15rem 0.55rem; border-radius: 999px;
  font-size: 0.75rem; font-weight: 500; border: 1px solid transparent; white-space: nowrap; }
.dm-badge::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.dm-badge.success { color: var(--dm-success); background: var(--dm-success-bg); border-color: #A7F3D0; }
.dm-badge.warning { color: var(--dm-warning); background: var(--dm-warning-bg); border-color: #FDE68A; }
.dm-badge.danger  { color: var(--dm-danger);  background: var(--dm-danger-bg);  border-color: #FECACA; }
.dm-badge.neutral { color: var(--dm-text-2);  background: var(--dm-bg);         border-color: var(--dm-border); }
.dm-badge.info    { color: var(--dm-primary); background: var(--dm-primary-50); border-color: var(--dm-primary-100); }
.dm-tag { display: inline-block; padding: 0.1rem 0.45rem; border-radius: 6px; font-size: 0.6875rem; font-weight: 600;
  letter-spacing: 0.03em; color: var(--dm-text-2); background: #F1F5F9; border: 1px solid var(--dm-border); }

/* ---------- Data tables ------------------------------------------------- */
.dm-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.875rem; }
.dm-table th { text-align: left; font-size: 0.75rem; font-weight: 600; color: var(--dm-text-3); text-transform: uppercase;
  letter-spacing: 0.04em; padding: 0.6rem 0.75rem; background: var(--dm-bg); border-bottom: 1px solid var(--dm-border); }
.dm-table td:first-child { max-width: 0; width: 55%; }
.dm-table td { padding: 0.75rem; border-bottom: 1px solid var(--dm-border); color: var(--dm-text-2); vertical-align: middle; }
.dm-table tr:last-child td { border-bottom: none; }
.dm-table tr:hover td { background: #FBFCFE; }
.dm-file { display: flex; align-items: center; gap: 0.65rem; min-width: 0; }
.dm-file-icon { flex: none; width: 32px; height: 32px; border-radius: 8px; background: #FEF2F2; color: #DC2626;
  display: grid; place-items: center; font-size: 0.625rem; font-weight: 700; letter-spacing: 0.02em; }
.dm-file-name { color: var(--dm-text); font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dm-file-sub { font-size: 0.75rem; color: var(--dm-muted); }

/* Interactive table rows built from st.columns (parent container has gap=None) */
.st-key-doctable { background: var(--dm-surface); border: 1px solid var(--dm-border); border-radius: var(--dm-radius);
  overflow: hidden; box-shadow: var(--dm-shadow); }
.st-key-dochead { background: var(--dm-bg); padding: 0.6rem 1rem; }
.st-key-dochead .dm-th { font-size: 0.75rem; font-weight: 600; color: var(--dm-text-3); text-transform: uppercase; letter-spacing: 0.04em; }
[class*="st-key-docrow"] { padding: 0.55rem 1rem; border-top: 1px solid var(--dm-border); }
[class*="st-key-docrow"]:hover { background: #FBFCFE; }
[class*="st-key-docrow"] [data-testid="stColumn"] { min-width: 0; }
[class*="st-key-docrow"] .dm-td { font-size: 0.875rem; color: var(--dm-text-2); white-space: nowrap; }
[class*="st-key-docrow"] .dm-file-name { font-size: 0.875rem; }
[class*="st-key-docrow"] button { min-height: 32px; padding: 0 0.45rem; }

/* ---------- Upload zone (Dropbox / Drive style) ------------------------- */
[data-testid="stFileUploader"] > label { display: none; }
[data-testid="stFileUploaderDropzone"] {
  display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important;
  gap: 0.6rem; min-height: 190px; text-align: center;
  border: 1.5px dashed var(--dm-border-strong) !important; background: var(--dm-bg) !important;
  border-radius: var(--dm-radius) !important; padding: 1.75rem 1.25rem !important; transition: border-color .15s ease, background .15s ease;
}
[data-testid="stFileUploaderDropzone"]::before {
  content: "Drag and drop PDF files here"; display: block; padding-top: 56px;
  background: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%2244%22%20height%3D%2244%22%20viewBox%3D%220%200%2044%2044%22%3E%3Crect%20width%3D%2244%22%20height%3D%2244%22%20rx%3D%2212%22%20fill%3D%22%23EFF6FF%22/%3E%3Cg%20transform%3D%22translate%2810%2010%29%22%20fill%3D%22none%22%20stroke%3D%22%232563EB%22%20stroke-width%3D%221.8%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M12%2016V4M7%209l5-5%205%205%22/%3E%3Cpath%20d%3D%22M4%2016v3a2%202%200%200%200%202%202h12a2%202%200%200%200%202-2v-3%22/%3E%3C/g%3E%3C/svg%3E") top center / 44px 44px no-repeat;
  font-weight: 600; font-size: 0.9375rem; color: var(--dm-text);
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--dm-primary) !important; background: var(--dm-primary-50) !important; }
[data-testid="stFileUploaderDropzone"] button { order: 2; }
[data-testid="stFileUploaderDropzoneInstructions"] { order: 1; }
[data-testid="stFileUploaderDropzoneInstructions"] * { color: var(--dm-muted) !important; font-size: 0.8125rem !important; }

/* ---------- Buttons, inputs, tabs -------------------------------------- */
button[kind="primary"], [data-testid="stBaseButton-primary"] { font-weight: 500; box-shadow: 0 1px 2px rgba(37,99,235,.25); }
button[kind="secondary"], [data-testid="stBaseButton-secondary"] { font-weight: 500; background: var(--dm-surface); }
[data-testid="stBaseButton-tertiary"] { font-weight: 500; color: var(--dm-text-2); }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 1.25rem; border-bottom: 1px solid var(--dm-border); }
[data-testid="stTabs"] [data-baseweb="tab"] { font-weight: 500; color: var(--dm-text-3); padding: 0.5rem 0.1rem; }
[data-testid="stTabs"] [aria-selected="true"] { color: var(--dm-text); }
textarea { font-size: 0.9375rem !important; line-height: 1.55 !important; }
[data-testid="stForm"] { border: none; padding: 0; }

/* ---------- Activity feed ---------------------------------------------- */
.dm-feed { list-style: none; margin: 0 !important; padding: 0 !important; }
.dm-feed li { display: flex; gap: 0.75rem; padding: 0.7rem 0; border-bottom: 1px solid var(--dm-border); }
.dm-feed li:last-child { border-bottom: none; }
.dm-feed-icon { flex: none; width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center;
  background: var(--dm-bg); border: 1px solid var(--dm-border); color: var(--dm-text-3); }
.dm-feed-icon.upload { color: var(--dm-primary); background: var(--dm-primary-50); border-color: var(--dm-primary-100); }
.dm-feed-icon.analysis { color: var(--dm-secondary); }
.dm-feed-icon.delete, .dm-feed-icon.upload_failed, .dm-feed-icon.workspace_cleared { color: var(--dm-danger); background: var(--dm-danger-bg); border-color: #FECACA; }
.dm-feed-body { min-width: 0; flex: 1; }
.dm-feed-title { font-size: 0.8125rem; color: var(--dm-text); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dm-feed-detail { font-size: 0.75rem; color: var(--dm-text-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dm-feed-time { flex: none; font-size: 0.75rem; color: var(--dm-muted); white-space: nowrap; }
.dm-feed-group { font-size: 0.6875rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--dm-muted); margin: 1rem 0 0.15rem; }

/* ---------- Key/value overview list ------------------------------------ */
.dm-kv { display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; padding: 0.6rem 0;
  border-bottom: 1px solid var(--dm-border); font-size: 0.8125rem; }
.dm-kv:last-child { border-bottom: none; }
.dm-kv span:first-child { color: var(--dm-text-3); }
.dm-kv span:last-child { color: var(--dm-text); font-weight: 500; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ---------- Checklist / onboarding ------------------------------------- */
.dm-check { display: flex; align-items: center; gap: 0.6rem; padding: 0.4rem 0; font-size: 0.875rem; color: var(--dm-text-2); }
.dm-check .box { width: 18px; height: 18px; border-radius: 50%; border: 1.5px solid var(--dm-border-strong); display: grid; place-items: center; flex: none; }
.dm-check.done { color: var(--dm-text-3); text-decoration: line-through; }
.dm-check.done .box { background: var(--dm-primary); border-color: var(--dm-primary); color: white; }

/* ---------- Report cards (analysis results) ---------------------------- */
[class*="st-key-report"] {
  background: var(--dm-surface); border: 1px solid var(--dm-border); border-radius: var(--dm-radius);
  padding: 1.25rem 1.4rem 0.9rem; box-shadow: var(--dm-shadow); margin-bottom: 0.25rem;
}
.dm-report-label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; color: var(--dm-text-3); font-weight: 500; }
.dm-report-label .id { font-weight: 600; color: var(--dm-primary); letter-spacing: 0.04em; text-transform: uppercase; }
.dm-report-q { font-size: 1.0625rem; font-weight: 600; color: var(--dm-text); margin: 0.35rem 0 0.2rem; line-height: 1.4; }
.dm-report-rewrite { font-size: 0.8125rem; color: var(--dm-text-3); margin-bottom: 0.25rem; }
.dm-report-meta { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.5rem 0 0.75rem; }
.dm-report-divider { height: 1px; background: var(--dm-border); margin: 0.25rem 0 0.9rem; }
[class*="st-key-report"] [data-testid="stMarkdownContainer"] p,
[class*="st-key-report"] [data-testid="stMarkdownContainer"] li { font-size: 0.9375rem; line-height: 1.65; color: #1E293B; }
[class*="st-key-report"] table { font-size: 0.875rem; }
.dm-cite { display: inline-flex; align-items: center; justify-content: center; min-width: 18px; height: 18px; padding: 0 4px;
  margin: 0 1px; border-radius: 5px; font-size: 0.6875rem; font-weight: 600; vertical-align: 2px;
  background: var(--dm-primary-50); color: var(--dm-primary); border: 1px solid var(--dm-primary-100); }

/* ---------- References side panel -------------------------------------- */
.st-key-card-references { position: sticky; top: 1rem; }
.dm-ref { border: 1px solid var(--dm-border); border-radius: 10px; padding: 0.75rem 0.85rem; margin-bottom: 0.6rem; background: var(--dm-surface); }
.dm-ref:hover { border-color: var(--dm-border-strong); box-shadow: var(--dm-shadow-sm); }
.dm-ref-head { display: flex; align-items: center; gap: 0.55rem; }
.dm-ref-num { flex: none; width: 22px; height: 22px; border-radius: 6px; background: var(--dm-secondary); color: white;
  font-size: 0.6875rem; font-weight: 600; display: grid; place-items: center; }
.dm-ref-file { font-size: 0.8125rem; font-weight: 600; color: var(--dm-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.dm-ref-page { font-size: 0.75rem; color: var(--dm-text-3); white-space: nowrap; }
.dm-ref-snip { font-size: 0.8125rem; color: var(--dm-text-2); line-height: 1.55; margin-top: 0.5rem;
  display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
.dm-ref-score { margin-top: 0.5rem; display: flex; align-items: center; gap: 0.5rem; font-size: 0.6875rem; color: var(--dm-muted); }
.dm-ref-bar { flex: 1; height: 4px; background: var(--dm-border); border-radius: 999px; overflow: hidden; }
.dm-ref-bar span { display: block; height: 100%; background: var(--dm-primary); }

/* ---------- Empty states ----------------------------------------------- */
.dm-empty { text-align: center; padding: 2.5rem 1rem 1.25rem; }
.dm-empty-icon { width: 48px; height: 48px; margin: 0 auto 0.85rem; border-radius: 12px; display: grid; place-items: center;
  background: var(--dm-bg); border: 1px solid var(--dm-border); color: var(--dm-text-3); }
.dm-empty h4 { font-size: 0.9375rem; font-weight: 600; margin: 0 0 0.3rem; color: var(--dm-text); }
.dm-empty p { font-size: 0.8125rem; color: var(--dm-text-3); max-width: 360px; margin: 0 auto; }

/* ---------- Skeleton loaders ------------------------------------------- */
.dm-skel { display: block; height: 12px; border-radius: 6px; margin: 0.6rem 0;
  background: linear-gradient(90deg, #EEF2F6 25%, #F8FAFC 37%, #EEF2F6 63%); background-size: 400% 100%;
  animation: dm-shimmer 1.3s ease infinite; }
.dm-skel.h { height: 16px; width: 45%; }
@keyframes dm-shimmer { 0% { background-position: 100% 50%; } 100% { background-position: 0 50%; } }
.dm-status-line { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; color: var(--dm-text-3); }
.dm-spinner { width: 14px; height: 14px; border: 2px solid var(--dm-primary-100); border-top-color: var(--dm-primary);
  border-radius: 50%; animation: dm-spin .8s linear infinite; }
@keyframes dm-spin { to { transform: rotate(360deg); } }

/* ---------- Callouts ---------------------------------------------------- */
.dm-callout { display: flex; gap: 0.65rem; padding: 0.75rem 0.9rem; border-radius: 10px; font-size: 0.8125rem;
  border: 1px solid var(--dm-border); background: var(--dm-bg); color: var(--dm-text-2); }
.dm-callout.warning { background: var(--dm-warning-bg); border-color: #FDE68A; color: #92400E; }
.dm-callout.info { background: var(--dm-primary-50); border-color: var(--dm-primary-100); color: #1E40AF; }

/* ---------- Dialogs ----------------------------------------------------- */
div[role="dialog"] { border-radius: 14px !important; box-shadow: var(--dm-shadow-lg) !important; }

/* ---------- Responsive -------------------------------------------------- */
@media (max-width: 1024px) {
  [data-testid="stMainBlockContainer"], .block-container { padding: 3.25rem 1.25rem 3rem; }
  .dm-hide-md { display: none !important; }
}
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"], .block-container { padding: 3.25rem 0.75rem 3rem; }
  .st-key-topbar [data-testid="stColumn"]:nth-child(2) { display: none !important; }
  .dm-stat { padding: 0.85rem; }
  .dm-table td, .dm-table th { padding: 0.6rem 0.5rem; }
  .dm-page-title { font-size: 1.35rem; }
  .dm-hide-sm, .st-key-dochead [data-testid="stColumn"]:nth-child(2), .st-key-dochead [data-testid="stColumn"]:nth-child(3),
  [class*="st-key-docrow"] [data-testid="stColumn"]:nth-child(2), [class*="st-key-docrow"] [data-testid="stColumn"]:nth-child(3) { display: none !important; }
  .st-key-topbar-new-ws { display: none !important; }
  .dm-stat-value { font-size: 1.4rem; }
  .st-key-card-references { position: static; }
}
</style>
"""
