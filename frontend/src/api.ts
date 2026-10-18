export type Row = Record<string, any>;
let workspace = localStorage.getItem("engram.workspace") || "";
export function setWorkspace(value: string) {
  workspace = value;
  localStorage.setItem("engram.workspace", value);
}
export async function api<T = Row>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const form = options.body instanceof FormData;
  const result = await fetch("/api" + path, {
    ...options,
    credentials: "same-origin",
    headers: {
      ...(form ? {} : { "Content-Type": "application/json" }),
      "X-Engram-Request": "1",
      ...(workspace ? { "X-Workspace": workspace } : {}),
      ...options.headers,
    },
  });
  const body = await result.json();
  if (!result.ok)
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : JSON.stringify(body.detail),
    );
  return body;
}
export function post<T = Row>(path: string, body: unknown = {}): Promise<T> {
  return api<T>(path, { method: "POST", body: JSON.stringify(body) });
}
