export type Document = { id: string; name: string; page_count: number; passage_count: number };
export type Classification = "supported" | "partially_supported" | "contradicted" | "insufficient_evidence";
export type Evidence = { id: string; document_id: string; document_name: string; page_number: number; text: string };
export type VerificationResult = {
  claim: { id: string; text: string };
  classification: Classification;
  explanation: string;
  evidence: Evidence[];
};

async function request<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new Error("Unable to reach EvidenceLens. Check that the application is running.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(typeof body?.detail === "string" ? body.detail : `Request failed (${response.status}). Check your inputs and that the backend is running.`);
  }
  return body as T;
}

export function uploadDocuments(files: File[]) {
  const body = new FormData();
  for (const file of files) body.append("files", file);
  return request<{ documents: Document[] }>("/api/documents", { method: "POST", body });
}

export function verifyText(text: string, documentIds: string[]) {
  return request<{ results: VerificationResult[] }>("/api/verifications", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, document_ids: documentIds }),
  });
}
