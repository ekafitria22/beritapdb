import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

from utils.constants import APP_TITLE, CATEGORY_SITEID, NEWS_TYPE_OPTIONS, KEYWORD_HINT
from utils.scraper_detik import scrape_detik_search
from utils.text_utils import clean_text, split_sentences

# =========================
# STYLE
# =========================
st.set_page_config(page_title=APP_TITLE, layout="wide")

st.markdown("""
<style>
div.stButton > button {
    border-radius: 8px;
    padding: 10px 16px;
    border: 0px;
    font-weight: 600;
}
.btn-save  div.stButton > button {background:#28a745;color:white;}
.btn-proc  div.stButton > button {background:#007bff;color:white;}
.btn-seg   div.stButton > button {background:#FF9800;color:white;}
.btn-model div.stButton > button {background:#ffc107;color:black;}
.small-note {font-size: 13px; opacity: 0.8;}
</style>
""", unsafe_allow_html=True)

# =========================
# HEADER
# =========================
st.image("bps.png", width=200)

st.markdown(f"<h1 style='text-align: center;'>{APP_TITLE}</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center;'>Sistem ini mengklasifikasikan berita ekonomi untuk mendeteksi pergerakan PDB Indonesia. "
    "Percobaan awal: scraping → pembersihan → segmentasi → (dummy) penerapan model.</p>",
    unsafe_allow_html=True
)

# =========================
# SESSION STATE INIT
# =========================
if "params" not in st.session_state:
    st.session_state.params = {}
if "df_raw" not in st.session_state:
    st.session_state.df_raw = pd.DataFrame()
if "df_clean" not in st.session_state:
    st.session_state.df_clean = pd.DataFrame()
if "segments" not in st.session_state:
    st.session_state.segments = {}   # url -> list kalimat
if "df_pred" not in st.session_state:
    st.session_state.df_pred = pd.DataFrame()

# =========================
# INPUT AREA
# =========================
st.subheader("Pilih Rentang Tanggal")
colA, colB = st.columns(2)
with colA:
    start_date = st.date_input("Tanggal Mulai")
with colB:
    end_date = st.date_input("Tanggal Akhir")

st.subheader("Pilih Jenis Berita")
news_type = st.selectbox("Pilih Jenis Berita:", options=NEWS_TYPE_OPTIONS)

st.subheader("Masukkan Kata Kunci Berita")
keywords = st.text_input("Ketikkan kata kunci berita yang dicari:", value="pdb")

show_notes = st.checkbox("Tampilkan Catatan Kata Kunci")
if show_notes:
    st.subheader("Catatan Kata Kunci")
    st.write("Contoh keyword ekonomi yang bisa kamu coba:")
    st.write(", ".join(KEYWORD_HINT))

# kategori detik (yang real dipakai scraper)
st.subheader("Sumber / Kategori Detik")
cat_label = st.selectbox("Pilih kategori Detik:", options=["Semua"] + list(CATEGORY_SITEID.keys()))

st.subheader("Jumlah Artikel (Percobaan)")
max_articles = st.slider("Ambil maksimal artikel:", 5, 200, 30, 5)

# request control
with st.expander("Pengaturan request (advanced)"):
    sleep_s = st.slider("Delay per request (detik)", 0.3, 3.0, 0.8, 0.1)
    timeout = st.slider("Timeout (detik)", 5, 60, 20, 5)

st.markdown("<hr>", unsafe_allow_html=True)
st.subheader("Proses Scraping dan Penerapan Model")

# =========================
# BUTTONS (REAL Streamlit)
# =========================
btn1, btn2, btn3, btn4 = st.columns(4)

with btn1:
    st.markdown("<div class='btn-save'>", unsafe_allow_html=True)
    save_clicked = st.button("Simpan Pilihan")
    st.markdown("</div>", unsafe_allow_html=True)

with btn2:
    st.markdown("<div class='btn-proc'>", unsafe_allow_html=True)
    scrape_clicked = st.button("Proses Scraping")
    st.markdown("</div>", unsafe_allow_html=True)

