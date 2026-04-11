import { useStore } from "@nanostores/react";
import { $session, clearSession, hydrateSession } from "@/lib/stores";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function NavUser() {
  // Hydrate session from localStorage on first render
  useEffect(() => { hydrateSession(); }, []);

  const session = useStore($session);
  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState("");
  const [nameSaving, setNameSaving] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);

  const openEditName = () => {
    setNameInput(session?.githubName || "");
    setNameError(null);
    setEditingName(true);
  };

  const saveDisplayName = async () => {
    if (!session?.token) return;
    setNameSaving(true);
    setNameError(null);
    try {
      await api.updateDisplayName(session.token, nameInput.trim() || null);
      $session.set({ ...session, githubName: nameInput.trim() || session.githubHandle || "" });
      setEditingName(false);
    } catch {
      setNameError("Failed to save. Try again.");
    } finally {
      setNameSaving(false);
    }
  };

  if (!session) {
    return (
      <div className="px-3 pb-6 pt-4 border-t border-white/8">
        <a href="/auth" className="btn btn-primary text-sm w-full flex items-center justify-center gap-2 py-2.5">
          <img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Octicons-mark-github.svg" alt="" className="w-4 h-4 invert" />
          Sign in with GitHub
        </a>
      </div>
    );
  }

  return (
    <div className="px-3 pb-5 pt-4 border-t border-white/8 flex flex-col gap-2">
      {/* User identity */}
      <div className="flex items-center gap-3 px-2 py-2">
        {session.githubAvatarUrl ? (
          <img src={session.githubAvatarUrl} alt="" className="w-8 h-8 rounded-full ring-1 ring-white/20 flex-shrink-0" />
        ) : (
          <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-[16px] text-gray-400">person</span>
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-white truncate leading-tight">
            {session.githubName || (session.githubHandle ? `@${session.githubHandle}` : "User")}
          </p>
          {session.githubHandle && (
            <p className="text-xs text-gray-600 truncate">@{session.githubHandle}</p>
          )}
        </div>
        {session.isSuperadmin && (
          <span className="text-[9px] bg-primary/20 text-primary px-1.5 py-0.5 rounded font-mono flex-shrink-0">admin</span>
        )}
      </div>

      {/* Inline display name editor */}
      {editingName ? (
        <div className="px-2 space-y-1.5">
          <input
            type="text"
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") saveDisplayName(); if (e.key === "Escape") setEditingName(false); }}
            placeholder="Display name…"
            className="w-full bg-black/20 border border-white/10 rounded-lg px-2.5 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            autoFocus
          />
          {nameError && <p className="text-xs text-red-400 px-0.5">{nameError}</p>}
          <div className="flex gap-2">
            <button
              onClick={() => setEditingName(false)}
              className="flex-1 py-1 text-xs text-gray-400 border border-white/10 rounded-lg hover:bg-white/5 transition-all"
            >Cancel</button>
            <button
              onClick={saveDisplayName}
              disabled={nameSaving}
              className="flex-1 py-1 text-xs bg-primary/80 hover:bg-primary text-white rounded-lg transition-all disabled:opacity-50"
            >{nameSaving ? "Saving…" : "Save"}</button>
          </div>
        </div>
      ) : (
        <button
          onClick={openEditName}
          className="flex items-center gap-3 px-3 py-1.5 rounded-lg text-xs font-medium text-gray-500 hover:text-white hover:bg-white/6 border border-transparent transition-all w-full text-left"
        >
          <span className="material-symbols-outlined text-[16px]">edit</span>
          Edit display name
        </button>
      )}

      {/* Admin link — only for superadmin */}
      {session.isSuperadmin && (
        <a
          href="/admin"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-primary hover:bg-primary/10 border border-transparent hover:border-primary/20 transition-all"
        >
          <span className="material-symbols-outlined text-[18px]">admin_panel_settings</span>
          Admin Panel
        </a>
      )}

      {/* Sign out */}
      <button
        onClick={() => { clearSession(); window.location.href = "/"; }}
        className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-500 hover:text-white hover:bg-white/6 border border-transparent transition-all w-full text-left"
      >
        <span className="material-symbols-outlined text-[18px]">logout</span>
        Sign Out
      </button>
    </div>
  );
}
