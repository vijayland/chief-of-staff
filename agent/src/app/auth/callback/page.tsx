"use client";

import { Bot } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { saveTokens } from "@/lib/auth";

export default function AuthCallbackPage() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState("");

  useEffect(() => {
    const access = params.get("access_token");
    const refresh = params.get("refresh_token");

    if (!access || !refresh) {
      setError("Authentication failed. No tokens received.");
      return;
    }

    saveTokens(access, refresh);
    router.replace("/dashboard");
  }, [params, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-sidebar">
        <div className="text-center">
          <p className="text-sm text-danger bg-danger-light px-4 py-3 rounded-lg border border-danger/20">
            {error}
          </p>
          <button
            type="button"
            onClick={() => router.push("/")}
            className="mt-4 text-xs text-text-secondary hover:text-text-primary"
          >
            ← Back to sign in
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-sidebar">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-text-primary flex items-center justify-center animate-pulse">
          <Bot className="w-5 h-5 text-white" />
        </div>
        <p className="text-sm text-text-secondary">Signing you in…</p>
      </div>
    </div>
  );
}