with btn3:
    st.markdown("<div class='btn-seg'>", unsafe_allow_html=True)
    segment_clicked = st.button("Segmentasi Berita")
    st.markdown("</div>", unsafe_allow_html=True)

with btn4:
    st.markdown("<div class='btn-model'>", unsafe_allow_html=True)
    model_clicked = st.button("Terapkan Model (Dummy)")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# ACTIONS
# =========================
def fmt_ddmmyyyy(d):
    return d.strftime("%d/%m/%Y")

if save_clicked:
    st.session_state.params = {
        "start_date": start_date,
        "end_date": end_date,
        "news_type": news_type,
        "keywords": keywords.strip(),
        "cat_label": cat_label,
        "max_articles": int(max_articles),
        "sleep_s": float(sleep_s),
        "timeout": int(timeout),
    }
    st.success("Pilihan tersimpan di session.")

if scrape_clicked:
    if not keywords.strip():
        st.error("Keyword tidak boleh kosong.")
        st.stop()
    if end_date < start_date:
        st.error("Tanggal akhir harus >= tanggal mulai.")
        st.stop()

    progress = st.progress(0)
    status = st.empty()

    def cb(done, total):
        pct = int((done / total) * 100)
        progress.progress(min(pct, 100))
        status.write(f"Mengambil {done}/{total} artikel…")

    from_date = fmt_ddmmyyyy(start_date)
    to_date = fmt_ddmmyyyy(end_date)

    dfs = []
    if cat_label == "Semua":
        for name, siteid in CATEGORY_SITEID.items():
            st.write(f"Scraping: **{name}**")
            df = scrape_detik_search(
                query=keywords.strip(),
                siteid=siteid,
                from_date=from_date,
                to_date=to_date,
                max_articles=max_articles,
                timeout=timeout,
                sleep_s=sleep_s,
                progress_cb=None
            )
            if not df.empty:
                df["source"] = name
                dfs.append(df)
        df_raw = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    else:
        siteid = CATEGORY_SITEID[cat_label]
        df_raw = scrape_detik_search(
            query=keywords.strip(),
            siteid=siteid,
            from_date=from_date,
            to_date=to_date,
            max_articles=max_articles,
            timeout=timeout,
            sleep_s=sleep_s,
            progress_cb=cb
        )
        if not df_raw.empty:
            df_raw["source"] = cat_label

    st.session_state.df_raw = df_raw
    st.session_state.df_clean = pd.DataFrame()
    st.session_state.df_pred = pd.DataFrame()
    st.session_state.segments = {}

    if df_raw.empty:
        st.warning("Tidak ada artikel ditemukan.")
    else:
        st.success(f"Selesai scraping ✅ total: {len(df_raw)} artikel.")

if segment_clicked:
    if st.session_state.df_raw is None or st.session_state.df_raw.empty:
        st.warning("Belum ada data hasil scraping. Klik 'Proses Scraping' dulu.")
        st.stop()

    # cleaning minimal untuk title (karena kita belum scrape content)
    df = st.session_state.df_raw.copy()
    df["title_clean"] = df["title"].astype(str).apply(clean_text)
    st.session_state.df_clean = df

    # segmentasi title (percobaan)
    seg = {}
    for _, row in df.iterrows():
        seg[row["article_url"]] = split_sentences(row["title_clean"])
    st.session_state.segments = seg

    st.success("Pembersihan + segmentasi selesai ✅ (sementara dari judul).")
    st.caption("Nanti kalau sudah ambil 'content', segmentasi dilakukan pada content (lebih sesuai paper).")

