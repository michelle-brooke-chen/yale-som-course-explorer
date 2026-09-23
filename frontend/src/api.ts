const API_BASE = "http://127.0.0.1:8000";

export interface Course {
  id: string;
  title: string;
  number: string;
  faculty?: string;
  category?: string;
  day?: string;
  time?: string;
  description?: string;
  faculty_bio?: string;
  credits?: number;
  session?: string;
  room?: string;
  start_date?: string;
  end_date?: string;
  enrollment?: string;
  faculty_email?: string;
  syllabus?: string;
}

export interface CoursesResponse {
  count: number;
  courses: Course[];
}

export interface ChatResponse {
  reply: string;
  tools_used: string[];
}

export interface User {
  id: number;
  username: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface SavedChat {
  id: number;
  user_message: string;
  reply: string;
  tools_used: string[];
  created_at: string;
}

const TOKEN_KEY = "course-explorer-token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

// Lets the app return to the sign-in screen when a session expires
let handleUnauthorized: () => void = () => {};
export function onUnauthorized(callback: () => void) {
  handleUnauthorized = callback;
}

async function errorMessage(response: Response, fallback: string) {
  try {
    const body = await response.json();
    return typeof body.detail === "string" ? body.detail : fallback;
  } catch {
    return fallback;
  }
}

async function authFetch(path: string, init: RequestInit = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken() ?? ""}`,
      ...init.headers,
    },
  });
  if (response.status === 401) {
    clearToken();
    handleUnauthorized();
  }
  return response;
}

async function authenticate(path: string, username: string, password: string) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response, "Something went wrong. Please try again."));
  }
  const data: AuthResponse = await response.json();
  localStorage.setItem(TOKEN_KEY, data.token);
  return data.user;
}

export const login = (username: string, password: string) =>
  authenticate("/api/auth/login", username, password);

export const register = (username: string, password: string) =>
  authenticate("/api/auth/register", username, password);

export async function getCurrentUser(): Promise<User | null> {
  if (!getToken()) return null;
  const response = await authFetch("/api/auth/me");
  return response.ok ? response.json() : null;
}

export async function getChatHistory(): Promise<SavedChat[]> {
  const response = await authFetch("/api/chats");
  if (!response.ok) throw new Error(await errorMessage(response, "Failed to load chat history"));
  const data = await response.json();
  return data.chats;
}

export async function getCourses(query?: string): Promise<CoursesResponse> {
  const params = new URLSearchParams();
  if (query) params.append("q", query);
  const response = await fetch(`${API_BASE}/api/courses?${params}`);
  if (!response.ok) throw new Error("Failed to fetch courses");
  return response.json();
}

export async function chatWithAgent(message: string): Promise<ChatResponse> {
  const response = await authFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
  if (!response.ok) throw new Error(await errorMessage(response, "Failed to chat with agent"));
  return response.json();
}

export async function healthCheck(): Promise<{ ok: boolean }> {
  const response = await fetch(`${API_BASE}/api/health`);
  if (!response.ok) throw new Error("Health check failed");
  return response.json();
}
