"use client";

import { useEffect, useState } from "react";
import { Document, VerificationResult, loadSample, uploadDocuments, verifyText } from "../lib/api";

const labels = { supported: "Supported", partially_supported: "Partially supported", contradicted: "Contradicted", insufficient_evidence: "Insufficient evidence" };
const colors = { supported: "bg-teal-100 text-teal-900", partially_supported: "bg-amber-100 text-amber-950", contradicted: "bg-red-100 text-red-900", insufficient_evidence: "bg-slate-100 text-slate-700" };

export default function Home() {
  const [files, setFiles] = useState<File[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [text, setText] = useState("");
  const [results, setResults] = useState<VerificationResult[] | null>(null);
  const [busy, setBusy] = useState<"upload" | "verify" | "sample" | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");
  const [fileKey, setFileKey] = useState(0);

  useEffect(() => {
    if (!busy) return;
    const started = Date.now();
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, [busy]);

  async function sample() {
    setElapsed(0); setBusy("sample"); setError(""); setResults(null);
    try {
      const data = await loadSample();
      setDocuments((previous) => [...previous, ...data.documents]);
      setSelected(data.documents.map((document) => document.id));
      setText(data.text);
      setFiles([]); setFileKey((key) => key + 1);
    } catch (error) { setError(error instanceof Error ? error.message : "Sample loading failed."); }
    finally { setBusy(null); }
  }

  async function upload() {
    setElapsed(0); setBusy("upload"); setError(""); setResults(null);
    try {
      const data = await uploadDocuments(files);
      setDocuments((previous) => [...previous, ...data.documents]);
      setSelected((previous) => [...previous, ...data.documents.map((document) => document.id)]);
      setFiles([]); setFileKey((key) => key + 1);
    } catch (error) { setError(error instanceof Error ? error.message : "Upload failed."); }
    finally { setBusy(null); }
  }

  async function verify() {
    setElapsed(0); setBusy("verify"); setError(""); setResults(null);
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
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <button onClick={sample} disabled={!!busy} className="rounded-lg bg-teal-800 px-5 py-3 font-semibold text-white">{busy === "sample" ? "Preparing sample…" : "Try sample"}</button>
          <p className="max-w-lg text-sm text-slate-600">Start with a fictional three-page study and four claims. Then choose Verify claims to run a real check.</p>
        </div>
      </header>
      <aside className="mb-8 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
        <strong>Evidence-grounded verification.</strong> Each claim is assessed against passages from your selected documents.
        Conflicting sources lead to abstention; similarity alone is not proof.
        <p className="mt-2">With the default local setup, retrieved document evidence is sent only to the verifier running on this computer. Documents are temporary and cleared when the backend restarts. An explicitly configured remote verifier changes where evidence is sent.</p>
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
            <legend className="mb-2 text-sm font-semibold">Sources used for verification · {selected.length} selected</legend>
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
      {busy && <div role="status" className="mt-6 rounded-xl border border-teal-200 bg-teal-50 p-5 text-teal-950">
        <p className="font-semibold"><span aria-hidden="true" className="mr-2 inline-block h-3 w-3 rounded-full bg-teal-600 motion-safe:animate-pulse" />{busy === "verify" ? "Checking claims against selected evidence" : "Extracting PDF pages and preparing evidence"}</p>
        <p className="mt-2 text-sm"><span aria-hidden="true">{elapsed}s elapsed. </span>{busy === "verify" ? "Local inference can take several minutes for multiple claims. Keep this page open; all results appear together after validation." : "The first upload may take longer while the local embedding model loads."}</p>
      </div>}
      {error && <p role="alert" className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</p>}
      <section aria-live="polite" aria-busy={!!busy} className="mt-10">
        <h2 className="mb-4 text-2xl font-semibold">Evidence review</h2>
        {results && results.length > 0 && <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4">
          <p className="font-semibold">{results.length} atomic claims detected</p>
          <div className="mt-3 flex flex-wrap gap-2">{(Object.keys(labels) as Array<keyof typeof labels>).map((verdict) => <span key={verdict} className={`rounded-full px-3 py-1 text-xs font-semibold ${colors[verdict]}`}>{labels[verdict]} · {results.filter((result) => result.classification === verdict).length}</span>)}</div>
        </div>}
        {results === null && <p className="text-slate-500">Upload sources and verify text to see claims and page citations.</p>}
        {results?.length === 0 && <p className="text-slate-500">No factual claim candidates were identified. Try a concrete factual statement.</p>}
        {results?.map((result, index) => (
          <article key={result.claim.id} className="mb-5 rounded-2xl border border-slate-200 bg-white p-6">
            <span className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${colors[result.classification]}`}>{labels[result.classification]}</span>
            <h3 className="mt-4 text-lg font-semibold">{index + 1}. {result.claim.text}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{result.explanation}</p>
            {result.classification === "insufficient_evidence" && <p className="mt-2 text-sm font-medium text-slate-700">Abstained — the supplied evidence does not establish a reliable decision.</p>}
            <details open className="mt-4">
              <summary className="cursor-pointer text-sm font-semibold text-teal-800">Evidence used for this verdict ({result.evidence.length})</summary>
              {result.evidence.length === 0 && <p className="mt-3 text-sm text-slate-500">No decisive evidence was identified for this claim.</p>}
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
