# *Hidup*. : Agentic SSDLC

## Gambaran Umum

Proyek ini mengimplementasikan sistem AI Agentic di dalam **Secure Software Development Lifecycle (SSDLC)**. Sistem menggunakan alur kerja yang terstruktur, modular, dan terorganisir untuk mengotomatisasi serta meningkatkan berbagai tahap pengembangan perangkat lunak—mulai dari pengumpulan kebutuhan awal hingga desain dan dokumentasi.

Sistem dibangun dengan kombinasi **Pydantic AI** dan **LangGraph**, memberikan dasar yang kuat untuk alur kerja yang terstruktur, skalabel, dan adaptif. Pendekatan agentic ini membuat proses pengembangan lebih transparan, modular, dan **secure by design**.

---

## Cara Kerja

Sistem menerapkan alur kerja multi-agen yang diorkestrasi oleh **LangGraph**. Proses dimulai dari analisis intent (maksud) pengguna, lalu dialirkan ke agen-agen khusus yang masing-masing menangani tahapan spesifik SSDLC.

### Komponen Utama

- **Intent Agent** — Mengklasifikasikan input pengguna sebagai `ask`, `agent_mode`, atau `complete_workflow`.
- **Router** — Mengarahkan permintaan ke agen/workflow sesuai hasil analisis intent.
- **Workflow Graph** — Graf berstatus (stateful) dengan LangGraph yang mendefinisikan urutan operasi dan transisi antar agen.

### Alur Kerja Agentic (SSDLC)

1. **Interviewer Agent** — Mengumpulkan kebutuhan proyek awal secara percakapan.
2. **Planner Agent** — Menghasilkan analisis kebutuhan lingkungan & keamanan dari hasil interview.
3. **Designer Agent** — Menyusun desain sistem berdasarkan perencanaan.
4. **Coder Agent** — Menghasilkan dokumentasi & struktur kode berdasarkan desain.

Setiap agen bersifat modular (dapat diganti/diperluas). Utilitas **Memory** menyimpan konteks lintas tahap agar alur tetap konsisten.

## Demonstrasi

Demostrasi Prototype: [https://drive.google.com/file/d/1whOVSh0Y2QPgzDdlpELPncOLLEbxQvsc/view?usp=sharing](https://drive.google.com/file/d/1whOVSh0Y2QPgzDdlpELPncOLLEbxQvsc/view?usp=sharing)
