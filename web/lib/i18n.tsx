"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type Lang = "ID" | "EN";

const KEY = "lang";

// ID is the source of truth for the shape; EN must satisfy it, so a missing
// key is a compile error rather than a silently untranslated string.
const ID = {
    brand: "Chatbot RAG",
    brandSub: "Internal Assistant",
    newChat: "Chat Baru",
    navChat: "Chat",
    navKnowledge: "Knowledge Base",
    navAbout: "Tentang",
    navHow: "Cara Kerja",
    recent: "Percakapan terbaru",
    recentEmpty: "Belum ada. Tersimpan di browser kamu.",
    demoTitle: "Mode Demo",
    demoBody: "Dokumen dihapus otomatis setelah 24 jam.",
    openSidebar: "Buka sidebar",
    closeSidebar: "Tutup sidebar",
    openMenu: "Buka menu",
    closeMenu: "Tutup menu",
    menu: "Menu",
    tracePanel: "Panel Jejak",
    traceTitle: "Jejak Retrieval",
    traceClose: "Tutup panel jejak retrieval",
    traceEmpty:
      "Setelah kamu bertanya, di sini muncul potongan dokumen yang dipakai, beserta skor dense, sparse, RRF, dan reranker.",
    toDark: "Ganti ke Mode Gelap",
    toLight: "Ganti ke Mode Terang",
    switchLang: "Ganti Bahasa",
    waking: "Membangunkan server… sekitar 30 detik.",
    offline: "Server tidak merespons. Pastikan API hidup di",
    emptyTitle: "Tanya apa saja tentang dokumen kamu",
    emptyBody:
      "Jawaban diambil dari dokumen yang kamu unggah. Kalau tidak ada di sana, asisten bilang tidak tahu.",
    examples: "Contoh pertanyaan",
    uploadFirst: "Unggah PDF atau DOCX dulu",
    placeholder: "Ketik pertanyaan kamu di sini…",
    placeholderEmpty: "Unggah dokumen dulu…",
    listening: "Mendengarkan…",
    send: "Kirim pertanyaan",
    attach: "Unggah dokumen",
    micOn: "Tulis pertanyaan dengan suara",
    micOff: "Berhenti merekam suara",
    disclaimer: "Jawaban bisa keliru. Cek sitasinya sebelum dipakai.",
    searching: "Mencari di dokumen…",
    composing: "Menyusun jawaban…",
    stepRetrieve: "Mengambil",
    stepRank: "Merangking",
    stepRerank: "Mererangking",
    stepAnswer: "Menjawab",
    chunksFound: "potongan ditemukan.",
    source: "Sumber:",
    chunks: "potongan",
    fromDocs: "dari",
    docsWord: "dokumen",
    model: "Model:",
    rejected: "sitasi ditolak",
    failedOver: "penuh → dialihkan",
    kbTitle: "Knowledge Base",
    kbBody: "PDF atau DOCX, maksimal 3 per sesi.",
    attachTitle: "Unggah PDF atau DOCX",
    micTitle: "Dikte suara. Audio diproses layanan browser, bukan di perangkat.",
    navAria: "Navigasi utama",
    pickFile: "Pilih berkas",
    uploading: "Mengunggah…",
    dropHint: "atau seret ke sini — PDF atau DOCX, maks 5 MB",
    useSample: "Tidak punya berkas? Pakai SOP contoh",
    uploadFailed: "Unggahan gagal.",
    sampleFailed: "Gagal memuat dokumen contoh.",
    atCapacity: "Batas 3 dokumen tercapai. Hapus salah satu untuk menambah.",
    stQueued: "Mengantre",
    stParsing: "Membaca",
    stEmbedding: "Mengindeks",
    stReady: "Siap",
    stFailed: "Gagal",
    parts: "bagian",
    pagesSkipped: "halaman dilewati",
    remove: "Hapus",
    ocrWarning: "Teks ini hasil pembacaan mesin — angka dan nama bisa keliru.",
    sourceLabel: "Sumber",
    sparseDead:
      "Semua skor sparse nol. Indeks BM25 kemungkinan tidak terbentuk.",
    aboutTitle: "Tentang",
    aboutLede:
      "Tanya-jawab atas dokumen internal, dengan jawaban yang bisa dilacak ke bagian asalnya.",
    aboutWhyH: "Kenapa dibuat",
    aboutWhy1:
      "Jawaban pertanyaan karyawan biasanya sudah ada di SOP, tapi SOP-nya puluhan halaman. Chatbot umum menjawab lancar tapi bisa mengarang — masalah untuk aturan cuti, pesangon, atau kewenangan persetujuan.",
    aboutWhy2:
      "Di sini tiap klaim bisa diklik dan menunjukkan kalimat aslinya. Kalau jawabannya tidak ada di dokumen, asisten bilang tidak tahu.",
    aboutStackH: "Yang dipakai",
    aboutStack: [
      "Chunking mengikuti heading dokumen, bukan potongan tetap.",
      "Pencarian hybrid: dense + BM25, digabung RRF, lalu rerank.",
      "Sitasi divalidasi server; yang mengarang dibuang.",
      "Failover otomatis saat kuota model utama penuh.",
    ],
    aboutPrivacyH: "Privasi",
    aboutPrivacy:
      "Dokumen terisolasi per sesi dan dihapus setelah 24 jam. Isinya tidak masuk log. Riwayat percakapan disimpan di browser kamu.",
    howTitle: "Cara Kerja",
    howLede:
      "Empat tahap. Panel Jejak Retrieval menampilkan hasil nyata tiap tahap, termasuk skornya.",
    howSteps: [
      {
        title: "Dokumen dipecah per bagian",
        body: "PDF dan DOCX dipotong di batas heading, bukan tiap sekian karakter. Tiap potongan membawa jalurnya, misalnya 4. Cuti › 4.2 Cuti Tahunan.",
      },
      {
        title: "Dicari lewat dua jalur",
        body: "Dense menangkap makna dan parafrase. BM25 menangkap istilah persis seperti SOP-HR-014. Hasil keduanya digabung dengan RRF.",
      },
      {
        title: "Diurutkan ulang",
        body: "Cross-encoder membaca pertanyaan dan kandidat bersamaan, lalu memilih delapan potongan terbaik.",
      },
      {
        title: "Jawaban diperiksa",
        body: "Model hanya boleh memakai delapan potongan itu dan wajib menandai sumbernya. Server membuang penanda yang tidak cocok.",
      },
    ],
    howTip:
      "setelah bertanya untuk melihat potongan yang dipakai beserta skornya.",
    suggestions: [
      "Berapa hari cuti tahunan?",
      "Siapa yang menyetujui pengajuan cuti?",
      "Apa saja syarat pengajuan cuti besar?",
  ],
};