if model_clicked:
    if st.session_state.df_clean is None or st.session_state.df_clean.empty:
        st.warning("Belum ada data bersih. Klik 'Segmentasi Berita' dulu.")
        st.stop()

    # DUMMY MODEL: aturan sederhana dari keyword
    df = st.session_state.df_clean.copy()
    def dummy_pdb_label(t):
        t = t.lower()
        if any(k in t for k in ["naik", "tumbuh", "menguat", "meningkat"]):
            return "Naik"
        if any(k in t for k in ["turun", "melemah", "anjlok", "menurun", "kontraksi"]):
            return "Turun"
        return "Tidak diketahui"

    df["pdb_label"] = df["title"].astype(str).apply(dummy_pdb_label)
    df["sector_label"] = df["source"].fillna("Unknown")  # sementara
    df["growth_label"] = "Not Specified"                 # sementara

    st.session_state.df_pred = df
    st.success("Prediksi dummy selesai ✅ (untuk test UI).")

# =========================
# DISPLAY TABLE (AgGrid)
# =========================
st.subheader("Hasil Klasifikasi Berita Topik Ekonomi")

df_show = st.session_state.df_pred if not st.session_state.df_pred.empty else st.session_state.df_raw

if df_show is None or df_show.empty:
    st.info("Belum ada data. Jalankan scraping terlebih dahulu.")
else:
    # filter sektor (di UI kamu)
    sector_options = ["Semua"]
    if "sector_label" in df_show.columns:
        sector_options += sorted(df_show["sector_label"].dropna().unique().tolist())

    sector_label = st.selectbox("Pilih Kategori Lapangan Usaha:", options=sector_options)

    if sector_label != "Semua" and "sector_label" in df_show.columns:
        filtered = df_show[df_show["sector_label"] == sector_label].copy()
    else:
        filtered = df_show.copy()

    st.write(f"Menampilkan berita dengan kategori: **{sector_label}**")

    # label icon
    if "pdb_label" in filtered.columns:
        def label_with_color(x):
            if x == "Naik":
                return "🟢 Naik"
            elif x == "Turun":
                return "🔴 Turun"
            return x
        filtered["pdb_label_color"] = filtered["pdb_label"].apply(label_with_color)
    else:
        filtered["pdb_label_color"] = ""

    cols_to_show = ["title", "publish_date", "source"]
    if "sector_label" in filtered.columns:
        cols_to_show.append("sector_label")
    cols_to_show += ["pdb_label_color"]
    if "growth_label" in filtered.columns:
        cols_to_show.append("growth_label")

    data1 = filtered[cols_to_show].copy()
    data1.reset_index(drop=True, inplace=True)

    gb = GridOptionsBuilder.from_dataframe(data1)
    gb.configure_default_column(editable=False, groupable=False, resizable=True, sortable=True, filter=True)
    gb.configure_column("title", header_name="Judul Berita", width=420)
    gb.configure_column("publish_date", header_name="Tanggal Terbit", width=160)
    gb.configure_column("source", header_name="Sumber", width=120)
    if "sector_label" in data1.columns:
        gb.configure_column("sector_label", header_name="Sektor Industri", width=160)
    gb.configure_column("pdb_label_color", header_name="Prediksi", width=120)
    if "growth_label" in data1.columns:
        gb.configure_column("growth_label", header_name="Jenis Pertumbuhan", width=160)

    AgGrid(data1, gridOptions=gb.build(), height=420)

    # download
    st.subheader("Download hasil")
    csv_bytes = data1.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv_bytes, file_name="hasil_scrape_prediksi.csv", mime="text/csv")

# =========================
# METRICS (tetap tampil, tapi diberi label dummy)
# =========================
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("Hasil Klasifikasi")
st.markdown("#### Pergerakan PDB Dengan Model IndoRoBERTa (sementara dummy)")

def colored_metric(label, value, color):
    st.markdown(f"""
    <div style="padding: 8px; border-radius: 6px; background-color: {color}; color: white; text-align: center;">
        <div style="font-weight:700;">{label}</div>
        <div style="font-size: 22px; font-weight: 800;">{value}</div>
    </div>
    """, unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1: colored_metric("Akurasi", "—", "#FF9800")
with c2: colored_metric("Presisi", "—", "#4CAF50")
with c3: colored_metric("Recall", "—", "#FFD700")
with c4: colored_metric("F1-Score", "—", "#2196F3")

st.caption("Nanti metrik ini akan dihitung dari output model sebenarnya (bukan angka statis).")
