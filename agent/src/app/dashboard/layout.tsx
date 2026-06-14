"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { ChatProvider } from "@/lib/chat-context";
import { getAccessToken } from "@/lib/auth";
import { Spinner } from "@/components/ui/Spinner";
import { Menu } from "lucide-react";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!getAccessToken()) router.replace("/");
    else setReady(true);
  }, [router]);

  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center bg-white">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <ChatProvider>
      <div className="flex h-screen overflow-hidden bg-white">

        {/* Mobile overlay */}
        {sidebarOpen && (
          <div className="fixed inset-0 z-20 bg-black/40 lg:hidden"
            onClick={() => setSidebarOpen(false)} />
        )}

        {/* Sidebar */}
        <div className={`
          fixed inset-y-0 left-0 z-30 lg:static lg:z-auto
          transform transition-transform duration-200 ease-in-out lg:transform-none
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}>
          <Sidebar onClose={() => setSidebarOpen(false)} />
        </div>

        {/* Main */}
        <main className="flex-1 overflow-hidden flex flex-col min-w-0">
          {/* Mobile top bar */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-white lg:hidden shrink-0">
            <button type="button" onClick={() => setSidebarOpen(true)}
              className="p-1.5 rounded-md text-text-muted hover:bg-surface-hover transition-colors">
              <Menu className="w-5 h-5" />
            </button>
            <span className="text-sm font-semibold text-text-primary">Chief of Staff</span>
          </div>
          <div className="flex-1 overflow-hidden flex flex-col min-w-0">
            {children}
          </div>
        </main>
      </div>
    </ChatProvider>
  );
}