export type Dict = typeof ID;

const EN: Dict = {
    brand: "Chatbot RAG",
    brandSub: "Internal Assistant",
    newChat: "New Chat",
    navChat: "Chat",
    navKnowledge: "Knowledge Base",
    navAbout: "About",
    navHow: "How It Works",
    recent: "Recent chats",
    recentEmpty: "Nothing yet. Stored in your browser.",
    demoTitle: "Demo Mode",
    demoBody: "Documents are deleted automatically after 24 hours.",
    openSidebar: "Expand sidebar",
    closeSidebar: "Collapse sidebar",
    openMenu: "Open menu",
    closeMenu: "Close menu",
    menu: "Menu",
    tracePanel: "Trace Panel",
    traceTitle: "Retrieval Trace",
    traceClose: "Close retrieval trace panel",
    traceEmpty:
      "Once you ask something, this shows the document chunks that were used, with their dense, sparse, RRF and reranker scores.",
    toDark: "Switch to Dark Mode",
    toLight: "Switch to Light Mode",
    switchLang: "Change language",
    waking: "Waking the server… about 30 seconds.",
    offline: "Server is not responding. Make sure the API is running at",
    emptyTitle: "Ask anything about your documents",
    emptyBody:
      "Answers come only from the documents you upload. If it is not in there, the assistant says it does not know.",
    examples: "Try one",
    uploadFirst: "Upload a PDF or DOCX first",
    placeholder: "Type your question here…",
    placeholderEmpty: "Upload a document first…",
    listening: "Listening…",
    send: "Send question",
    attach: "Upload document",
    micOn: "Dictate your question",
    micOff: "Stop recording",
    disclaimer: "Answers can be wrong. Check the citations before relying on them.",
    searching: "Searching the documents…",
    composing: "Composing the answer…",
    stepRetrieve: "Retrieve",
    stepRank: "Rank",
    stepRerank: "Rerank",
    stepAnswer: "Answer",
    chunksFound: "chunks found.",
    source: "Source:",
    chunks: "chunks",
    fromDocs: "from",
    docsWord: "documents",
    model: "Model:",
    rejected: "citations rejected",
    failedOver: "at capacity → rerouted",
    kbTitle: "Knowledge Base",
    kbBody: "PDF or DOCX, up to 3 per session.",
    attachTitle: "Upload a PDF or DOCX",
    micTitle: "Voice dictation. Audio is processed by a browser service, not on-device.",
    navAria: "Main navigation",
    pickFile: "Choose a file",
    uploading: "Uploading…",
    dropHint: "or drop it here — PDF or DOCX, max 5 MB",
    useSample: "No file handy? Use the sample SOP",
    uploadFailed: "Upload failed.",
    sampleFailed: "Could not load the sample document.",
    atCapacity: "Limit of 3 documents reached. Remove one to add another.",
    stQueued: "Queued",
    stParsing: "Reading",
    stEmbedding: "Indexing",
    stReady: "Ready",
    stFailed: "Failed",
    parts: "chunks",
    pagesSkipped: "pages skipped",
    remove: "Remove",
    ocrWarning: "This text came from OCR — numbers and names may be wrong.",
    sourceLabel: "Source",
    sparseDead: "All sparse scores are zero. The BM25 index likely failed to build.",
    aboutTitle: "About",
    aboutLede:
      "Question answering over internal documents, with every answer traceable back to its source section.",
    aboutWhyH: "Why this exists",
    aboutWhy1:
      "The answers staff need are usually already in the SOP, but the SOP runs dozens of pages. A general chatbot answers fluently yet can make things up — a problem for leave rules, severance, or approval authority.",
    aboutWhy2:
      "Here every claim is clickable and shows the original sentence. If the answer is not in the documents, the assistant says so.",
    aboutStackH: "What it uses",
    aboutStack: [
      "Chunking follows document headings, not fixed-size splits.",
      "Hybrid search: dense + BM25, fused with RRF, then reranked.",
      "Citations are validated server-side; fabricated ones are dropped.",
      "Automatic failover when the primary model is at capacity.",
    ],
    aboutPrivacyH: "Privacy",
    aboutPrivacy:
      "Documents are isolated per session and deleted after 24 hours. Their contents are never logged. Chat history stays in your browser.",
    howTitle: "How It Works",
    howLede:
      "Four stages. The Retrieval Trace panel shows the real output of each one, scores included.",
    howSteps: [
      {
        title: "Documents are split by section",
        body: "PDF and DOCX are cut at heading boundaries rather than every N characters. Each chunk carries its path, for example 4. Leave › 4.2 Annual Leave.",
      },
      {
        title: "Searched two ways at once",
        body: "Dense catches meaning and paraphrase. BM25 catches exact terms like SOP-HR-014. Both result sets are fused with RRF.",
      },
      {
        title: "Reranked",
        body: "A cross-encoder reads the question and each candidate together, then keeps the best eight chunks.",
      },
      {
        title: "The answer is checked",
        body: "The model may only use those eight chunks and must mark its sources. The server drops any marker that does not match.",
      },
    ],
    howTip: "after asking to see which chunks were used, along with their scores.",
    suggestions: [
      "How many days of annual leave?",
      "Who approves a leave request?",
      "What are the requirements for long-service leave?",
  ],
};

const DICT: Record<Lang, Dict> = { ID, EN };

const Ctx = createContext<{ lang: Lang; t: Dict; toggle: () => void }>({
  lang: "ID",
  t: DICT.ID,
  toggle: () => {},
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLang] = useState<Lang>("ID");

  useEffect(() => {
    const stored = localStorage.getItem(KEY);
    if (stored !== "EN" && stored !== "ID") return;
    setLang(stored);
    // Keep <html lang> in step with the restored choice, not just with the
    // toggle: otherwise a saved preference renders English text still marked
    // as Indonesian, and screen readers pronounce it with the wrong voice.
    document.documentElement.lang = stored === "ID" ? "id" : "en";
  }, []);

  const toggle = useCallback(() => {
    setLang((current) => {
      const next: Lang = current === "ID" ? "EN" : "ID";
      localStorage.setItem(KEY, next);
      document.documentElement.lang = next === "ID" ? "id" : "en";
      return next;
    });
  }, []);

  return (
    <Ctx.Provider value={{ lang, t: DICT[lang], toggle }}>
      {children}
    </Ctx.Provider>
  );
}

export const useLang = () => useContext(Ctx);
