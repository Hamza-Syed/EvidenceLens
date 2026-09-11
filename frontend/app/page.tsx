"use client";

import { useState } from "react";
import { Document, VerificationResult, uploadDocuments, verifyText } from "../lib/api";

const labels = { supported: "Supported", partially_supported: "Partially supported", contradicted: "Contradicted", insufficient_evidence: "Insufficient evidence" };

export default function Home() {
  const [files, setFiles] = useState<File[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [text, setText] = useState("");
  const [results, setResults] = useState<VerificationResult[] | null>(null);
  const [busy, setBusy] = useState<"upload" | "verify" | null>(null);
  const [error, setError] = useState("");
  const [fileKey, setFileKey] = useState(0);

  async function upload() {
    setBusy("upload"); setError(""); setResults(null);
    try {
      const data = await uploadDocuments(files);
      setDocuments((previous) => [...previous, ...data.documents]);
      setSelected((previous) => [...previous, ...data.documents.map((document) => document.id)]);
      setFiles([]); setFileKey((key) => key + 1);
    } catch (error) { setError(error instanceof Error ? error.message : "Upload failed."); }
    finally { setBusy(null); }
  }

  async function verify() {
    setBusy("verify"); setError(""); setResults(null);
    try { setResults((await verifyText(text, selected)).results); }
    catch (error) { setError(error instanceof Error ? error.message : "Verification failed."); }
    finally { setBusy(null); }
  }

  return (
    <main className="mx-auto max-w-5xl px-5 py-12">
      <header className="mb-10 border-b border-emerald-900/15 pb-8">
        <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-teal-700">Document-grounded verification</p>
        <h1 className="text-4xl font-bold tracking-tight">EvidenceLens</h1>
        <p className="mt-3 text-lg text-slate-600">Trace each claim back to the evidence you provide.</p>
      </header>
      <aside className="mb-8 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
        <strong>First-slice baseline.</strong> Text is split into sentences. Only exact sentence matches can be supported;
        other claims receive insufficient evidence. Paraphrases, compound claims, and conflicting evidence need further review.
        Documents are temporary and cleared when the backend restarts.
      </aside>
      <div className="grid gap-6 md:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="mb-2 text-xl font-semibold">1. Add your sources</h2>
          <p id="upload-help" className="mb-5 text-sm text-slate-600">Text-based PDFs. Up to 10 files per upload, 10 MiB each.</p>
          <label htmlFor="pdfs" className="mb-2 block text-sm font-medium">PDF documents</label>
          <input key={fileKey} id="pdfs" type="file" accept=".pdf,application/pdf" multiple disabled={!!busy} aria-describedby="upload-help"
            className="w-full rounded-lg border border-slate-300 p-3 text-sm file:mr-3 file:rounded file:border-0 file:bg-teal-50 file:p-2"
            onChange={(event) => { setFiles(Array.from(event.target.files ?? [])); setError(""); }} />
          <button onClick={upload} disabled={!!busy || !files.length} className="mt-4 rounded-lg bg-teal-800 px-5 py-3 font-medium text-white">
            {busy === "upload" ? "Extracting pages…" : "Upload PDFs"}
          </button>
          <fieldset className="mt-6" disabled={!!busy}>
            <legend className="mb-2 text-sm font-semibold">Sources used for verification</legend>
            {!documents.length && <p className="text-sm text-slate-500">Your uploaded sources will appear here.</p>}
            {documents.map((document) => (
              <label key={document.id} className="flex items-start gap-3 border-b border-slate-100 py-3 text-sm">
                <input type="checkbox" className="mt-1" checked={selected.includes(document.id)} onChange={(event) => {
                  setSelected(event.target.checked ? [...selected, document.id] : selected.filter((id) => id !== document.id)); setResults(null);
                }} />
                <span className="min-w-0 break-words"><strong>{document.name}</strong><span className="block text-slate-500">{document.page_count} pages · {document.passage_count} passages</span></span>
              </label>
            ))}
          </fieldset>
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="mb-2 text-xl font-semibold">2. Check your text</h2>
          <p className="mb-5 text-sm text-slate-600">Paste an AI response or article to check against selected sources.</p>
          <label htmlFor="claims" className="mb-2 block text-sm font-medium">Text to verify</label>
          <textarea id="claims" value={text} maxLength={20000} disabled={!!busy} rows={9}
            className="w-full resize-y rounded-lg border border-slate-300 p-3 text-sm leading-6"
            placeholder="The observatory opened in 1998."
            onChange={(event) => { setText(event.target.value); setResults(null); }} />
          <p className="mt-1 text-right text-xs text-slate-500">{text.length.toLocaleString()} / 20,000 characters</p>
          <button onClick={verify} disabled={!!busy || !selected.length || !text.trim()} className="mt-4 rounded-lg bg-teal-800 px-5 py-3 font-medium text-white">
            {busy === "verify" ? "Checking evidence…" : "Verify claims"}
          </button>
        </section>
      </div>
      {error && <p role="alert" className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</p>}
      <section aria-live="polite" aria-busy={!!busy} className="mt-10">
        <h2 className="mb-4 text-2xl font-semibold">Evidence review</h2>
        {results === null && <p className="text-slate-500">Upload sources and verify text to see claims and page citations.</p>}
        {results?.map((result, index) => (
          <article key={result.claim.id} className="mb-5 rounded-2xl border border-slate-200 bg-white p-6">
            <span className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${result.classification === "supported" ? "bg-teal-100 text-teal-900" : "bg-amber-100 text-amber-950"}`}>{labels[result.classification]}</span>
            <h3 className="mt-4 text-lg font-semibold">{index + 1}. {result.claim.text}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{result.explanation}</p>
            <details className="mt-4">
              <summary className="cursor-pointer text-sm font-semibold text-teal-800">Retrieved evidence ({result.evidence.length})</summary>
              {result.evidence.length === 0 && <p className="mt-3 text-sm text-slate-500">No relevant passage was retrieved.</p>}
              {result.evidence.map((evidence) => (
                <blockquote key={evidence.id} className="mt-4 border-l-2 border-teal-300 pl-4">
                  <p className="whitespace-pre-wrap break-words text-sm leading-6">{evidence.text}</p>
                  <footer className="mt-2 text-xs font-semibold text-teal-800">{evidence.document_name} · Page {evidence.page_number}</footer>
                </blockquote>
              ))}
            </details>
          </article>
        ))}
      </section>
    </main>
  );
}
